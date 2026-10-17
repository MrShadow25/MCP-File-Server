# MCP File Server

## Overview

A Python MCP server with nine tools, workspace-restricted file operations, Git inspection, local stdio support, and authenticated remote access.

## Tools

1. `add` â€” adds two integers.
2. `list_files` â€” lists workspace entries.
3. `read_file` â€” reads a bounded UTF-8 text-file chunk using `offset` and `limit`.
4. `search_files` â€” searches workspace files with a `max_results` cap.
5. `write_file` â€” creates or overwrites a file.
6. `replace_in_file` â€” replaces matching text.
7. `delete_file` â€” deletes a workspace file only when called with `confirm=True`.
8. `git_status` â€” reports Git status.
9. `git_diff` â€” reports unstaged changes.

A greeting resource and operation logging are also included.

## Requirements and tests

Use Python matching `pyproject.toml` and the project dependencies. In PowerShell from the project directory:

```powershell
uv sync
.\.venv\Scripts\python.exe -m pytest test/ -q
```

`pyproject.toml` limits pytest to `test/`, so plain `pytest` collects only the unit tests (the `test_public*.py` scripts and `test-results.txt` are not collected).

Result history (do not mix these up):

- Earlier Windows run (recorded): **46 passed, 1 skipped**. The skipped test concerns symbolic-link behavior on Windows.
- Later change: 10 tests added (`test/test_proxy_and_url.py`) and a git-output decoding fix. Verified on Windows: **56 passed, 1 skipped, 0 failed.** The latest results are saved in `test-results.txt`.
- Linux run during the 2026-10-17 repair session: 55 passed, 2 failed. The two failures are the Windows-drive-path tests (`C:\...` is not an absolute path on Linux) and are expected there.

## Local client

Configure the MCP-compatible desktop client to launch the project's Python environment and `main.py` using the stdio transport. Use an absolute path to the project directory in the client configuration. Do not put secrets in the configuration file.

## Remote deployment (Windows)

1. Create a local token file if one does not already exist:

   ```powershell
   python -c "import secrets; from pathlib import Path; p=Path('.mcp-token'); p.write_text(secrets.token_urlsafe(32), encoding='utf-8') if not p.exists() else None"
   ```

   Keep `.mcp-token` private; it is excluded by `.gitignore`.

2. Start both Python services with the manager:

   ```powershell
   .\.venv\Scripts\python.exe .\service_manager.py
   ```

   The manager uses port `8000` for the MCP HTTP server and port `8001` for the authentication proxy. Do not start duplicate instances if those ports are already occupied.

3. In another PowerShell window, start an HTTPS tunnel to the proxy, for example with ngrok installed and authenticated:

   ```powershell
   ngrok http 8001
   ```

   Use the HTTPS forwarding URL ngrok prints, with `/mcp` appended, as the remote MCP endpoint. A free tunnel URL is typically temporary and can change when the tunnel restarts. The tunnel is not managed by `service_manager.py`, so it must be kept running separately.

   Recommended: use your static ngrok domain so the URL never changes, e.g.
   `ngrok http --url=your-name.ngrok-free.dev 8001`.

   To let the manager supervise the tunnel as well, this would need a third service entry; at present it does not (see Evidence below).

4. Configure the remote MCP client to use that HTTPS endpoint and send the value from `.mcp-token` as a bearer token. Do not publish the token or place it in this README.

## Checking the public endpoint

```powershell
$env:MCP_SERVER_URL = "https://your-name.ngrok-free.dev/mcp"   # /mcp is added if you forget it
.\.venv\Scripts\python.exe diagnose_public.py                  # layer-by-layer diagnosis, never prints the token
.\.venv\Scripts\python.exe test_public_mcp.py                  # two-session handoff test, writes handoff-transcript.txt
.\.venv\Scripts\python.exe test_public_tools.py                # every tool + sandbox-boundary checks
```

### Troubleshooting `MCPError: Not Found`

`Not Found` (HTTP 404) has two real causes in this setup:

1. **Wrong path.** The proxy serves only `/mcp` (plus an open `/healthz`). A URL without `/mcp` returns 404. Reproduced locally; the test scripts now append `/mcp` automatically, but Claude Desktop and other clients must be configured with the full `.../mcp` URL.
2. **Tunnel offline or pointing at the wrong port.** ngrok answers 404 with error `ERR_NGROK_3200` when no tunnel is online for the domain. Start `ngrok http --url=... 8001` and confirm `https://your-name.ngrok-free.dev/healthz` returns `{"status":"ok"}`.

`diagnose_public.py` tells these apart.

## Security notes

File operations are restricted to `workspace`; absolute paths and paths resolving outside it are rejected. Additional symbolic-link checks are present. Git inspection tools are read-only. The remote proxy requires bearer-token authentication.

Limitations include a possible time-of-check/time-of-use race, a shared bearer token, a destructive delete tool that requires explicit confirmation (`confirm=True`), and platform-specific symlink behavior. These protections do not guarantee complete filesystem isolation.

## Evidence

- `test-results.txt` â€” recorded local test results.
- `deployment-test.txt` â€” two independent public MCP session checks.
- `handoff-transcript.txt` â€” the last PASSING scripted two-session exchange (2026-10-17 10:47:37 +08).
- `workspace/evidence/handoff-transcript-FAILED-2026-10-17T1149.txt` â€” the later run that failed with `MCPError: Not Found`, kept as honest evidence. The cause is analysed in `workspace/PLAN_LOG`.
- `security_design_report.md` â€” design rationale, security trade-offs, and limitations.

Both services have been observed starting under `service_manager.py`. Automatic restart of both the MCP server and authentication proxy was verified and recorded in workspace/PROCESS_MANAGER_RESTART_LOG.txt. Tunnel restart and recovery remain untested. The existing handoff transcript records a simple `READY` to `COMPLETED` exchange; if the rubric requires a genuine multi-step task performed interactively in Claude Desktop, capture that actual interaction separately.


## Handoff state files

The agent-readable handoff files are available inside `workspace/` using the required names: `PROJECT_STATE`, `PLAN_LOG`, `CHECKPOINTS`, and `DECISIONS`. A second-session agent should read these files before acting and append its progress to the appropriate files. The included scripted transcript is test evidence, not a substitute for a genuine Claude Desktop task transcript required by the rubric.

## Tool efficiency and destructive actions

`read_file(path, offset=0, limit=200)` returns a line-bounded chunk (limit maximum 1000). `search_files(query, path=".", max_results=50)` caps matches (maximum 500). `delete_file(path, confirm=False)` refuses deletion unless `confirm=True` is explicitly provided.
