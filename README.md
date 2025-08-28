# MCP Sidecar Demo: "Hello, Remote MCP" on Morph

> **Multiple SSE MCP servers behind a permissioning sidecar enforcing PERM-UNIFY-R1 (Call/Read/Write/Grant + epochs + IFC witnesses)**

[![Morph Cloud](https://img.shields.io/badge/Morph-Cloud-blue)](https://cloud.morph.so)
[![MCP](https://img.shields.io/badge/MCP-Protocol-green)](https://modelcontextprotocol.io)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

## 90-Second Tutorial

### 1. Setup (30 seconds)
```bash
# Install dependencies
make install-deps

# Set your Morph API key
export MORPH_API_KEY="your-api-key-here"

# Run the complete demo
make demo
```

### 2. What Happens (30 seconds)
- **Morph VM** spins up with MCP devbox
- **3 MCP servers** install (filesystem, git, http)
- **Permissioning sidecar** starts with PERM-UNIFY-R1 policy
- **Authenticated HTTP endpoints** expose via Morph Cloud
- **Client configs** generate for Claude Desktop & Cursor

### 3. Use It (30 seconds)
- Copy configs to your MCP clients
- Connect via supergateway (stdio↔SSE bridge)
- Enjoy authenticated, policy-enforced MCP access

## Scope

This demo creates a **production-ready MCP infrastructure** on Morph Cloud:

- **Morph VM** with MCP development environment
- **2-3 MCP servers** (filesystem, git, http)
- **Authenticated HTTP services** (bearer token auth)
- **Permissioning sidecar** with policy enforcement
- **PERM-UNIFY-R1 schema** (roles, tools, epochs, witnesses)
- **Reverse proxy** with request logging
- **CERT-V1 records** for audit trails
- **Ready configs** for Claude Desktop & Cursor

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Claude/Cursor │    │   Supergateway   │    │  Morph Cloud    │
│   (MCP Client)  │◄──►│  (stdio↔SSE)     │◄──►│  (HTTP Service) │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                         │
                                                         ▼
                                              ┌──────────────────┐
                                              │  Permissioning   │
                                              │    Sidecar       │
                                              │  (Policy Check)  │
                                              └──────────────────┘
                                                         │
                                                         ▼
                                              ┌──────────────────┐
                                              │   MCP Servers    │
                                              │ ┌─────────────┐  │
                                              │ │filesystem   │  │
                                              │ │git          │  │
                                              │ │http         │  │
                                              │ └─────────────┘  │
                                              └──────────────────┘
```

## Project Structure

```
mcp-sidecar-demo/
├── setup/
│   └── setup_mcp.py          # One-liner VM creation & setup
├── config/
│   └── policy.yaml            # PERM-UNIFY-R1 policy schema
├── clients/
│   ├── claude-desktop.json    # Claude Desktop MCP config
│   └── cursor.json            # Cursor MCP config
├── Makefile                   # Easy commands for demo
├── instance_info.json         # Generated instance details
└── README.md                  # This file
```

## Quick Start

### Prerequisites
- **Morph Cloud account** ([sign up](https://cloud.morph.so))
- **Python 3.8+** with pip
- **Node.js** (for npx/supergateway)
- **MORPH_API_KEY** environment variable

### Installation
```bash
# Clone the repo
git clone https://github.com/SentinelOps-CI/mcp-sidecar-demo.git
cd mcp-sidecar-demo

# Install dependencies
make install-deps

# Set your API key
export MORPH_API_KEY="your-morph-api-key"

# Run the demo
make demo
```

### What You Get
After running `make demo`, you'll have:

1. **Running Morph VM** with MCP infrastructure
2. **3 authenticated HTTP endpoints**:
   - `https://mcp1.http.cloud.morph.so/mcp1/sse`
   - `https://mcp2.http.cloud.morph.so/mcp2/sse`
   - `https://mcp3.http.cloud.morph.so/mcp3/sse`
3. **Client configs** ready for Claude Desktop & Cursor
4. **Permissioning sidecar** enforcing PERM-UNIFY-R1 policy

## Demo Commands

```bash
make help           # Show all available commands
make setup          # Create VM and setup MCP servers
make test           # Run smoke tests
make logs           # Show sidecar logs and permits
make epoch-rotate   # Demonstrate epoch rotation
make status         # Check instance status
make clean          # Stop instance and cleanup
```

## Policy Enforcement

### PERM-UNIFY-R1 Schema
The sidecar implements a minimal but complete permission schema:

```yaml
epochs:
  epoch-1:
    active: true
    expires_at: "2025-12-31T23:59:59Z"
    permissions: [read, write, call, grant]

roles:
  default:
    epochs: [epoch-1]
    tools: [filesystem, git, http]
    permissions: [read, write, call]

witnesses:
  sidecar-v1:
    type: "sidecar"
    capabilities: [policy_enforcement, request_logging, cert_generation]
```

### Request Flow
1. **Client request** → Morph Cloud HTTP service
2. **Authentication** → Bearer token validation
3. **Policy check** → Sidecar validates permissions
4. **Decision** → Allow/deny based on epoch + role
5. **Logging** → Request logged with CERT-V1 record
6. **Proxy** → Forward to appropriate MCP server

## Epoch Rotation Demo

See the power of time-based permissions in action:

```bash
# Run the epoch rotation demo
make epoch-rotate
```

**What happens:**
1. **Start**: Access allowed with `epoch-1` (active)
2. **Rotate**: Switch to `epoch-2` (inactive)
3. **Result**: Access denied (epoch inactive)
4. **Activate**: Enable `epoch-2`
5. **Success**: Access restored with new epoch

**Output example:**
```
🔄 Demonstrating epoch rotation...
Current epoch: epoch-1 (active)
Testing access...

🔄 Rotating to epoch-2...
✅ Epoch rotated to epoch-2
Testing access with new epoch...

🎉 Epoch rotation demo completed!
```

## Monitoring & Logs

### View Sidecar Activity
```bash
make logs
```

**Shows:**
- Sidecar logs (policy decisions)
- Request permits (JSONL format)
- MCP server logs
- CERT-V1 audit records

### Sample Log Output
```json
{
  "timestamp": "2025-01-20T10:30:00Z",
  "request_id": "req-1705750200000000000",
  "method": "GET",
  "path": "/mcp1/sse",
  "client_ip": "192.168.1.100",
  "decision": "permitted",
  "epoch": "epoch-1",
  "witness": "sidecar-v1",
  "cert_record": "CERT-V1:permitted:epoch-1:2025-01-20T10:30:00Z"
}
```

## Client Integration

### Claude Desktop
1. Copy `clients/claude-desktop.json` to your Claude Desktop config
2. Update `MORPH_API_KEY` in the config
3. Restart Claude Desktop
4. MCP servers appear in your tools

### Cursor
1. Copy `clients/cursor.json` to your Cursor MCP config
2. Update `MORPH_API_KEY` in the config
3. Restart Cursor
4. Access MCP servers via the command palette

### Supergateway
The configs use [supergateway](https://github.com/supergateway/supergateway) to bridge:
- **stdio** (what Claude/Cursor expect)
- **SSE** (what Morph Cloud provides)

## Snapshot Management

### Metadata Tagging
Snapshots are tagged for easy management:

```json
{
  "role": "mcp-demo",
  "epoch": "1",
  "created_at": "2025-01-20T10:00:00Z"
}
```

### Epoch Rotation
To rotate epochs:
1. **Stop instance** from current snapshot
2. **Start instance** from new epoch snapshot
3. **Update policy** in sidecar
4. **Restart sidecar** with new configuration

## Troubleshooting

### Common Issues

**"MORPH_API_KEY not set"**
```bash
export MORPH_API_KEY="your-api-key"
```

**"morphcloud SDK not found"**
```bash
pip install morphcloud
```

**"npx not available"**
```bash
# Install Node.js from https://nodejs.org/
```

**Instance not starting**
```bash
make status          # Check instance status
make logs            # View sidecar logs
```

### Debug Mode
Enable verbose logging:
```bash
# Set environment variable
export MORPH_DEBUG=1

# Run setup
make setup
```

## Performance

### Resource Usage
- **VM Specs**: 2 vCPUs, 2GB RAM, 2GB disk
- **Startup Time**: ~2-3 minutes (first time)
- **Response Time**: <100ms (sidecar overhead)
- **Concurrent Users**: 10+ (configurable)

### Scaling
- **Horizontal**: Add more MCP servers
- **Vertical**: Increase VM resources
- **Load Balancing**: Multiple sidecar instances

## Contributing

### Development Setup
```bash
# Clone and setup
git clone https://github.com/SentinelOps-CI/mcp-sidecar-demo.git
cd mcp-sidecar-demo

# Install dev dependencies
pip install -e ".[dev]"

# Run tests
make test
```

### Architecture Decisions
- **Go sidecar**: Performance and simplicity
- **Python setup**: Rapid prototyping
- **Morph Cloud**: Managed infrastructure
- **Supergateway**: Proven SSE bridge

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Acknowledgments

- **Morph Labs** for the amazing cloud platform
- **MCP Community** for the protocol specification
- **Supergateway** for the SSE bridge implementation


*Questions? Issues? [Open an issue](https://github.com/SentinelOps-CI/mcp-sidecar-demo/issues)*
