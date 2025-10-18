import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from mcp_facade import mcp_asgi_app, mcp_admin
from mcp_ext.http_root import attach_healthz, mount_mcp_root
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

app = FastAPI(title="fastapi-mcp")

# True MCP endpoint:
app.mount("/mcp", mcp_asgi_app)

# Optional manual reload endpoint for downstream catalog
if mcp_admin:
    app.include_router(mcp_admin)

# --- CORS (relax in dev; restrict in prod) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
)

COMMIT_SHA = os.getenv("COMMIT_SHA", "unknown")

mount_mcp_root(app)
attach_healthz(app)

@app.get("/version")
async def version():
    return {"commit": COMMIT_SHA}
