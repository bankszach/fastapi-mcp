from __future__ import annotations
import os
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from mcp.server.fastapi import FastAPITransport
from .server import create_server

load_dotenv()
NAME = os.getenv("SERVER_NAME", "fastapi-mcp")
VERSION = os.getenv("SERVER_VERSION", "0.1.0")
API_KEY = os.getenv("API_KEY")

def mount_mcp_root(app: FastAPI) -> None:
    """Mounts Streamable HTTP MCP at '/' without touching your existing SSE route."""
    transport = FastAPITransport(app)
    server = create_server(NAME, VERSION)

    @transport.route("/")
    async def mcp_root(req: Request) -> Response:
        if API_KEY and req.headers.get("x-api-key") != API_KEY:
            raise HTTPException(status_code=401, detail="Unauthorized")
        return await transport.handle(req, server)

def attach_healthz(app: FastAPI) -> None:
    @app.get("/healthz")
    async def healthz():
        return JSONResponse({"status": "ok", "name": NAME, "version": VERSION})
