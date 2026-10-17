
import asyncio
import os
from pathlib import Path

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

BASE_DIR = Path(__file__).resolve().parent
TOKEN_FILE = BASE_DIR / ".mcp-token"
SERVER_URL = os.environ.get("MCP_SERVER_URL")
if not SERVER_URL:
    raise RuntimeError("Set the MCP_SERVER_URL environment variable to your public MCP endpoint.")


async def main():
    if not TOKEN_FILE.is_file():
        raise FileNotFoundError(".mcp-token file not found.")

    token = TOKEN_FILE.read_text(encoding="utf-8").strip()

    headers = {
        "Authorization": f"Bearer {token}",
        "ngrok-skip-browser-warning": "true",
    }

    async with httpx.AsyncClient(
        headers=headers, timeout=30.0
    ) as client:
        async with streamable_http_client(
            SERVER_URL, http_client=client
        ) as (read_stream, write_stream):
            async with ClientSession(
                read_stream, write_stream
            ) as session:
                await session.initialize()
                result = await session.list_tools()

                for tool in result.tools:
                    print(f"\nTool: {tool.name}")
                    print(tool.description or "No description")
                    print("Input schema:")
                    print(tool.input_schema)


if __name__ == "__main__":
    asyncio.run(main())
