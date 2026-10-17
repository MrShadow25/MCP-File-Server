
import os
import secrets

import httpx
import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from starlette.routing import Route

ACCESS_TOKEN = os.environ.get("MCP_ACCESS_TOKEN")
UPSTREAM = "http://127.0.0.1:8000"

if not ACCESS_TOKEN:
    raise RuntimeError("Set the MCP_ACCESS_TOKEN environment variable first.")

client = httpx.AsyncClient(timeout=None)

async def proxy(request: Request):
    # Require a bearer token for every request.
    auth = request.headers.get("authorization", "")
    supplied = auth.removeprefix("Bearer ").strip()

    if not secrets.compare_digest(supplied, ACCESS_TOKEN):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    # Forward the MCP request and session headers to the local server.
    headers = {}
    for name in ("accept", "content-type", "mcp-session-id", "last-event-id"):
        value = request.headers.get(name)
        if value:
            headers[name] = value

    body = await request.body()

    async with client.stream(
        request.method,
        f"{UPSTREAM}{request.url.path}",
        params=request.query_params,
        headers=headers,
        content=body,
    ) as upstream:
        response_headers = {}
        for name in ("content-type", "mcp-session-id", "mcp-protocol-version"):
            value = upstream.headers.get(name)
            if value:
                response_headers[name] = value

        content = await upstream.aread()
        return Response(
            content=content,
            status_code=upstream.status_code,
            headers=response_headers,
        )

async def health(request: Request):
    # No secrets, no upstream access: only proves tunnel -> proxy works.
    return JSONResponse({"status": "ok", "mcp_path": "/mcp"})


async def not_found(request: Request, exc):
    return JSONResponse(
        {"error": "Not Found", "hint": "The MCP endpoint is /mcp"},
        status_code=404,
    )


app = Starlette(
    routes=[
        Route("/healthz", health, methods=["GET"]),
        Route("/mcp", proxy, methods=["GET", "POST", "DELETE"]),
    ],
    exception_handlers={404: not_found},
)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001)
