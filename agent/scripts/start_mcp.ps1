$ErrorActionPreference="Stop"
$root=(Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$python=Join-Path $root ".venv-agent\Scripts\python.exe"
if (-not (Test-Path $python)) { throw "Missing .venv-agent; run .\scripts\setup-agent.ps1" }
$env:AGENT3_MCP_POC_MODE="1"
if ([string]::IsNullOrWhiteSpace($env:DATACONTROL_PORTAL_URL)) { $env:DATACONTROL_PORTAL_URL="http://127.0.0.1:8000/api/v1" }
Push-Location (Join-Path $root "agent")
try { & $python -m agent3.adapters.mcp.server; exit $LASTEXITCODE } finally { Pop-Location }
