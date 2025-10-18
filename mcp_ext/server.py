from __future__ import annotations
import json, uuid, datetime
from pydantic import BaseModel, Field
from typing import Any, Optional
from mcp.server import Server
from mcp.types import TextContent
from .policy import get_policy

class UpsertItem(BaseModel):
    id: str
    text: str = Field(max_length=10000)
    metadata: dict[str, Any] | None = None

class UpsertRequest(BaseModel):
    collection: str
    items: list[UpsertItem]
    dedupe: str = "id"
    idempotency_key: Optional[str] = None

class UpsertResponse(BaseModel):
    upserted: int
    skipped: int
    cursor: Optional[str]
    audit_ref: str

def create_server(name: str, version: str) -> Server:
    server = Server(name=name, version=version)

    @server.tool(name="health.check")
    async def health_check() -> dict:
        now = datetime.datetime.utcnow().isoformat()+"Z"
        result = {"status": "ok", "name": name, "version": version, "now": now}
        return {
            "content": [TextContent(type="text", text=json.dumps(result))],
            "structuredContent": result,
            "meta": {"policy": get_policy("health.check")}
        }

    @server.tool(name="echo.json")
    async def echo_json(data: Any) -> dict:
        result = {"data": data}
        return {
            "content": [TextContent(type="text", text=json.dumps(result))],
            "structuredContent": result,
            "meta": {"policy": get_policy("echo.json")}
        }

    @server.tool(name="index.upsert.v1")
    async def index_upsert_v1(collection: str, items: list[dict], dedupe: str = "id", idempotency_key: Optional[str] = None) -> dict:
        req = UpsertRequest(collection=collection, items=[UpsertItem(**i) for i in items], dedupe=dedupe, idempotency_key=idempotency_key)
        out = UpsertResponse(upserted=len(req.items), skipped=0, cursor=None, audit_ref=f"trace-{uuid.uuid4()}")
        return {
            "content": [TextContent(type="text", text=out.model_dump_json())],
            "structuredContent": out.model_dump(),
            "meta": {"policy": get_policy("index.upsert.v1")}
        }

    # Resource example
    @server.resource("greeting://{name}")
    async def greeting_resource(name: str):
        return {"contents": [{"uri": f"greeting://{name}", "text": f"Hello, {name}!"}]}

    # Prompt metadata (toy)
    server.prompt("summarize.v1", description="Summarize text with citations (toy).", arguments=[{
        "name": "text", "description": "Text to summarize", "required": True
    }])

    return server
