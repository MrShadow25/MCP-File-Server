
import asyncio
import os
from pathlib import Path

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

BASE_DIR = Path(__file__).resolve().parent
TOKEN_FILE = BASE_DIR / ".mcp-token"
from public_config import get_server_url

SERVER_URL = get_server_url()


async def main():
    if not TOKEN_FILE.is_file():
        raise FileNotFoundError("The .mcp-token file was not found.")

    token = TOKEN_FILE.read_text(encoding="utf-8").strip()

    headers = {
        "Authorization": f"Bearer {token}",
        "ngrok-skip-browser-warning": "true",
    }

    async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
        async with streamable_http_client(
            SERVER_URL,
            http_client=client,
        ) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.list_tools()

                tool_names = {tool.name for tool in result.tools}

                print("MCP connection successful.")
                print(f"Tools found: {len(result.tools)}")

                for tool in result.tools:
                    print(f"\nTool: {tool.name}")
                    print(f"Input schema: {tool.inputSchema}")

                if "add" not in tool_names:
                    raise RuntimeError("The add tool was not found.")

                print("\n--- Testing add ---")

                response = await session.call_tool(
                    "add",
                    arguments={"a": 2, "b": 3},
                )

                if (getattr(response, "is_error", None) or getattr(response, "isError", False)):
                    raise RuntimeError(f"Tool call failed: {response.content}")

                output = [
                    item.text
                    for item in response.content
                    if hasattr(item, "text")
                ]

                print(f"Result: {' '.join(output)}")

                if not any(value.strip() == "5" for value in output):
                    raise AssertionError(
                        f"Expected add(2, 3) to return 5, got: {output}"
                    )

                print("PASS: add(2, 3) returned 5.")
                print("\nPublic MCP client test completed successfully.")


if __name__ == "__main__":
    asyncio.run(main())
