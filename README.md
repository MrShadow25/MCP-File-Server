# MCP File Server

A Python-based Model Context Protocol (MCP) file server that provides controlled file operations inside a designated workspace. It supports local MCP clients through standard input/output (stdio) and an authenticated remote endpoint through an HTTP proxy.

## Features

The server exposes nine tools:

| Tool | Description |
|---|---|
| `add` | Performs the project's arithmetic addition operation. |
| `list_files` | Lists files and directories inside the workspace. |
| `read_file` | Reads a permitted workspace file. |
| `search_files` | Searches workspace files for matching content. |
| `write_file` | Creates or writes a permitted workspace file. |
| `replace_in_file` | Replaces specified text within a permitted file. |
| `delete_file` | Deletes a permitted workspace file. |
| `git_status` | Retrieves Git working-tree status. |
| `git_diff` | Retrieves Git differences. |

File operations are restricted to the configured workspace. The server is designed to prevent file operations from escaping that workspace through path traversal.

## Requirements

- Python 3.10 or later, compatible with the dependencies in the project.
- Git for Git inspection tools.
- A virtual environment for isolated Python dependencies.
- Optional: ngrok or another supported tunnel for exposing the authenticated HTTP endpoint.
- Claude Desktop or another compatible MCP client.

Install the project dependencies using the repository's dependency files and instructions.

## Local setup

Run these commands in PowerShell from the project directory:

```powershell
cd "C:\Users\Admin\PycharmProjects\MCP Server"

.\.venv\Scripts\python.exe .\main.py
```

The local server uses stdio and is intended to be launched by an MCP-compatible client. When launching it through Claude Desktop, configure the Python executable and the absolute path to `main.py`.

Example Claude Desktop configuration:

```json
{
  "mcpServers": {
    "demo": {
      "command": "C:\\Users\\Admin\\PycharmProjects\\MCP Server\\.venv\\Scripts\\python.exe",
      "args": [
        "C:\\Users\\Admin\\PycharmProjects\\MCP Server\\main.py"
      ]
    }
  }
}
```

Use the actual project path on your computer if it differs from this example. Restart or refresh the MCP server from Claude Desktop's Developer settings after changing the configuration.

## Testing

The repository records results from multiple test runs. These are historical results and should not be interpreted as proof that every test was rerun during the latest handoff session.

- An earlier Windows run recorded 46 passed and 1 skipped.
- A later Windows run recorded 56 passed and 1 skipped, with no failures. The repository's `test-results.txt` contains the recorded result.
- A Linux run during repair recorded 55 passed and 2 failed. The failures were associated with Windows-drive-path assumptions and should be reviewed before claiming cross-platform compatibility.

The public MCP test script previously reported a successful connection and discovered nine tools:

```text
MCP connection successful.
Tools found: 9
- add
- list_files
- read_file
- search_files
- write_file
- replace_in_file
- delete_file
- git_status
- git_diff
```

This is a recorded result from an earlier test. It does not establish that the public endpoint was retested during the latest Claude Desktop handoff session.

Run the appropriate project test command from the repository root. For example, if the project uses pytest:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Record the actual command, environment, date, and outcome when running tests again.

## Remote deployment

The project also includes an HTTP deployment path through an authentication proxy. The proxy exposes the MCP endpoint and a health-check endpoint.

The configured endpoint paths are:

- `/mcp` — authenticated MCP requests.
- `/healthz` — service health check.

The public deployment has previously used an ngrok URL. Public URLs can change when a temporary tunnel restarts, so use the current URL printed by the running tunnel rather than assuming an old URL remains valid.

A successful health check indicates that the health endpoint responded. It does not, by itself, prove that an authenticated MCP session can connect and use all nine tools.

### Authentication

The remote proxy uses a Bearer token. Keep the token private and supply it through the intended configuration or environment mechanism.

Never commit authentication tokens, `.mcp-token` files, private credentials, or other secrets to GitHub. If a token has been exposed, revoke or rotate it.

A remote MCP client must support the authentication mechanism expected by the proxy. If the client cannot supply the required authorization header, the remote connection may fail even while the server and tunnel are running. Local stdio configuration avoids this particular remote-header compatibility issue.

### Deployment and diagnostic scripts

The repository contains scripts for checking the public deployment, including:

- `diagnose_public.py`
- `test_public_mcp.py`
- `test_public_tools.py`

Run these scripts only when the relevant services and tunnel are running and the required configuration is available. Record the actual output instead of relying on results from previous runs.

## Security design

The server limits file operations to its designated workspace. This boundary is important because MCP tools can read, create, modify, search, and delete files.

Security considerations include:

