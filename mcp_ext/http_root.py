from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Tuple

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.types import ContentBlock
from pydantic import BaseModel, Field, ValidationError

from .policy import get_policy
from .server import create_server

load_dotenv()

NAME = os.getenv("SERVER_NAME", "fastapi-mcp")
VERSION = os.getenv("SERVER_VERSION", "0.1.0")
API_KEY = os.getenv("API_KEY")
logger = logging.getLogger(__name__)


class ToolCallPayload(BaseModel):
    tool: str
    arguments: Dict[str, Any] = Field(default_factory=dict)


def _serialize_content(blocks: List[ContentBlock]) -> List[Dict[str, Any]]:
    """Convert content blocks into JSON-serializable dictionaries."""
    return [block.model_dump(mode="json") for block in blocks]


def _format_response(
    tool_name: str,
    result: Tuple[List[ContentBlock], Dict[str, Any]]
    | List[ContentBlock]
    | Dict[str, Any]
    | None,
) -> Dict[str, Any]:
    """Normalize tool results into a consistent response body."""
    content_blocks: List[ContentBlock] = []
    structured: Dict[str, Any] | None = None

    if isinstance(result, tuple):
        content_blocks, structured = result
    elif isinstance(result, list):
        content_blocks = result
    elif isinstance(result, dict):
        structured = result

    body: Dict[str, Any] = {
        "tool": tool_name,
        "content": _serialize_content(content_blocks),
    }

    if structured is not None:
        body["structured"] = structured

    policy = get_policy(tool_name)
    if policy is not None:
        body["meta"] = {"policy": policy}

    return body


def mount_mcp_root(app: FastAPI) -> None:
    """Expose a simple HTTP facade for MCP tools at the service root."""
    server: FastMCP = create_server(NAME, VERSION)

    @app.get("/")
    async def root_status() -> Dict[str, Any]:
        tools = await server.list_tools()
        return {
            "status": "ok",
            "name": NAME,
            "version": VERSION,
            "tools": [tool.name for tool in tools],
        }

    @app.options("/")
    async def root_options() -> Response:
        return Response(status_code=status.HTTP_200_OK)

    @app.post("/")
    async def invoke_tool(payload: ToolCallPayload, request: Request) -> JSONResponse:
        if API_KEY and request.headers.get("x-api-key") != API_KEY:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

        try:
            result = await server.call_tool(payload.tool, payload.arguments or {})
        except ToolError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except ValidationError as exc:
            logger.warning("Invalid arguments for tool %s: %s", payload.tool, exc)
            return JSONResponse(
                {"error": "invalid_arguments", "details": exc.errors()},
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("Unhandled error invoking %s", payload.tool)
            return JSONResponse(
                {"error": "tool_execution_failed", "message": str(exc)},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        response_body = _format_response(payload.tool, result)
        return JSONResponse(response_body, status_code=status.HTTP_200_OK)


def attach_healthz(app: FastAPI) -> None:
    @app.get("/healthz")
    async def healthz() -> Dict[str, Any]:
        return {"status": "ok", "name": NAME, "version": VERSION}
