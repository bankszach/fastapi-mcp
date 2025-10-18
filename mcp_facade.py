import json
from typing import Any, Dict, List

import httpx
from mcp.server.fastmcp import FastMCP
from mcp.server.sse import create_sse_app

# This service’s public URL (no trailing slash)
BASE = "https://fastapi-mcp-596716165839.us-west2.run.app"

mcp = FastMCP("fastapi-mcp")


async def _fetch_catalog() -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(f"{BASE}/catalog")
        r.raise_for_status()
        return r.json()


async def _invoke_direct(server_tool: str, args: Dict[str, Any] | None) -> Dict[str, Any]:
    payload = {"direct": server_tool, "args": args or {}}
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(f"{BASE}/agent/invoke", json=payload)
        try:
            data = r.json()
        except Exception:
            data = {"status": r.status_code, "text": r.text}
        return {"status": r.status_code, "data": data}


@mcp.list_tools
async def list_tools() -> List[Dict[str, Any]]:
    cat = await _fetch_catalog()
    tools = []
    for t in cat.get("tools", []):
        name = f'{t["server"]}.{t["name"]}'
        desc = t.get("description", "")
        schema = t.get("input_schema", {"type": "object"})
        tools.append({"name": name, "description": desc, "inputSchema": schema})
    return tools


@mcp.call_tool
async def call_tool(name: str, arguments: Dict[str, Any] | None = None):
    result = await _invoke_direct(name, arguments or {})
    pretty = json.dumps(result, indent=2, ensure_ascii=False)
    return {
        "content": [{"type": "text", "text": pretty}],
        "isError": result.get("status", 200) >= 400,
    }


# ASGI app serving MCP over SSE at /mcp (will be mounted in app.py)
mcp_asgi_app = create_sse_app(mcp)
