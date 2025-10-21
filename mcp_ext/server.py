from __future__ import annotations

import datetime
import uuid
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field


class HealthCheckResponse(BaseModel):
    status: str
    name: str
    version: str
    now: str


class EchoResponse(BaseModel):
    data: Any


class UpsertItem(BaseModel):
    id: str
    text: str = Field(max_length=10000)
    metadata: dict[str, Any] | None = None


class UpsertResponse(BaseModel):
    upserted: int
    skipped: int
    cursor: Optional[str]
    audit_ref: str


def create_server(name: str, version: str) -> FastMCP:
    server = FastMCP(name=name, instructions=None)

    @server.tool(name="health.check", structured_output=True)
    async def health_check() -> HealthCheckResponse:
        now = datetime.datetime.utcnow().isoformat() + "Z"
        return HealthCheckResponse(status="ok", name=name, version=version, now=now)

    @server.tool(name="echo.json", structured_output=True)
    async def echo_json(data: Any) -> EchoResponse:
        return EchoResponse(data=data)

    @server.tool(name="index.upsert.v1", structured_output=True)
    async def index_upsert_v1(
        collection: str,
        items: list[UpsertItem],
        dedupe: str = "id",
        idempotency_key: Optional[str] = None,
    ) -> UpsertResponse:
        return UpsertResponse(
            upserted=len(items),
            skipped=0,
            cursor=None,
            audit_ref=f"trace-{uuid.uuid4()}",
        )

    @server.resource("greeting://{name}")
    async def greeting_resource(name: str):
        return {"contents": [{"uri": f"greeting://{name}", "text": f"Hello, {name}!"}]}

    return server
