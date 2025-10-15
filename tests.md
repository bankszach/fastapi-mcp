
# Quick Test Commands

```bash
# Health
curl -s https://YOUR_SERVICE_URL/healthz | jq

# List tools
curl -s https://YOUR_SERVICE_URL/ -H 'content-type: application/json'   -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | jq

# Call tool (with format)
curl -s https://YOUR_SERVICE_URL/ -H 'content-type: application/json'   -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"get_time","arguments":{"format":"%Y-%m-%dT%H:%M:%SZ"}}}' | jq
```
