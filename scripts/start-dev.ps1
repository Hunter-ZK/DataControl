$ErrorActionPreference="Stop";if(-not(Test-Path .venv\Scripts\python.exe)){throw "Run .\scripts\setup-dev.ps1 first."};if(-not(Get-Command npm -ErrorAction SilentlyContinue)){throw "npm is required."}
$backend=Start-Process -FilePath ".\.venv\Scripts\python.exe" -ArgumentList "-m","uvicorn","backend.app.main:app","--reload","--host","127.0.0.1","--port","8000" -WorkingDirectory (Get-Location) -PassThru
Start-Sleep -Milliseconds 800;$mcp=$null
if(Test-Path .venv-agent\Scripts\python.exe){$env:AGENT3_MCP_POC_MODE="1";$env:DATACONTROL_PORTAL_URL="http://127.0.0.1:8000/api/v1";$mcp=Start-Process -FilePath ".\.venv-agent\Scripts\python.exe" -ArgumentList "-m","agent3.adapters.mcp.server" -WorkingDirectory (Join-Path (Get-Location) "agent") -PassThru;Write-Host "Agent3 MCP: http://127.0.0.1:8900/mcp"}else{Write-Warning "Agent3 MCP skipped because .venv-agent is missing"}
Write-Host "DataControl API: http://127.0.0.1:8000";Write-Host "DataControl Web: http://127.0.0.1:5173"
try{Push-Location web;npm run dev}finally{Pop-Location;if($mcp -and -not $mcp.HasExited){Stop-Process -Id $mcp.Id -Force};if($backend -and -not $backend.HasExited){Stop-Process -Id $backend.Id -Force}}
