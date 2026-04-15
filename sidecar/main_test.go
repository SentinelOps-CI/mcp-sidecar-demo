package main

import (
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestEvaluateRequestPermitted(t *testing.T) {
	var cfg Config
	cfg.Auth.Required = true
	cfg.Auth.Header = "Authorization"
	cfg.Auth.Prefix = "Bearer "
	cfg.Auth.Token = "abc123"

	s := &Sidecar{
		config: cfg,
		policy: Policy{
			Epochs: map[string]Epoch{
				"epoch-1": {
					Active:      true,
					ExpiresAt:   "2099-01-01T00:00:00Z",
					Permissions: []string{"call"},
				},
			},
			Roles: map[string]Role{
				"default": {
					Epochs:      []string{"epoch-1"},
					Tools:       []string{"filesystem"},
					Permissions: []string{"call"},
				},
			},
		},
	}
	req := httptest.NewRequest(http.MethodGet, "/mcp1/sse", nil)
	req.Header.Set("Authorization", "Bearer abc123")

	epoch, reason := s.evaluateRequest(req, "filesystem")
	if reason != "permitted" {
		t.Fatalf("expected permitted, got %s", reason)
	}
	if epoch != "epoch-1" {
		t.Fatalf("expected epoch-1, got %s", epoch)
	}
}

func TestEvaluateRequestDeniedWithoutToken(t *testing.T) {
	var cfg Config
	cfg.Auth.Required = true
	cfg.Auth.Header = "Authorization"
	cfg.Auth.Prefix = "Bearer "

	s := &Sidecar{
		config: cfg,
		policy: Policy{
			Epochs: map[string]Epoch{
				"epoch-1": {
					Active:      true,
					ExpiresAt:   "2099-01-01T00:00:00Z",
					Permissions: []string{"call"},
				},
			},
			Roles: map[string]Role{
				"default": {
					Epochs:      []string{"epoch-1"},
					Tools:       []string{"filesystem"},
					Permissions: []string{"call"},
				},
			},
		},
	}
	req := httptest.NewRequest(http.MethodGet, "/mcp1/sse", nil)

	_, reason := s.evaluateRequest(req, "filesystem")
	if reason != "missing_or_invalid_token" {
		t.Fatalf("expected missing_or_invalid_token, got %s", reason)
	}
}

func TestWriteAuditRedactsAuthorization(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "audit.jsonl")

	var cfg Config
	cfg.Audit.Enabled = true
	cfg.Audit.OutputFile = path
	cfg.Audit.IncludeHeaders = true
	cfg.Auth.Header = "Authorization"

	s := &Sidecar{config: cfg}
	req := httptest.NewRequest(http.MethodGet, "/mcp1/sse", nil)
	req.Header.Set("Authorization", "Bearer ultra-secret-token")
	s.writeAudit(req, "permitted", "permitted", "epoch-1", "filesystem")

	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("read audit: %v", err)
	}
	if strings.Contains(string(data), "ultra-secret") {
		t.Fatalf("authorization material must not appear in audit logs")
	}
	if !strings.Contains(string(data), "redacted") {
		t.Fatalf("expected redacted marker in audit payload")
	}
}

func TestLoadConfigRejectsInvalidTarget(t *testing.T) {
	dir := t.TempDir()
	cfgPath := filepath.Join(dir, "config.yaml")
	configYAML := `
server:
  port: 8080
policy:
  file: "/tmp/policy.yaml"
mcp_servers:
  filesystem:
    target: "://bad-target"
`
	if err := os.WriteFile(cfgPath, []byte(configYAML), 0o644); err != nil {
		t.Fatalf("write config: %v", err)
	}

	_, err := loadConfig(cfgPath)
	if err == nil {
		t.Fatalf("expected invalid target error")
	}
}

func TestLoadConfigRejectsInvalidReloadInterval(t *testing.T) {
	dir := t.TempDir()
	cfgPath := filepath.Join(dir, "config.yaml")
	configYAML := `
server:
  port: 8080
policy:
  file: "/tmp/policy.yaml"
  reload_interval: "not-a-duration"
mcp_servers:
  filesystem:
    target: "http://localhost:8000"
`
	if err := os.WriteFile(cfgPath, []byte(configYAML), 0o644); err != nil {
		t.Fatalf("write config: %v", err)
	}

	_, err := loadConfig(cfgPath)
	if err == nil {
		t.Fatalf("expected invalid reload interval error")
	}
}

func TestLoadPolicyRejectsMissingDefaultRole(t *testing.T) {
	dir := t.TempDir()
	policyPath := filepath.Join(dir, "policy.yaml")
	policyYAML := `
epochs:
  epoch-1:
    active: true
    expires_at: "2099-01-01T00:00:00Z"
    permissions: [call]
roles:
  admin:
    epochs: [epoch-1]
    tools: [filesystem]
    permissions: [call]
`
	if err := os.WriteFile(policyPath, []byte(policyYAML), 0o644); err != nil {
		t.Fatalf("write policy: %v", err)
	}

	_, err := loadPolicy(policyPath)
	if err == nil {
		t.Fatalf("expected missing default role error")
	}
}

func TestLoadPolicyRejectsUnknownEpochReference(t *testing.T) {
	dir := t.TempDir()
	policyPath := filepath.Join(dir, "policy.yaml")
	policyYAML := `
epochs:
  epoch-1:
    active: true
    expires_at: "2099-01-01T00:00:00Z"
    permissions: [call]
roles:
  default:
    epochs: [epoch-x]
    tools: [filesystem]
    permissions: [call]
`
	if err := os.WriteFile(policyPath, []byte(policyYAML), 0o644); err != nil {
		t.Fatalf("write policy: %v", err)
	}

	_, err := loadPolicy(policyPath)
	if err == nil {
		t.Fatalf("expected unknown epoch reference error")
	}
}
