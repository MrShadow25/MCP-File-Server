"""Shared settings for the public-endpoint test and diagnostic scripts.

MCP_SERVER_URL may be the bare tunnel domain or the full MCP endpoint;
the /mcp path is added when missing. (Without it the proxy answers
"404 Not Found", which the MCP client reports as "MCPError: Not Found".)
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
TOKEN_FILE = BASE_DIR / ".mcp-token"


def normalize_url(url: str) -> str:
    url = (url or "").strip().rstrip("/")
    if not url:
        raise RuntimeError(
            "Set MCP_SERVER_URL, e.g. https://your-name.ngrok-free.dev/mcp"
        )
    if not url.lower().endswith("/mcp"):
        url += "/mcp"
    return url


def get_server_url() -> str:
    return normalize_url(os.environ.get("MCP_SERVER_URL", ""))


def get_token() -> str:
    token = os.environ.get("MCP_ACCESS_TOKEN", "").strip()
    if not token and TOKEN_FILE.is_file():
        token = TOKEN_FILE.read_text(encoding="utf-8").strip()
    if not token:
        raise FileNotFoundError(
            "No token: set MCP_ACCESS_TOKEN or create .mcp-token"
        )
    return token
