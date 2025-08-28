# MCP Sidecar Usage Examples

This document shows how to use the MCP sidecar with different clients and scenarios.

## Basic Usage

### 1. Setup the Infrastructure

```bash
# Install dependencies
make install-deps

# Set your API key
export MORPH_API_KEY="your-morph-api-key"

# Run the complete setup
make demo
```

### 2. Test the Setup

```bash
# Run smoke tests
make test

# Check sidecar logs
make logs

# View instance status
make status
```

## Client Integration

### Claude Desktop

1. **Copy the configuration**:
   ```bash
   cp clients/claude-desktop.json ~/.config/claude-desktop/mcp-servers/
   ```

2. **Update the API key** in the config file:
   ```json
   {
     "mcpServers": {
       "filesystem": {
         "command": "npx",
         "args": ["-y", "supergateway", "--sse", "https://mcp1.http.cloud.morph.so/mcp1/sse"],
         "env": {
           "MORPH_API_KEY": "your-actual-api-key"
         }
       }
     }
   }
   ```

3. **Restart Claude Desktop**

4. **Verify connection**:
   - Open Claude Desktop
   - Check that MCP servers appear in your tools
   - Try using the filesystem, git, or http tools

### Cursor

1. **Copy the configuration**:
   ```bash
   cp clients/cursor.json ~/.cursor/mcp-servers/
   ```

2. **Update the API key** in the config file

3. **Restart Cursor**

4. **Access MCP servers**:
   - Use Command Palette (Cmd/Ctrl + Shift + P)
   - Type "MCP" to see available commands
   - Access your remote MCP servers

## Advanced Usage

### Epoch Rotation Demo

```bash
# Run the epoch rotation demonstration
make epoch-rotate
```

This shows:
- Starting with epoch-1 (active)
- Rotating to epoch-2 (inactive)
- Access being denied
- Activating epoch-2
- Access restored

### Custom Policy Updates

1. **SSH into the instance**:
   ```bash
   # Get instance info
   cat instance_info.json
   
   # SSH into the instance
   morphcloud instance ssh <instance-id>
   ```

2. **Update the policy**:
   ```bash
   cd /opt/sidecar
   nano policy.yaml
   ```

3. **Restart the sidecar**:
   ```bash
   pkill -f sidecar
   nohup ./sidecar > sidecar.log 2>&1 &
   ```

### Monitoring and Debugging

#### View Sidecar Logs
```bash
make logs
```

#### Check Health Status
```bash
# Get the health URL from instance_info.json
curl -H "Authorization: Bearer $MORPH_API_KEY" \
     https://mcp1.http.cloud.morph.so/health
```

#### Monitor Requests
```bash
# View real-time permits
tail -f /opt/sidecar/permits.jsonl
```

## Troubleshooting

### Common Issues

#### "Connection refused"
- Check if the instance is running: `make status`
- Verify the sidecar is running: `make logs`
- Check firewall rules and port exposure

#### "Authentication failed"
- Verify `MORPH_API_KEY` is set correctly
- Check the API key in your client config
- Ensure the key has proper permissions

#### "MCP server not responding"
- Check MCP server logs: `make logs`
- Verify the sidecar is routing correctly
- Check if the MCP servers are running on the expected ports

### Debug Mode

Enable verbose logging:
```bash
export MORPH_DEBUG=1
make setup
```

### Reset Everything

If you need to start fresh:
```bash
make clean
make setup
```

## Production Considerations

### Security
- Use strong, unique API keys
- Regularly rotate epochs
- Monitor access logs
- Implement rate limiting

### Performance
- Monitor response times
- Scale instances as needed
- Use connection pooling
- Implement caching

### Monitoring
- Set up alerts for policy violations
- Monitor resource usage
- Track request patterns
- Log all access attempts

## API Reference

### Sidecar Endpoints

- `GET /health` - Health check
- `GET /mcp1/sse` - Filesystem MCP server
- `GET /mcp2/sse` - Git MCP server  
- `GET /mcp3/sse` - HTTP MCP server
- `GET /metrics` - Prometheus metrics

### Authentication

All requests require the `Authorization` header:
```
Authorization: Bearer <MORPH_API_KEY>
```

### Response Codes

- `200` - Success
- `401` - Unauthorized (missing/invalid API key)
- `403` - Forbidden (policy violation)
- `404` - Not found
- `500` - Internal server error

## Examples

### Python Client

```python
import requests

api_key = "your-morph-api-key"
headers = {"Authorization": f"Bearer {api_key}"}

# Test health
response = requests.get(
    "https://mcp1.http.cloud.morph.so/health",
    headers=headers
)
print(f"Health: {response.status_code}")

# Test MCP endpoint
response = requests.get(
    "https://mcp1.http.cloud.morph.so/mcp1/sse",
    headers=headers
)
print(f"MCP: {response.status_code}")
```

### cURL Examples

```bash
# Health check
curl -H "Authorization: Bearer $MORPH_API_KEY" \
     https://mcp1.http.cloud.morph.so/health

# MCP endpoint
curl -H "Authorization: Bearer $MORPH_API_KEY" \
     https://mcp1.http.cloud.morph.so/mcp1/sse
```

### JavaScript/Node.js

```javascript
const fetch = require('node-fetch');

const apiKey = 'your-morph-api-key';
const headers = { 'Authorization': `Bearer ${apiKey}` };

// Test health
fetch('https://mcp1.http.cloud.morph.so/health', { headers })
  .then(response => console.log('Health:', response.status))
  .catch(error => console.error('Error:', error));
```

## Support

For issues or questions:
1. Check the logs: `make logs`
2. Review this documentation
3. Check the troubleshooting section
4. Open an issue on GitHub
