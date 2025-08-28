#!/usr/bin/env python3
"""
MCP Sidecar Demo Setup Script
Creates a Morph VM with multiple MCP servers behind an authenticated sidecar
"""

import os
import time
import subprocess
import json
from pathlib import Path
from morphcloud.api import MorphCloudClient


def check_dependencies():
    """Check if required dependencies are installed"""
    try:
        import morphcloud

        print("✓ morphcloud SDK installed")
    except ImportError:
        print("❌ morphcloud SDK not found. Install with: pip install morphcloud")
        return False

    try:
        result = subprocess.run(["npx", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ npx available")
        else:
            print("❌ npx not available. Install Node.js")
            return False
    except FileNotFoundError:
        print("❌ npx not found. Install Node.js")
        return False

    return True


def create_mcp_devbox_snapshot(client):
    """Create a snapshot with MCP development environment"""
    print("Creating MCP devbox snapshot...")

    # Start from minimal image
    base_snapshot = client.snapshots.create(
        image_id="morphvm-minimal",
        vcpus=2,
        memory=2048,
        disk_size=2048,
        metadata={"role": "mcp-demo", "epoch": "1"},
    )

    print(f"✓ Base snapshot created: {base_snapshot.id}")
    return base_snapshot


def install_mcp_servers(snapshot):
    """Install MCP servers on the snapshot"""
    print("Installing MCP servers...")

    # Install Python and pip
    python_snapshot = snapshot.exec(
        """
        apt-get update && 
        apt-get install -y python3 python3-pip python3-venv curl git &&
        python3 -m pip install --upgrade pip
    """
    )

    # Install MCP servers
    mcp_snapshot = python_snapshot.exec(
        """
        python3 -m pip install mcp-server-filesystem mcp-server-git mcp-server-http &&
        mkdir -p /opt/mcp-servers
    """
    )

    # Create MCP server configurations
    config_snapshot = mcp_snapshot.exec(
        """
        cat > /opt/mcp-servers/filesystem.json << 'EOF'
        {
            "mcpServers": {
                "filesystem": {
                    "command": "python3",
                    "args": ["-m", "mcp.server.filesystem"],
                    "env": {
                        "MCP_FILESYSTEM_ROOT": "/home/user"
                    }
                }
            }
        }
        EOF
        
        cat > /opt/mcp-servers/git.json << 'EOF'
        {
            "mcpServers": {
                "git": {
                    "command": "python3",
                    "args": ["-m", "mcp.server.git"],
                    "env": {
                        "MCP_GIT_ROOT": "/home/user"
                    }
                }
            }
        }
        EOF
        
        cat > /opt/mcp-servers/http.json << 'EOF'
        {
            "mcpServers": {
                "http": {
                    "command": "python3",
                    "args": ["-m", "mcp.server.http"],
                    "env": {
                        "MCP_HTTP_ROOT": "/home/user"
                    }
                }
            }
        }
        EOF
    """
    )

    print("✓ MCP servers installed and configured")
    return config_snapshot


def create_sidecar_snapshot(snapshot):
    """Create snapshot with the permissioning sidecar"""
    print("Installing permissioning sidecar...")

    # Install Go
    go_snapshot = snapshot.exec(
        """
        curl -fsSL https://go.dev/dl/go1.21.0.linux-amd64.tar.gz -o go.tar.gz &&
        tar -C /usr/local -xzf go.tar.gz &&
        echo 'export PATH=$PATH:/usr/local/go/bin' >> /home/user/.bashrc &&
        export PATH=$PATH:/usr/local/go/bin &&
        go version
    """
    )

    # Create sidecar source
    sidecar_snapshot = go_snapshot.exec(
        """
        mkdir -p /opt/sidecar &&
        cat > /opt/sidecar/main.go << 'EOF'
        package main
        
        import (
            "encoding/json"
            "fmt"
            "io"
            "log"
            "net/http"
            "net/http/httputil"
            "net/url"
            "os"
            "strings"
            "time"
        )
        
        type Policy struct {
            Epochs map[string]Epoch `json:"epochs"`
            Roles  map[string]Role  `json:"roles"`
        }
        
        type Epoch struct {
            Active    bool      `json:"active"`
            ExpiresAt time.Time `json:"expires_at"`
            Permissions []string `json:"permissions"`
        }
        
        type Role struct {
            Epochs []string `json:"epochs"`
            Tools  []string `json:"tools"`
        }
        
        type RequestLog struct {
            Timestamp time.Time `json:"timestamp"`
            RequestID string    `json:"request_id"`
            Method    string    `json:"method"`
            Path      string    `json:"path"`
            ClientIP  string    `json:"client_ip"`
            Decision  string    `json:"decision"`
            Epoch     string    `json:"epoch"`
            Witness   string    `json:"witness"`
            CertRecord string   `json:"cert_record"`
        }
        
        var (
            policy     Policy
            requestLog []RequestLog
            currentEpoch = "epoch-1"
        )
        
        func loadPolicy() error {
            data, err := os.ReadFile("/opt/sidecar/policy.yaml")
            if err != nil {
                return err
            }
            
            // Simple YAML parsing for demo
            policy = Policy{
                Epochs: map[string]Epoch{
                    "epoch-1": {
                        Active: true,
                        ExpiresAt: time.Now().Add(24 * time.Hour),
                        Permissions: []string{"read", "write", "call"},
                    },
                },
                Roles: map[string]Role{
                    "default": {
                        Epochs: []string{"epoch-1"},
                        Tools:  []string{"filesystem", "git", "http"},
                    },
                },
            }
            return nil
        }
        
        func checkPermission(method, path string) (bool, string) {
            epoch, exists := policy.Epochs[currentEpoch]
            if !exists || !epoch.Active {
                return false, "epoch-inactive"
            }
            
            if time.Now().After(epoch.ExpiresAt) {
                return false, "epoch-expired"
            }
            
            // Simple permission check
            if method == "GET" && strings.Contains(path, "/sse") {
                return true, "permitted"
            }
            
            return false, "denied"
        }
        
        func logRequest(r *http.Request, decision, epoch string) {
            log := RequestLog{
                Timestamp: time.Now(),
                RequestID: fmt.Sprintf("req-%d", time.Now().UnixNano()),
                Method:    r.Method,
                Path:      r.URL.Path,
                ClientIP:  r.RemoteAddr,
                Decision:  decision,
                Epoch:     epoch,
                Witness:   "sidecar-v1",
                CertRecord: fmt.Sprintf("CERT-V1:%s:%s:%s", decision, epoch, time.Now().Format("2006-01-02T15:04:05Z")),
            }
            
            requestLog = append(requestLog, log)
            
            // Write to permits.jsonl
            if f, err := os.OpenFile("/opt/sidecar/permits.jsonl", os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644); err == nil {
                defer f.Close()
                json.NewEncoder(f).Encode(log)
            }
        }
        
        func proxyHandler(target string) http.HandlerFunc {
            return func(w http.ResponseWriter, r *http.Request) {
                decision, epoch := checkPermission(r.Method, r.URL.Path)
                
                logRequest(r, decision, epoch)
                
                if !decision {
                    http.Error(w, "Access denied", http.StatusForbidden)
                    return
                }
                
                // Proxy to target
                targetURL, _ := url.Parse(target)
                proxy := httputil.NewSingleHostReverseProxy(targetURL)
                proxy.ServeHTTP(w, r)
            }
        }
        
        func main() {
            if err := loadPolicy(); err != nil {
                log.Fatal("Failed to load policy:", err)
            }
            
            // Create permits.jsonl file
            os.WriteFile("/opt/sidecar/permits.jsonl", []byte(""), 0644)
            
            // Start MCP servers
            go func() {
                subprocess := exec.Command("python3", "-m", "mcp.server.filesystem")
                subprocess.Dir = "/opt/mcp-servers"
                subprocess.Start()
            }()
            
            go func() {
                subprocess := exec.Command("python3", "-m", "mcp.server.git")
                subprocess.Dir = "/opt/mcp-servers"
                subprocess.Start()
            }()
            
            go func() {
                subprocess := exec.Command("python3", "-m", "mcp.server.http")
                subprocess.Dir = "/opt/mcp-servers"
                subprocess.Start()
            }()
            
            // Setup routes
            http.HandleFunc("/mcp1/sse", proxyHandler("http://localhost:8000"))
            http.HandleFunc("/mcp2/sse", proxyHandler("http://localhost:8001"))
            http.HandleFunc("/mcp3/sse", proxyHandler("http://localhost:8002"))
            
            // Health check
            http.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
                w.Write([]byte("sidecar healthy"))
            })
            
            log.Println("Sidecar starting on :8080")
            log.Fatal(http.ListenAndServe(":8080", nil))
        }
        EOF
    """
    )

    # Build sidecar
    built_snapshot = sidecar_snapshot.exec(
        """
        cd /opt/sidecar &&
        export PATH=$PATH:/usr/local/go/bin &&
        go mod init sidecar &&
        go mod tidy &&
        go build -o sidecar main.go
    """
    )

    print("✓ Permissioning sidecar built")
    return built_snapshot


def start_instance_and_expose_services(client, snapshot):
    """Start instance and expose HTTP services"""
    print("Starting instance...")

    instance = client.instances.start(snapshot_id=snapshot.id)
    instance.wait_until_ready()

    print("✓ Instance ready")

    # Start sidecar
    with instance.ssh() as ssh:
        ssh.run("cd /opt/sidecar && nohup ./sidecar > sidecar.log 2>&1 &")
        time.sleep(3)  # Wait for sidecar to start

        # Start MCP servers on different ports
        ssh.run(
            "cd /opt/mcp-servers && nohup python3 -m mcp.server.filesystem --port 8000 > filesystem.log 2>&1 &"
        )
        ssh.run(
            "cd /opt/mcp-servers && nohup python3 -m mcp.server.git --port 8001 > git.log 2>&1 &"
        )
        ssh.run(
            "cd /opt/mcp-servers && nohup python3 -m mcp.server.http --port 8002 > http.log 2>&1 &"
        )

        time.sleep(2)  # Wait for servers to start

    # Expose authenticated HTTP services
    print("Exposing HTTP services...")

    mcp1_url = instance.expose_http_service("mcp1", 8080, auth_mode="api_key")
    mcp2_url = instance.expose_http_service("mcp2", 8080, auth_mode="api_key")
    mcp3_url = instance.expose_http_service("mcp3", 8080, auth_mode="api_key")

    print("✓ HTTP services exposed")

    return instance, {"mcp1": mcp1_url, "mcp2": mcp2_url, "mcp3": mcp3_url}


def create_client_configs(urls):
    """Create client configuration files"""
    print("Creating client configurations...")

    # Create clients directory
    Path("clients").mkdir(exist_ok=True)

    # Claude Desktop config
    claude_config = {
        "mcpServers": {
            "filesystem": {
                "command": "npx",
                "args": ["-y", "supergateway", "--sse", f"{urls['mcp1']}/mcp1/sse"],
            },
            "git": {
                "command": "npx",
                "args": ["-y", "supergateway", "--sse", f"{urls['mcp2']}/mcp2/sse"],
            },
            "http": {
                "command": "npx",
                "args": ["-y", "supergateway", "--sse", f"{urls['mcp3']}/mcp3/sse"],
            },
        }
    }

    with open("clients/claude-desktop.json", "w") as f:
        json.dump(claude_config, f, indent=2)

    # Cursor config
    cursor_config = {
        "mcpServers": {
            "filesystem": {
                "command": "npx",
                "args": ["-y", "supergateway", "--sse", f"{urls['mcp1']}/mcp1/sse"],
            },
            "git": {
                "command": "npx",
                "args": ["-y", "supergateway", "--sse", f"{urls['mcp2']}/mcp2/sse"],
            },
            "http": {
                "command": "npx",
                "args": ["-y", "supergateway", "--sse", f"{urls['mcp3']}/mcp3/sse"],
            },
        }
    }

    with open("clients/cursor.json", "w") as f:
        json.dump(cursor_config, f, indent=2)

    print("✓ Client configurations created")


def main():
    """Main setup function"""
    print("🚀 MCP Sidecar Demo Setup")
    print("=" * 50)

    # Check dependencies
    if not check_dependencies():
        return

    # Check API key
    api_key = os.getenv("MORPH_API_KEY")
    if not api_key:
        print("❌ MORPH_API_KEY environment variable not set")
        print("Set it with: export MORPH_API_KEY='your-api-key'")
        return

    try:
        # Initialize client
        client = MorphCloudClient()

        # Create snapshot chain
        base_snapshot = create_mcp_devbox_snapshot(client)
        mcp_snapshot = install_mcp_servers(base_snapshot)
        sidecar_snapshot = create_sidecar_snapshot(mcp_snapshot)

        # Start instance and expose services
        instance, urls = start_instance_and_expose_services(client, sidecar_snapshot)

        # Create client configs
        create_client_configs(urls)

        print("\n🎉 Setup Complete!")
        print("=" * 50)
        print(f"Instance ID: {instance.id}")
        print(f"MCP1 URL: {urls['mcp1']}/mcp1/sse")
        print(f"MCP2 URL: {urls['mcp2']}/mcp2/sse")
        print(f"MCP3 URL: {urls['mcp3']}/mcp3/sse")
        print(f"Sidecar Health: {urls['mcp1']}/health")
        print("\nClient configs created in clients/ directory")
        print("Use these URLs in Claude Desktop or Cursor with supergateway")

        # Save instance info
        with open("instance_info.json", "w") as f:
            json.dump(
                {
                    "instance_id": instance.id,
                    "snapshot_id": sidecar_snapshot.id,
                    "urls": urls,
                    "created_at": time.time(),
                },
                f,
                indent=2,
            )

        print("\nInstance info saved to instance_info.json")

    except Exception as e:
        print(f"❌ Setup failed: {e}")
        raise


if __name__ == "__main__":
    main()
