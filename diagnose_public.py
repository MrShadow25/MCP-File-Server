"""Find out WHY the public MCP endpoint fails, layer by layer.

Usage:  python diagnose_public.py [https://your-name.ngrok-free.dev[/mcp]]
(or set MCP_SERVER_URL). Never prints the token.

Layers checked, in order:
  1. DNS/TLS/ngrok edge reachable
  2. Tunnel online (ngrok reports offline endpoints with an
     'ngrok-error-code' header such as ERR_NGROK_3200)
  3. Tunnel reaches the auth proxy (GET /healthz -> {"status":"ok"})
  4. Auth enforced (POST /mcp without a token -> 401)
  5. Path correct (the URL you use must end in /mcp)
  6. Token accepted and MCP initialize works
"""
import asyncio
import sys

import httpx

from public_config import get_token, normalize_url
import os

H = {"ngrok-skip-browser-warning": "true"}


def verdict(ok, text):
    print(("PASS  " if ok else "FAIL  ") + text)
    return ok


def main():
    raw = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("MCP_SERVER_URL", "")
    if not raw.strip():
        raise SystemExit("Give the URL as an argument or set MCP_SERVER_URL.")
    given_has_path = raw.strip().rstrip("/").lower().endswith("/mcp")
    url = normalize_url(raw)
    base = url[: -len("/mcp")]

    verdict(given_has_path,
            f"URL path: you gave '{raw.strip()}'. "
            + ("It ends in /mcp." if given_has_path else
               "It does NOT end in /mcp - a bare domain returns 'Not Found'. "
               "Scripts now add /mcp automatically; Claude Desktop/clients must use "
               f"{url}"))

    try:
        r = httpx.get(base + "/healthz", headers=H, timeout=15)
    except httpx.HTTPError as e:
        verdict(False, f"Cannot reach {base}: {e!r}. Check internet/DNS/TLS.")
        return 1

    code = r.headers.get("ngrok-error-code")
    if code:
        verdict(False, f"ngrok edge answered with {code}. "
                f"3200 = tunnel OFFLINE: start ngrok (or fix its target port 8001).")
        return 1
    if r.status_code == 200 and "ok" in r.text:
        verdict(True, "Tunnel is online and reaches the authentication proxy (/healthz).")
    else:
        verdict(False, f"/healthz returned {r.status_code}. The tunnel is online but "
                f"not pointing at the auth proxy (expected port 8001). Body: {r.text[:100]!r}")
        return 1

    r = httpx.post(url, json={}, headers=H, timeout=15)
    verdict(r.status_code == 401, f"No-token request to /mcp -> {r.status_code} (expected 401).")

    try:
        token = get_token()
    except FileNotFoundError as e:
        verdict(False, str(e)); return 1

    async def init():
        from mcp import ClientSession
        from mcp.client.streamable_http import streamable_http_client
        async with httpx.AsyncClient(headers={**H, "Authorization": f"Bearer {token}"}) as c:
            async with streamable_http_client(url, http_client=c) as s:
                async with ClientSession(s[0], s[1]) as sess:
                    await sess.initialize()
                    return sorted(t.name for t in (await sess.list_tools()).tools)

    try:
        names = asyncio.run(init())
        verdict(True, f"MCP initialize OK with token; {len(names)} tools: {', '.join(names)}")
        return 0
    except Exception as e:  # report, don't hide
        verdict(False, f"MCP initialize failed: {e!r}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
