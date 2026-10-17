# Design Decisions

## 1. Python MCP Server
Python is used to implement the MCP server and its tools.

## 2. Workspace Restriction
File operations use a workspace directory located relative to the server project. Path validation prevents access outside the designated workspace.

## 3. Local and Remote Transport
The server supports stdio for local MCP client communication and HTTP transport for remote access through an HTTPS tunnel.

## 4. Authentication
The public endpoint uses a proxy with bearer-token authentication. A request without a valid token is expected to be rejected. Missing-token rejection was verified with HTTP 401.

## 5. File Operations
The server supports listing, reading, writing, searching, replacing text, and deleting files. File operations include path validation and additional symbolic-link checks.

## 6. Git Tools
Git status and Git diff are read-only tools intended to inspect the project repository.

## 7. Automated Testing
Pytest is used to verify normal operations, invalid paths, error handling, and Git behavior. The latest recorded suite result is 56 passed and 1 skipped.

## 8. Deployment and Process Management
The public HTTPS endpoint was tested successfully, including authentication, MCP initialization, and the multi-session handoff demonstration. Automatic restart behavior for the MCP server and authentication proxy was verified and recorded in workspace/PROCESS_MANAGER_RESTART_LOG.txt. Automatic tunnel restart and recovery remain untested.
## 9. Security Limitations
Passing automated tests does not prove complete filesystem isolation. Filesystem race conditions and platform-specific symbolic-link behavior remain limitations requiring further review.

