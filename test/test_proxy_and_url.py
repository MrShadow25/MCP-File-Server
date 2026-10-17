import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["MCP_ACCESS_TOKEN"] = "unit-test-token"

from starlette.testclient import TestClient  # noqa: E402

import proxy_server  # noqa: E402
from public_config import normalize_url  # noqa: E402

client = TestClient(proxy_server.app, follow_redirects=False)


def test_mcp_without_token_is_401():
    assert client.post("/mcp", json={}).status_code == 401


def test_mcp_with_wrong_token_is_401():
    r = client.post("/mcp", json={}, headers={"Authorization": "Bearer nope"})
    assert r.status_code == 401


def test_unknown_path_gives_helpful_404():
    r = client.get("/")
    assert r.status_code == 404
    assert "/mcp" in r.json()["hint"]


def test_healthz_is_open_and_leaks_nothing():
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert "unit-test-token" not in r.text


@pytest.mark.parametrize(
    "given",
    [
        "https://x.ngrok-free.dev",
        "https://x.ngrok-free.dev/",
        "https://x.ngrok-free.dev/mcp",
        "https://x.ngrok-free.dev/mcp/",
        "  https://x.ngrok-free.dev/MCP  ",
    ],
)
def test_normalize_url_always_ends_with_mcp(given):
    assert normalize_url(given).lower().endswith("/mcp")
    assert normalize_url(given).lower().count("/mcp") == 1


def test_normalize_url_rejects_empty():
    with pytest.raises(RuntimeError):
        normalize_url("")
