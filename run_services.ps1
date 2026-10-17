
$ErrorActionPreference = "Stop"

$Project = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Project ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    throw "Virtual environment Python not found: $Python"
}

# Load the token only if it is not already in the environment.
if (-not $env:MCP_ACCESS_TOKEN) {
    $TokenFile = Join-Path $Project ".mcp-token"

    if (-not (Test-Path $TokenFile)) {
        throw "MCP_ACCESS_TOKEN is missing and .mcp-token was not found."
    }

    $env:MCP_ACCESS_TOKEN = (Get-Content $TokenFile -Raw).Trim()
}

# Start the MCP server only if port 8000 is not already listening.
$McpPort = Get-NetTCPConnection -LocalPort 8000 -State Listen `
    -ErrorAction SilentlyContinue

if ($McpPort) {
    Write-Host "MCP server already listening on port 8000; reusing it."
}
else {
    Write-Host "Starting MCP server..."
    Start-Process -FilePath $Python `
        -ArgumentList @("-u", "http_server.py") `
        -WorkingDirectory $Project
    Start-Sleep -Seconds 3

    if (-not (Get-NetTCPConnection -LocalPort 8000 -State Listen `
        -ErrorAction SilentlyContinue)) {
        throw "MCP server did not start on port 8000."
    }
}

# Start the proxy only if port 8001 is not already listening.
$ProxyPort = Get-NetTCPConnection -LocalPort 8001 -State Listen `
    -ErrorAction SilentlyContinue

if ($ProxyPort) {
    Write-Host "Authentication proxy already listening on port 8001; reusing it."
}
else {
    Write-Host "Starting authentication proxy..."
    Start-Process -FilePath $Python `
        -ArgumentList @("-u", "proxy_server.py") `
        -WorkingDirectory $Project
    Start-Sleep -Seconds 3

    if (-not (Get-NetTCPConnection -LocalPort 8001 -State Listen `
        -ErrorAction SilentlyContinue)) {
        throw "Authentication proxy did not start on port 8001."
    }
}

Write-Host "MCP server and authentication proxy are listening."
Write-Host "This script does not manage automatic restarts or the HTTPS tunnel."
