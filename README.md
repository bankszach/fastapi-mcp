
# FastAPI MCP Server (Single Tool)

A minimal, production-ready **MCP server** implemented with **FastAPI** and deployable to **Google Cloud Run**. It exposes a single tool `get_time` via the OpenAI **Model Context Protocol (MCP)** using JSON‑RPC 2.0 over HTTP.

## Features
- `tools/list` and `tools/call` implemented exactly to spec
- Returns **content** (text for humans) and **structuredContent** (JSON for machines)
- Proper JSON‑RPC error codes and input validation with `jsonschema`
- CORS enabled (dev) + optional API key auth via `x-api-key`
- Health check (`/healthz`) and simple request logging
- Dockerfile and one‑command Cloud Run deploy

## Endpoints
- `POST /` — JSON‑RPC 2.0 endpoint for `tools/list` and `tools/call`
- `GET /healthz` — returns `{ "ok": true }`

## Tool
### `get_time`
**Description:** Returns the current UTC timestamp, optionally formatted.

**Input schema:**
```json
{
  "type": "object",
  "properties": {
    "format": {
      "type": "string",
      "description": "strftime format, e.g. %Y-%m-%dT%H:%M:%SZ"
    }
  },
  "required": []
}
```

**Output structuredContent:**
```json
{
  "iso": "2025-01-01T00:00:00Z",
  "formatted": "optional if format passed"
}
```

## Local Dev
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload --port 8000
```

Test:
```bash
curl -s localhost:8000/ -H 'content-type: application/json'   -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | jq

curl -s localhost:8000/ -H 'content-type: application/json'   -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"get_time","arguments":{"format":"%Y-%m-%dT%H:%M:%SZ"}}}' | jq
```

If you set `API_KEY=secret`, include a header: `-H 'x-api-key: secret'`

## Deploy to Google Cloud Run
Option 1 — from source (simplest):
```bash
./deploy.sh
# Set PROJECT_ID, REGION, SERVICE (or export them)
```

Option 2 — via Cloud Build pipeline:
```bash
gcloud builds submit --project $PROJECT_ID --substitutions=_REGION=us-central1,_SERVICE=mcp-clock
```

## Wire into OpenAI Agent Builder
- Add a new **MCP Server** to your agent
- **Server URL**: your Cloud Run URL (e.g. `https://mcp-clock-xxxx-uc.a.run.app`)
- **Label**: `clock`
- **Allowed tools**: `get_time` (or leave empty to allow all)

## License
MIT
