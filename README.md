# MCP File Server

## Overview

A Python MCP server with nine tools, workspace-restricted file operations, Git inspection, local stdio support, and authenticated remote access.

## Tools

1. `add` — adds two integers.
2. `list_files` — lists workspace entries.
3. `read_file` — reads a bounded UTF-8 text-file chunk using `offset` and `limit`.
4. `search_files` — searches workspace files with a `max_results` cap.
5. `write_file` — creates or overwrites a file.
6. `replace_in_file` — replaces matching text.
7. `delete_file` — deletes a workspace file only when called with `confirm=True`.
8. `git_status` — reports Git status.
9. `git_diff` — reports unstaged changes.

A greeting resource and operation logging are also included.

## Requirements and tests

Use Python matching `pyproject.toml` and the project dependencies. In PowerShell from the project directory:

```powershell
uv sync
.\.venv\Scripts\python.exe -m pytest test/ -q
```

Recorded result: **39 passed, 1 skipped**. The skipped test concerns symbolic-link behavior on Windows.

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

4. Configure the remote MCP client to use that HTTPS endpoint and send the value from `.mcp-token` as a bearer token. Do not publish the token or place it in this README.

## Security notes

File operations are restricted to `workspace`; absolute paths and paths resolving outside it are rejected. Additional symbolic-link checks are present. Git inspection tools are read-only. The remote proxy requires bearer-token authentication.

Limitations include a possible time-of-check/time-of-use race, a shared bearer token, a destructive delete tool without a separate confirmation gate, and platform-specific symlink behavior. These protections do not guarantee complete filesystem isolation.

## Evidence

- `test-results.txt` — recorded local test results.
- `deployment-test.txt` — two independent public MCP session checks.
- `handoff-transcript.txt` — recorded two-session task exchange.
- `security_design_report.md` — design rationale, security trade-offs, and limitations.

Both services have been observed starting under `service_manager.py`. Automatic restart after a child process crash remains unverified. The existing handoff transcript records a simple `READY` to `COMPLETED` exchange; if the rubric requires a genuine multi-step task performed interactively in Claude Desktop, capture that actual interaction separately.


## Handoff state files

The agent-readable handoff files are available inside `workspace/` using the required names: `PROJECT_STATE`, `PLAN_LOG`, `CHECKPOINTS`, and `DECISIONS`. A second-session agent should read these files before acting and append its progress to the appropriate files. The included scripted transcript is test evidence, not a substitute for a genuine Claude Desktop task transcript required by the rubric.

## Tool efficiency and destructive actions

`read_file(path, offset=0, limit=200)` returns a line-bounded chunk (limit maximum 1000). `search_files(query, path=".", max_results=50)` caps matches (maximum 500). `delete_file(path, confirm=False)` refuses deletion unless `confirm=True` is explicitly provided.
