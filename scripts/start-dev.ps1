$ErrorActionPreference="Stop"
$root=(Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $root
if(-not(Test-Path .venv\Scripts\python.exe)){throw "Portal environment is missing. Run .\scripts\setup-dev.ps1 first."}
if(-not(Get-Command npm -ErrorAction SilentlyContinue)){throw "npm is required."}
if(-not(Test-Path web\node_modules\.bin\vite.cmd)){throw "Frontend dependencies are missing. Run .\scripts\setup-dev.ps1 (or npm install inside web) first."}

$backend=$null;$mcp=$null;$gateway=$null
try {
  $backend=Start-Process -FilePath ".\.venv\Scripts\python.exe" -ArgumentList "-m","uvicorn","backend.app.main:app","--reload","--host","127.0.0.1","--port","8000" -WorkingDirectory $root -PassThru
  for($i=0;$i -lt 40;$i++){try{$r=Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/health -TimeoutSec 1;if($r.StatusCode -eq 200){break}}catch{};Start-Sleep -Milliseconds 250}

  if(Test-Path .venv-agent\Scripts\python.exe){
    if(-not(Test-Path agent\dsh\node_modules\.bin\dsh.cmd)){throw "Embedded DataAgent dsh dependencies are missing. Run .\scripts\setup-agent.ps1 first."}
    if(-not(Test-Path .local\dsh-home\profiles\dataagent-headless\package.json)){throw "Headless DataAgent profile is missing. Run .\scripts\setup-agent.ps1 first."}
    $env:AGENT3_MCP_POC_MODE="1"
    $env:DATACONTROL_PORTAL_URL="http://127.0.0.1:8000/api/v1"
    $env:DSH_HOME=(Join-Path $root ".local\dsh-home")
    $env:DSH_TELEMETRY_MODE="DISABLED"
    $mcp=Start-Process -FilePath ".\.venv-agent\Scripts\python.exe" -ArgumentList "-m","agent3.adapters.mcp.server" -WorkingDirectory (Join-Path $root "agent") -RedirectStandardOutput (Join-Path $root ".local\agent-mcp.log") -RedirectStandardError (Join-Path $root ".local\agent-mcp.err.log") -PassThru
    Start-Sleep -Milliseconds 900
    $gateway=Start-Process -FilePath ".\.venv-agent\Scripts\python.exe" -ArgumentList "-m","uvicorn","dataagent_gateway.app:app","--host","127.0.0.1","--port","8910" -WorkingDirectory $root -RedirectStandardOutput (Join-Path $root ".local\agent-gateway.log") -RedirectStandardError (Join-Path $root ".local\agent-gateway.err.log") -PassThru
    Write-Host "Agent3 MCP:       http://127.0.0.1:8900/mcp"
    Write-Host "DataAgent Gateway: http://127.0.0.1:8910"
    if([string]::IsNullOrWhiteSpace($env:DEEPSEEK_API_KEY)){Write-Warning "DEEPSEEK_API_KEY is not set; Agent Gateway will stay degraded until the key is provided before startup."}
  }else{
    Write-Warning "Embedded DataAgent skipped because .venv-agent is missing. Run .\scripts\setup-agent.ps1."
  }

  Write-Host "DataControl API:  http://127.0.0.1:8000"
  Write-Host "DataControl Web:  http://127.0.0.1:5173"
  Push-Location web
  try{npm run dev}finally{Pop-Location}
} finally {
  foreach($proc in @($gateway,$mcp,$backend)){if($proc -and -not $proc.HasExited){Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue}}
}