- Resolve and validate file paths against the configured workspace.
- Reject paths that attempt to escape the workspace.
- Keep authentication credentials out of source control.
- Restrict access to the remote endpoint.
- Review destructive operations such as `delete_file` before executing them.
- Treat public tunnel URLs as temporary unless a stable deployment is configured.
- Verify error handling and workspace restrictions through tests.
- Avoid treating a successful health check as proof of complete service security.

These controls reduce risk but do not replace a security review of the implementation, dependencies, deployment configuration, and runtime permissions.

See `security_design_report.md` for the recorded design rationale, trade-offs, and limitations.

## Process management and restart testing

The repository contains process-manager restart records, including process identifiers and recorded exit information.

The available restart log provides evidence of process restart activity. It does not independently establish that tunnel recovery was tested successfully. Tunnel restart and end-to-end recovery remain unverified unless supported by a separate recorded test.

A complete recovery test should verify that the MCP server restarts, the proxy restarts, the tunnel reconnects, the public endpoint becomes reachable, and an authenticated MCP client can use the tools afterward.

## Session handoff

The project includes files intended to let a second agent continue work from a fresh context:

- `workspace/PROJECT_STATE` — current project state and known limitations.
- `workspace/PLAN_LOG` — work history and planned actions.
- `workspace/CHECKPOINTS` — checkpoints and recorded progress.
- `workspace/DECISIONS` — design decisions and their rationale.
- `workspace/handoff_demo.txt` — handoff demonstration status.
- `workspace/PROCESS_MANAGER_RESTART_LOG.txt` — recorded process-manager restart information.
- `workspace/PROCESS_MANAGER_RESTART_TRANSCRIPT.txt` — related restart transcript, if present.

A second-session agent should read the handoff state files before taking action, confirm the current repository state, and append new progress without inventing completed work.

The latest recorded fresh-context Session 2 report states that the agent updated the handoff records and read back its appended entries. It also acknowledges that it did not follow the requested initial read order exactly: `PROJECT_STATE` was read separately before the other state files. The report records 15 tool calls, including file reads, file listing, a Git diff, and file replacements.

The saved file `workspace/evidence/session2-fresh-transcript.txt` is a **summary of the Session 2 report, not a complete raw interactive transcript**. The file `workspace/evidence/session-tool-call-log.txt` records server operation names and completion or failure events; it does not preserve complete tool inputs and outputs.

The existing scripted handoff transcript is separate evidence and should not be described as a genuine interactive Claude Desktop transcript. If the assignment requires a complete interactive two-session transcript, capture and retain that transcript separately.

## Evidence

The following files contain recorded evidence. Their existence does not imply that every test described in them was rerun during the latest session.

- `test-results.txt` — recorded local test results.
- `deployment-test.txt` — recorded public MCP session checks.
- `handoff-transcript.txt` — evidence of the scripted two-session exchange; not, by itself, a genuine interactive Claude Desktop transcript.
- `workspace/evidence/handoff-transcript-FAILED-2026-10-17T1149.txt` — retained evidence of a failed public test reporting `MCPError: Not Found`.
- `workspace/evidence/session2-fresh-transcript.txt` — summary of the fresh-context Session 2 report, not a complete raw transcript.
- `workspace/evidence/session-tool-call-log.txt` — server operation log showing tool names and completion or failure events, not complete tool inputs and outputs.
- `security_design_report.md` — security design rationale, trade-offs, and limitations.
- `workspace/PROCESS_MANAGER_RESTART_LOG.txt` — recorded process-manager restart information.

Claude Desktop was observed reporting the local MCP server as running. A subsequent `list_files` tool request successfully returned the workspace contents. This supports the claim that the local server was usable for that recorded interaction; it does not establish that every tool was individually tested through Claude Desktop.

The recorded Session 2 report describes updates to the handoff state files and acknowledges a deviation from the requested initial read order. The saved summary is not a complete raw Claude Desktop transcript.

Public endpoint checks, local test results, process-manager logs, and handoff evidence should be evaluated separately. Do not infer that the public endpoint, tunnel recovery, or full test suite was retested during Session 2 without additional recorded results.

## Repository status

Before submitting, verify that the files required by the assignment are present and that the Git working tree contains only intended changes.

```powershell
git status --short
git diff --check
git diff --stat
```

Review new and modified files before staging them. Do not commit secrets, unnecessary temporary scripts, or misleading evidence. Preserve failed test records when they are relevant to explaining known limitations.

## Limitations and future work

- Re-run the full test suite and record the current results.
- Review platform-specific path handling before claiming Linux compatibility.
- Perform and record an end-to-end remote MCP test after any deployment or tunnel restart.
- Capture a complete interactive two-session handoff transcript if required by the assignment.
- Verify that the authentication method is supported by the intended remote MCP client.
- Review workspace restrictions and destructive operations with additional security tests.

## License

Add the license required by the project or course, if applicable.
