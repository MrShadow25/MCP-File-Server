# MCP File Server: Security and Design Report

## 1. Purpose and architecture

The project implements a Model Context Protocol (MCP) server that exposes file operations limited to a project-local `workspace` directory. It supports stdio for local MCP clients and Streamable HTTP for remote clients. For remote access, `http_server.py` hosts the MCP transport on `127.0.0.1:8000`; `proxy_server.py` provides a bearer-token gate on `127.0.0.1:8001`. An HTTPS tunnel can expose the proxy without binding either Python service directly to a public interface.

## 2. Technology choices

**Python and MCPServer.** Python keeps the tool implementations readable and makes filesystem handling, automated testing, and integration with the MCP SDK straightforward. MCPServer-style decorators register tools and resources with relatively little protocol boilerplate.

**Streamable HTTP.** HTTP transport supports remote clients and session-based requests. Local stdio remains useful for desktop-client integration because it avoids opening a network port for local use.

**Authentication proxy.** The proxy separates public authentication from the MCP application. It checks a bearer token before forwarding requests to the loopback-only upstream. This reduces direct exposure of the MCP server, but the shared-token approach does not provide individual user identity or fine-grained permissions.

## 3. Tool design

The server exposes nine tools: `add`, `list_files`, `read_file`, `search_files`, `write_file`, `replace_in_file`, `delete_file`, `git_status`, and `git_diff`. It also exposes a greeting resource. File tools use a common path resolver to reject absolute paths and paths that resolve outside the workspace. The implementation includes additional symbolic-link checks and operation logging. Git tools are intended for read-only inspection.

## 4. Security controls and trade-offs

- **Workspace boundary:** Path resolution and containment checks reduce accidental or malicious access outside the workspace.
- **Symbolic links:** Link checks help prevent a link from escaping the workspace. The Windows symbolic-link test is skipped in the recorded test run, so behavior on that platform is not fully demonstrated.
- **TOCTOU race:** A path can potentially change between validation and file access. Resolve-then-open checks do not eliminate every time-of-check/time-of-use race.
- **Shared token:** A single bearer token is simple to configure but should be treated as a secret. Anyone who obtains it can act with the proxy's available permissions. Rotate it if exposed and never commit `.mcp-token`.
- **Deletion:** `delete_file` is destructive and requires explicit confirmation (`confirm=True`). Workspace restrictions lower the scope of risk but do not prevent accidental deletion of workspace files.
- **Logging:** Logs aid debugging and auditing, but should be protected from unauthorized access and should not contain credentials.
- **Tunnel:** HTTPS protects traffic in transit to the tunnel endpoint, but a temporary tunnel URL may change and the tunnel process can stop independently of the Python service manager.

These controls are risk reductions, not a guarantee of complete isolation. For stronger production security, consider stronger per-user credentials, request-size limits, atomic/descriptor-based file operations where supported, and tighter access control on the workspace and logs.

## 5. Verification evidence

The latest recorded automated test result is **46 passed, 1 skipped, 0 failed (2.71 seconds; 2026-10-17)**. The skipped test concerns symbolic-link behavior on Windows. `deployment-test.txt` records successful connections from two independent MCP sessions and the expected result from the addition tool. `handoff-transcript.txt` records a two-session `READY` to `COMPLETED` task exchange.

The process manager successfully started the MCP HTTP server on port 8000 and the authentication proxy on port 8001. Automatic restart of both child services was verified on 2026-10-17 and recorded in `workspace/PROCESS_MANAGER_RESTART_LOG.txt`.

The existing handoff transcript demonstrates a simple cross-session task exchange. If the rubric requires a genuine, more complex task performed interactively by Claude Desktop, run that task in the real client and preserve the actual tool-call transcript. Do not represent this report or the existing scripted transcript as evidence of that additional interaction.

## 6. Conclusion

The project has a working MCP tool set, workspace path controls, authenticated remote access, automated tests, and recorded multi-session/deployment checks. Remaining verification should focus on a real rubric-aligned Claude Desktop handoff, automatic process recovery, reproducible tunnel setup, and final repository review.


## Additional tool safeguards

`read_file` supports bounded line reads (`offset`, `limit`) and `search_files` supports `max_results` to reduce oversized tool outputs. `delete_file` requires an explicit `confirm=True` argument. These are guardrails, not a substitute for authorization by user role. The server currently uses a shared bearer token for remote access; per-role tool permissions are not implemented.

The Windows service manager supervises the MCP HTTP server and authentication proxy, but the HTTPS tunnel is started separately. Automatic child restart was verified in the target Windows environment. Tunnel recovery remains untested.
