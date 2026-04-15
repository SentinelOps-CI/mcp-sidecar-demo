package main

import (
	"encoding/json"
	"errors"
	"expvar"
	"fmt"
	"log"
	"net"
	"net/http"
	"net/http/httputil"
	"net/url"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"sync/atomic"
	"time"

	"gopkg.in/yaml.v3"
)

type Config struct {
	Server struct {
		Port         int    `yaml:"port"`
		Host         string `yaml:"host"`
		ReadTimeout  string `yaml:"read_timeout"`
		WriteTimeout string `yaml:"write_timeout"`
		IdleTimeout  string `yaml:"idle_timeout"`
	} `yaml:"server"`
	Policy struct {
		File           string `yaml:"file"`
		ReloadInterval string `yaml:"reload_interval"`
	} `yaml:"policy"`
	Audit struct {
		Enabled        bool   `yaml:"enabled"`
		OutputFile     string `yaml:"output_file"`
		IncludeHeaders bool   `yaml:"include_headers"`
	} `yaml:"audit"`
	Auth struct {
		Required bool   `yaml:"required"`
		Header   string `yaml:"header"`
		Prefix   string `yaml:"prefix"`
		Token    string `yaml:"token"`
	} `yaml:"auth"`
	MCPServers map[string]struct {
		Target      string `yaml:"target"`
		Timeout     string `yaml:"timeout"`
		HealthCheck string `yaml:"health_check"`
	} `yaml:"mcp_servers"`
}

type Policy struct {
	Epochs map[string]Epoch `yaml:"epochs"`
	Roles  map[string]Role  `yaml:"roles"`
}

type Epoch struct {
	Active      bool     `yaml:"active"`
	ExpiresAt   string   `yaml:"expires_at"`
	Permissions []string `yaml:"permissions"`
}

type Role struct {
	Epochs      []string `yaml:"epochs"`
	Tools       []string `yaml:"tools"`
	Permissions []string `yaml:"permissions"`
}

type RequestLog struct {
	Timestamp string            `json:"timestamp"`
	Method    string            `json:"method"`
	Path      string            `json:"path"`
	Decision  string            `json:"decision"`
	Reason    string            `json:"reason"`
	Epoch     string            `json:"epoch"`
	Tool      string            `json:"tool"`
	Headers   map[string]string `json:"headers,omitempty"`
}

type Sidecar struct {
	config     Config
	policy     Policy
	policyMu   sync.RWMutex
	ready      atomic.Bool
	permitted  *expvar.Int
	denied     *expvar.Int
	lastReload *expvar.String
}

func main() {
	cfg, err := loadConfig(configPath())
	if err != nil {
		log.Fatalf("failed to load config: %v", err)
	}
	policy, err := loadPolicy(cfg.Policy.File)
	if err != nil {
		log.Fatalf("failed to load policy: %v", err)
	}

	sidecar := &Sidecar{
		config:     cfg,
		policy:     policy,
		permitted:  expvar.NewInt("requests_permitted_total"),
		denied:     expvar.NewInt("requests_denied_total"),
		lastReload: expvar.NewString("policy_last_loaded_at"),
	}
	sidecar.ready.Store(true)
	sidecar.lastReload.Set(time.Now().UTC().Format(time.RFC3339))

	if reloadEvery := parseDurationOrDefault(cfg.Policy.ReloadInterval, 0); reloadEvery > 0 {
		go sidecar.policyReloadLoop(reloadEvery, cfg.Policy.File)
	}

	mux := http.NewServeMux()
	mux.HandleFunc("/health", sidecar.healthHandler)
	mux.HandleFunc("/ready", sidecar.readyHandler)
	mux.Handle("/metrics", expvar.Handler())
	mux.HandleFunc("/mcp1/sse", sidecar.proxyHandler("filesystem"))
	mux.HandleFunc("/mcp2/sse", sidecar.proxyHandler("git"))
	mux.HandleFunc("/mcp3/sse", sidecar.proxyHandler("http"))

	readTimeout := parseDurationOrDefault(cfg.Server.ReadTimeout, 15*time.Second)
	writeTimeout := parseDurationOrDefault(cfg.Server.WriteTimeout, 30*time.Second)
	idleTimeout := parseDurationOrDefault(cfg.Server.IdleTimeout, 60*time.Second)
	addr := fmt.Sprintf("%s:%d", cfg.Server.Host, cfg.Server.Port)
	if cfg.Server.Host == "" {
		addr = fmt.Sprintf(":%d", cfg.Server.Port)
	}

	server := &http.Server{
		Addr:              addr,
		Handler:           mux,
		ReadTimeout:       readTimeout,
		ReadHeaderTimeout: 10 * time.Second,
		WriteTimeout:      writeTimeout,
		IdleTimeout:       idleTimeout,
	}

	log.Printf("sidecar starting on %s", addr)
	log.Fatal(server.ListenAndServe())
}

