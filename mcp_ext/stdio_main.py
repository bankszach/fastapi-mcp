from __future__ import annotations
import os, asyncio
from dotenv import load_dotenv
from mcp.server.stdio import stdio_server
from .server import create_server

load_dotenv()
NAME = os.getenv("SERVER_NAME", "fastapi-mcp")
VERSION = os.getenv("SERVER_VERSION", "0.1.0")

async def main():
    server = create_server(NAME, VERSION)
    await stdio_server(server)

if __name__ == "__main__":
    asyncio.run(main())
