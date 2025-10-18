
import logging
import os
from typing import Any, Dict, Optional

from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from jsonschema import validate, ValidationError

from tool_impl import get_time_impl
from mcp_facade import mcp_asgi_app

logger = logging.getLogger("mcp")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

app = FastAPI(title="FastAPI MCP Server")

# Serve MCP over Server-Sent Events at /mcp for LM Studio clients.
app.mount("/mcp", mcp_asgi_app)

# --- CORS (relax in dev; restrict in prod) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
)

# --- Optional API key auth via header x-api-key ---
API_KEY = os.getenv("API_KEY")
COMMIT_SHA = os.getenv("COMMIT_SHA", "unknown")

def check_auth(request: Request):
    if not API_KEY:
        return
    if request.headers.get("x-api-key") != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")


# --- JSON-RPC models ---
class JsonRpcRequest(BaseModel):
    jsonrpc: str
    id: Optional[int | str] = None
    method: str
    params: Optional[Dict[str, Any]] = None

def rpc_result(id_val, result: Dict[str, Any]):
    return {"jsonrpc": "2.0", "id": id_val, "result": result}

def rpc_error(id_val, code: int, message: str):
    return {"jsonrpc": "2.0", "id": id_val, "error": {"code": code, "message": message}}


# --- Tool definition ---
TOOL_DEF = {
    "name": "get_time",
    "title": "UTC Clock",
    "description": "Return the current UTC timestamp. Optionally format it.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "format": {
                "type": "string",
                "description": "strftime format, e.g. %Y-%m-%dT%H:%M:%SZ"
            }
        },
        "additionalProperties": False,
        "required": []
    },
    "outputSchema": {
        "type": "object",
        "properties": {
            "iso": {"type": "string", "description": "ISO-8601 UTC timestamp"},
            "formatted": {"type": "string", "description": "Formatted timestamp (if requested)"}
        },
        "required": ["iso"],
        "additionalProperties": True
    }
}


@app.get("/healthz")
async def healthz():
    return {"ok": True}

@app.get("/")
async def root():
    return {
        "name": "FastAPI MCP Server",
        "status": "ok",
        "message": "Use POST / for JSON-RPC 2.0 tools.list and tools.call methods.",
    }

@app.get("/version")
async def version():
    return {"commit": COMMIT_SHA}


@app.post("/")
async def handle_rpc(request: Request):
    check_auth(request)

    try:
        body = await request.json()
    except Exception:
        # -32700 Parse error
        return rpc_error(None, -32700, "Parse error")

    try:
        rpc = JsonRpcRequest(**body)
    except Exception:
        # -32600 Invalid Request
        return rpc_error(body.get("id") if isinstance(body, dict) else None, -32600, "Invalid Request")

    if rpc.jsonrpc != "2.0":
        return rpc_error(rpc.id, -32600, "Invalid Request: jsonrpc must be '2.0'")

    method = rpc.method
    params = rpc.params or {}

    logger.info("rpc method=%s params=%s", method, params)

    if method == "tools/list":
        result = {"tools": [TOOL_DEF]}
        return rpc_result(rpc.id, result)

    if method == "tools/call":
        name = params.get("name")
        if not name:
            return rpc_error(rpc.id, -32602, "Missing tool name")
        if name != TOOL_DEF["name"]:
            return rpc_error(rpc.id, -32601, f"Unknown tool: {name}")

        arguments = params.get("arguments", {}) or {}

        # Validate against input schema
        try:
            validate(instance=arguments, schema=TOOL_DEF["inputSchema"])
        except ValidationError as ve:
            return rpc_error(rpc.id, -32602, f"Invalid params: {ve.message}")

        try:
            data = get_time_impl(arguments.get("format"))
        except Exception as e:
            logger.exception("Tool execution failed")
            # -32000 Server error (custom range)
            return rpc_error(rpc.id, -32000, f"Tool execution error: {e}")

        # Per MCP: content (for humans) + structuredContent (for machines)
        text = data.get("formatted") or data["iso"]
        result = {
            "content": [{"type": "text", "text": text}],
            "structuredContent": data
        }
        return rpc_result(rpc.id, result)

    # -32601 Method not found
    return rpc_error(rpc.id, -32601, "Method not found")
