
import asyncio
import os
import uuid
from pathlib import Path

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

BASE_DIR = Path(__file__).resolve().parent
TOKEN_FILE = BASE_DIR / ".mcp-token"
from public_config import get_server_url

SERVER_URL = get_server_url()


def show_result(name, result):
    print(f"\n--- {name} ---")
    output = "\n".join(
        item.text for item in result.content if hasattr(item, "text")
    )
    print(output or "(No text output)")
    return output, not (getattr(result, "is_error", None) or getattr(result, "isError", False))


async def main():
    if not TOKEN_FILE.is_file():
        raise FileNotFoundError(".mcp-token file not found.")

    token = TOKEN_FILE.read_text(encoding="utf-8").strip()
    headers = {
        "Authorization": f"Bearer {token}",
        "ngrok-skip-browser-warning": "true",
    }

    test_name = f"mcp_public_test_{uuid.uuid4().hex}.txt"
    original = f"MCP_TEST_ORIGINAL_{uuid.uuid4().hex}"
    replacement = f"MCP_TEST_REPLACED_{uuid.uuid4().hex}"
    file_created = False

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
                print("Public MCP connection successful.")

                try:
                    result = await session.call_tool(
                        "add", arguments={"a": 2, "b": 3}
                    )
                    show_result("add", result)

                    result = await session.call_tool(
                        "list_files", arguments={"path": "."}
                    )
                    show_result("list_files", result)

                    result = await session.call_tool(
                        "write_file",
                        arguments={
                            "path": test_name,
                            "content": original,
                        },
                    )
                    output, ok = show_result("write_file", result)
                    file_created = (
                        ok
                        and output.startswith("File written successfully:")
                    )

                    if file_created:
                        result = await session.call_tool(
                            "read_file",
                            arguments={"path": test_name},
                        )
                        output, ok = show_result("read_file", result)
                        print(
                            "Read verification:",
                            "PASS" if ok and output == original else "FAIL",
                        )

                        result = await session.call_tool(
                            "search_files",
                            arguments={"query": original, "path": "."},
                        )
                        output, ok = show_result("search_files", result)
                        print(
                            "Search verification:",
                            "PASS" if ok and test_name in output else "FAIL",
                        )

                        result = await session.call_tool(
                            "replace_in_file",
                            arguments={
                                "path": test_name,
                                "old_text": original,
                                "new_text": replacement,
                            },
                        )
                        show_result("replace_in_file", result)

                        result = await session.call_tool(
                            "read_file",
                            arguments={"path": test_name},
                        )
                        output, ok = show_result(
                            "read_file after replacement", result
                        )
                        print(
                            "Replacement verification:",
                            "PASS"
                            if ok and output == replacement
                            else "FAIL",
                        )
                    else:
                        print("File tests skipped because creation failed.")

                    result = await session.call_tool(
                        "git_status", arguments={}
                    )
                    show_result("git_status", result)

                    result = await session.call_tool(
                        "git_diff", arguments={}
                    )
                    show_result("git_diff", result)

                finally:
                    if file_created:
                        result = await session.call_tool(
                            "delete_file",
                            arguments={"path": test_name},
                        )
                        output, ok = show_result("delete_file", result)

                        if ok and output.startswith(
                            "File deleted successfully:"
                        ):
                            result = await session.call_tool(
                                "read_file",
                                arguments={"path": test_name},
                            )
                            output, _ = show_result(
                                "read after deletion", result
                            )
                            print(
                                "Deletion verification:",
                                "PASS"
                                if output.startswith("Error:")
                                else "FAIL",
                            )

                print("\n=== SANDBOX BOUNDARY TESTS ===")

                sandbox_tests = [
                    ("Parent-directory traversal", "../main.py"),
                    ("Absolute path", str(BASE_DIR / "main.py")),
                ]

                for name, path in sandbox_tests:
                    print(f"\n--- {name} ---")

                    try:
                        result = await session.call_tool(
                            "read_file",
                            arguments={"path": path},
                        )
                        output, ok = show_result(name, result)

                        rejected = (
                            not ok
                            or output.startswith("Error:")
                        )

                        print(
                            "PASS: Access rejected."
                            if rejected
                            else "FAIL: Access was not rejected."
                        )

                    except Exception as error:
                        print(
                            f"Request failed: {type(error).__name__}: {error}"
                        )

                print("\nPublic MCP tests completed.")


if __name__ == "__main__":
    asyncio.run(main())
