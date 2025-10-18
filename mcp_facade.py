import json
from typing import Any, Dict, Optional, Callable

import httpx
from mcp.server.fastmcp import FastMCP

# Your orchestrator that already aggregates and routes tools
ORCH_BASE = "https://agent-orchestrator-596716165839.us-west2.run.app"

mcp = FastMCP("fastapi-mcp")


# ---------- helpers ----------
async def _fetch_catalog() -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(f"{ORCH_BASE}/catalog")
        r.raise_for_status()
        return r.json()


async def _invoke(payload: Dict[str, Any]) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(f"{ORCH_BASE}/agent/invoke", json=payload)
        try:
            body = r.json()
        except Exception:
            body = {"status": r.status_code, "text": r.text}
        return {"status": r.status_code, "data": body}


# ---------- fallback meta-tool (always available) ----------
@mcp.tool("orchestrator.invoke")
async def orchestrator_invoke(
    direct: Optional[str] = None,
    query: Optional[str] = None,
    args: Optional[Dict[str, Any]] = None,
) -> str:
    if not direct and not query:
        return "error: provide either 'direct' (e.g., 'clock.get_time') or 'query'."

    payload: Dict[str, Any] = {}
    if direct:
        payload["direct"] = direct
        payload["args"] = args or {}
    else:
        payload["query"] = query
        if args:
            payload["args"] = args

    result = await _invoke(payload)
    return json.dumps(result, indent=2, ensure_ascii=False)


# ---------- dynamic registration of downstream tools ----------
def _register_tool(fullname: str) -> None:
    """
    Register a dynamic MCP tool named exactly like the downstream tool, e.g. 'clock.get_time'.
    We intentionally avoid passing schema/description kwargs to keep compatibility with mcp==1.18.
    """

    async def _caller(**kwargs) -> str:
        # Forward all kwargs as args to the direct tool
        result = await _invoke({"direct": fullname, "args": kwargs})
        return json.dumps(result, indent=2, ensure_ascii=False)

    # Decorate the function with the MCP tool name, then bind it
    wrapped = mcp.tool(fullname)(_caller)  # type: ignore[assignment]
    # Note: the decorator returns the same callable; we don't need to keep 'wrapped'


async def register_downstream_tools() -> int:
    """
    Fetch the orchestrator's catalog and register each tool as a native MCP tool.
    Returns the count of tools registered.
    """
    cat = await _fetch_catalog()
    count = 0
    for t in cat.get("tools", []):
        # Expecting fields: server, name
        server = t.get("server")
        name = t.get("name")
        if not server or not name:
            continue
        fullname = f"{server}.{name}"
        _register_tool(fullname)
        count += 1
    return count


# Try to register at import-time but don't crash if the catalog isn't ready yet.
# The server will still start with only 'orchestrator.invoke', and clients can call
# the '/mcp/reload' HTTP route (below) or reconnect later.
try:
    import asyncio

    asyncio.run(register_downstream_tools())
except Exception:
    # Silent fallback: we’ll provide a manual reload route below.
    pass


# Expose ASGI app for MCP over SSE (mount this at /mcp in your FastAPI app)
mcp_asgi_app = mcp.sse_app()


# --------- OPTIONAL: tiny HTTP helper to trigger a catalog reload ----------
# If you want a manual reload without restarting the service,
# you can mount this FastAPI router inside your app, or keep it out.
try:
    from fastapi import APIRouter

    mcp_admin = APIRouter()

    @mcp_admin.post("/mcp/reload")
    async def mcp_reload():
        try:
            # Re-register: this is idempotent (duplicate names just overwrite handlers)
            n = await register_downstream_tools()
            return {"ok": True, "registered": n}
        except Exception as e:
            return {"ok": False, "error": str(e)}
except Exception:
    # If FastAPI isn't available here (e.g., imported before app exists), it's fine.
    mcp_admin = None  # your main app can ignore mounting this