func configPath() string {
	if v := os.Getenv("SIDECAR_CONFIG"); v != "" {
		return v
	}
	return filepath.Join(".", "config.yaml")
}

func loadConfig(path string) (Config, error) {
	var cfg Config
	data, err := os.ReadFile(path)
	if err != nil {
		return cfg, err
	}
	if err := yaml.Unmarshal(data, &cfg); err != nil {
		return cfg, err
	}
	if cfg.Server.Port == 0 {
		cfg.Server.Port = 8080
	}
	if cfg.Auth.Header == "" {
		cfg.Auth.Header = "Authorization"
	}
	if cfg.Auth.Prefix == "" {
		cfg.Auth.Prefix = "Bearer "
	}
	if cfg.Policy.File == "" {
		return cfg, errors.New("policy.file is required")
	}
	if cfg.Policy.ReloadInterval != "" {
		if _, err := time.ParseDuration(cfg.Policy.ReloadInterval); err != nil {
			return cfg, fmt.Errorf("invalid policy.reload_interval: %w", err)
		}
	}
	if len(cfg.MCPServers) == 0 {
		return cfg, errors.New("mcp_servers is required")
	}
	for name, server := range cfg.MCPServers {
		if server.Target == "" {
			return cfg, fmt.Errorf("mcp_servers.%s.target is required", name)
		}
		parsed, err := url.Parse(server.Target)
		if err != nil || parsed.Scheme == "" || parsed.Host == "" {
			return cfg, fmt.Errorf("mcp_servers.%s.target is invalid", name)
		}
		if server.Timeout != "" {
			if _, err := time.ParseDuration(server.Timeout); err != nil {
				return cfg, fmt.Errorf("mcp_servers.%s.timeout is invalid: %w", name, err)
			}
		}
	}
	return cfg, nil
}

func loadPolicy(path string) (Policy, error) {
	var p Policy
	data, err := os.ReadFile(path)
	if err != nil {
		return p, err
	}
	if err := yaml.Unmarshal(data, &p); err != nil {
		return p, err
	}
	if len(p.Epochs) == 0 || len(p.Roles) == 0 {
		return p, errors.New("policy must include epochs and roles")
	}
	for epochName, epoch := range p.Epochs {
		if epoch.ExpiresAt == "" {
			return p, fmt.Errorf("epoch %s must define expires_at", epochName)
		}
		if _, err := time.Parse(time.RFC3339, epoch.ExpiresAt); err != nil {
			return p, fmt.Errorf("epoch %s has invalid expires_at: %w", epochName, err)
		}
	}
	defaultRole, ok := p.Roles["default"]
	if !ok {
		return p, errors.New("policy must include default role")
	}
	if len(defaultRole.Epochs) == 0 {
		return p, errors.New("default role must reference at least one epoch")
	}
	for _, epochName := range defaultRole.Epochs {
		if _, ok := p.Epochs[epochName]; !ok {
			return p, fmt.Errorf("default role references unknown epoch %q", epochName)
		}
	}
	return p, nil
}

func (s *Sidecar) healthHandler(w http.ResponseWriter, _ *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	_, _ = w.Write([]byte(`{"status":"ok"}`))
}

func (s *Sidecar) readyHandler(w http.ResponseWriter, _ *http.Request) {
	if !s.ready.Load() {
		http.Error(w, `{"status":"not_ready"}`, http.StatusServiceUnavailable)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	_, _ = w.Write([]byte(`{"status":"ready"}`))
}

func parseDurationOrDefault(raw string, fallback time.Duration) time.Duration {
	if raw == "" {
		return fallback
	}
	d, err := time.ParseDuration(raw)
	if err != nil {
		return fallback
	}
	return d
}

func (s *Sidecar) proxyHandler(tool string) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		epoch, reason := s.evaluateRequest(r, tool)
		if reason != "permitted" {
			s.denied.Add(1)
			s.writeAudit(r, "denied", reason, epoch, tool)
			http.Error(w, "access denied", http.StatusForbidden)
			return
		}

		targetConfig, ok := s.config.MCPServers[tool]
		if !ok {
			s.denied.Add(1)
			s.writeAudit(r, "denied", "tool_target_missing", epoch, tool)
			http.Error(w, "misconfigured target", http.StatusInternalServerError)
			return
		}
		targetURL, err := url.Parse(targetConfig.Target)
		if err != nil {
			s.denied.Add(1)
			s.writeAudit(r, "denied", "tool_target_invalid", epoch, tool)
			http.Error(w, "invalid target", http.StatusInternalServerError)
			return
		}

		proxy := httputil.NewSingleHostReverseProxy(targetURL)
		headerTimeout := parseDurationOrDefault(targetConfig.Timeout, 60*time.Second)
		proxy.Transport = newProxyTransport(headerTimeout)

		s.permitted.Add(1)
		s.writeAudit(r, "permitted", reason, epoch, tool)

		// Do not wrap SSE streaming with http.TimeoutHandler; long-lived connections must stay open.
		proxy.ServeHTTP(w, r)
	}
}

