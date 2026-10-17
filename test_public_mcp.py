
import asyncio
import os
from datetime import datetime
from pathlib import Path

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

BASE_DIR = Path(__file__).resolve().parent
TOKEN_FILE = BASE_DIR / ".mcp-token"
TRANSCRIPT_FILE = BASE_DIR / "handoff-transcript.txt"
from public_config import get_server_url

SERVER_URL = get_server_url()
HANDOFF_FILE = "handoff_demo.txt"

transcript = []


def record(message):
    print(message)
    transcript.append(message)


def result_text(result):
    return "\n".join(
        item.text for item in result.content if hasattr(item, "text")
    )


async def open_session(client, session_number):
    connection = streamable_http_client(
        SERVER_URL,
        http_client=client,
    )
    streams = await connection.__aenter__()
    session = ClientSession(streams[0], streams[1])
    await session.__aenter__()

    try:
        await session.initialize()
        record(f"Session {session_number}: connected and initialized.")

        tools = await session.list_tools()
        names = {tool.name for tool in tools.tools}

        required = {"write_file", "read_file", "replace_in_file"}
        if len(names) != 9 or not required.issubset(names):
            raise AssertionError(f"Unexpected tool list: {sorted(names)}")

        record(f"Session {session_number}: verified all 9 tools.")
        return connection, session
    except Exception:
        await session.__aexit__(None, None, None)
        await connection.__aexit__(None, None, None)
        raise


async def close_session(connection, session):
    await session.__aexit__(None, None, None)
    await connection.__aexit__(None, None, None)


async def main():
    if not TOKEN_FILE.is_file():
        raise FileNotFoundError("The .mcp-token file was not found.")

    token = TOKEN_FILE.read_text(encoding="utf-8").strip()
    if not token:
        raise ValueError("The .mcp-token file is empty.")

    headers = {
        "Authorization": f"Bearer {token}",
        "ngrok-skip-browser-warning": "true",
    }

    record("MCP multi-session handoff demonstration")
    record(f"Timestamp: {datetime.now().astimezone().isoformat()}")
    record("")

    async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
        # Session 1 creates a task and leaves it ready for handoff.
        connection1, session1 = await open_session(client, 1)
        try:
            created = await session1.call_tool(
                "write_file",
                arguments={
                    "path": HANDOFF_FILE,
                    "content": (
                        "Task: Verify MCP multi-session handoff\n"
                        "Status: READY\n"
                        "Next action: Mark the task completed.\n"
                    ),
                },
            )
            if created.is_error:
                raise RuntimeError(f"Session 1 write failed: {result_text(created)}")

            record("Session 1: created handoff task in the workspace.")
            record("Session 1: handed off task with status READY.")
        finally:
            await close_session(connection1, session1)

        record("Session 1: disconnected.")
        record("")

        # Session 2 independently reconnects, reads the handoff,
        # continues the task, and verifies the final state.
        connection2, session2 = await open_session(client, 2)
        try:
            read_result = await session2.call_tool(
                "read_file",
                arguments={"path": HANDOFF_FILE},
            )
            if read_result.is_error:
                raise RuntimeError(f"Session 2 read failed: {result_text(read_result)}")

            content = result_text(read_result)
            if "Status: READY" not in content:
                raise AssertionError(f"Unexpected handoff content: {content}")

            record("Session 2: read the task left by Session 1.")
            record("Session 2: confirmed status READY.")

            changed = await session2.call_tool(
                "replace_in_file",
                arguments={
                    "path": HANDOFF_FILE,
                    "old_text": "Status: READY",
                    "new_text": "Status: COMPLETED",
                },
            )
            if changed.is_error:
                raise RuntimeError(f"Session 2 update failed: {result_text(changed)}")

            record("Session 2: updated task status to COMPLETED.")

            verify = await session2.call_tool(
                "read_file",
                arguments={"path": HANDOFF_FILE},
            )
            if verify.is_error:
                raise RuntimeError(f"Verification read failed: {result_text(verify)}")

            final_content = result_text(verify)
            if "Status: COMPLETED" not in final_content:
                raise AssertionError(
                    f"Task completion could not be verified: {final_content}"
                )

            record("Session 2: verified the final task state.")
            record("PASS: Multi-session handoff completed successfully.")
        finally:
            await close_session(connection2, session2)

    TRANSCRIPT_FILE.write_text(
        "\n".join(transcript) + "\n",
        encoding="utf-8",
    )
    print(f"\nTranscript saved to: {TRANSCRIPT_FILE}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as error:
        transcript.append(f"FAIL: {type(error).__name__}: {error}")
        TRANSCRIPT_FILE.write_text(
            "\n".join(transcript) + "\n",
            encoding="utf-8",
        )
        raise