func (s *Sidecar) evaluateRequest(r *http.Request, tool string) (string, string) {
	if r.Method != http.MethodGet || !strings.HasSuffix(r.URL.Path, "/sse") {
		return "", "unsupported_request_shape"
	}
	if s.config.Auth.Required && !s.validBearer(r) {
		return "", "missing_or_invalid_token"
	}

	s.policyMu.RLock()
	policy := s.policy
	s.policyMu.RUnlock()

	now := time.Now().UTC()
	role, ok := policy.Roles["default"]
	if !ok {
		return "", "missing_default_role"
	}
	if !contains(role.Tools, tool) {
		return "", "tool_not_allowed_for_role"
	}

	for _, epochID := range role.Epochs {
		epoch, found := policy.Epochs[epochID]
		if !found || !epoch.Active {
			continue
		}
		if !contains(epoch.Permissions, "call") || !contains(role.Permissions, "call") {
			continue
		}
		expiresAt, err := time.Parse(time.RFC3339, epoch.ExpiresAt)
		if err != nil {
			return epochID, "invalid_epoch_expiry_format"
		}
		if now.After(expiresAt) {
			continue
		}
		return epochID, "permitted"
	}

	return "", "no_active_epoch_permits_request"
}

func (s *Sidecar) validBearer(r *http.Request) bool {
	value := r.Header.Get(s.config.Auth.Header)
	if value == "" || !strings.HasPrefix(value, s.config.Auth.Prefix) {
		return false
	}
	if s.config.Auth.Token == "" {
		return true
	}
	return strings.TrimPrefix(value, s.config.Auth.Prefix) == s.config.Auth.Token
}

func (s *Sidecar) writeAudit(r *http.Request, decision, reason, epoch, tool string) {
	if !s.config.Audit.Enabled || s.config.Audit.OutputFile == "" {
		return
	}
	entry := RequestLog{
		Timestamp: time.Now().UTC().Format(time.RFC3339),
		Method:    r.Method,
		Path:      r.URL.Path,
		Decision:  decision,
		Reason:    reason,
		Epoch:     epoch,
		Tool:      tool,
	}
	if s.config.Audit.IncludeHeaders {
		entry.Headers = map[string]string{
			"User-Agent": r.Header.Get("User-Agent"),
		}
		if v := r.Header.Get(s.config.Auth.Header); v != "" {
			entry.Headers[s.config.Auth.Header] = "redacted"
		}
	}
	file, err := os.OpenFile(s.config.Audit.OutputFile, os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0o644)
	if err != nil {
		log.Printf("failed to write audit log: %v", err)
		return
	}
	defer file.Close()
	if err := json.NewEncoder(file).Encode(entry); err != nil {
		log.Printf("failed to encode audit log entry: %v", err)
	}
}

func contains(items []string, want string) bool {
	for _, item := range items {
		if item == want {
			return true
		}
	}
	return false
}

func (s *Sidecar) policyReloadLoop(interval time.Duration, path string) {
	ticker := time.NewTicker(interval)
	defer ticker.Stop()

	for range ticker.C {
		next, err := loadPolicy(path)
		if err != nil {
			log.Printf("policy reload skipped: %v", err)
			continue
		}
		s.policyMu.Lock()
		s.policy = next
		s.policyMu.Unlock()
		s.lastReload.Set(time.Now().UTC().Format(time.RFC3339))
	}
}

func newProxyTransport(responseHeaderTimeout time.Duration) *http.Transport {
	return &http.Transport{
		Proxy: http.ProxyFromEnvironment,
		DialContext: (&net.Dialer{
			Timeout:   5 * time.Second,
			KeepAlive: 30 * time.Second,
		}).DialContext,
		MaxIdleConns:          100,
		IdleConnTimeout:       90 * time.Second,
		TLSHandshakeTimeout:   10 * time.Second,
		ExpectContinueTimeout: 1 * time.Second,
		ResponseHeaderTimeout: responseHeaderTimeout,
	}
}
