[CmdletBinding()]
param([switch]$SkipAgent)

$ErrorActionPreference="Stop"
$root=(Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $root

$python=Join-Path $root ".venv\Scripts\python.exe"
$dshBin=Join-Path $root "agent\dsh\node_modules\.bin\dsh.cmd"
$headlessProfile=Join-Path $root ".local\dsh-home\profiles\dataagent-headless\package.json"
$localDir=Join-Path $root ".local"
$backendOut=Join-Path $localDir "backend.log"
$backendErr=Join-Path $localDir "backend.err.log"
$mcpOut=Join-Path $localDir "agent-mcp.log"
$mcpErr=Join-Path $localDir "agent-mcp.err.log"
$gatewayOut=Join-Path $localDir "agent-gateway.log"
$gatewayErr=Join-Path $localDir "agent-gateway.err.log"
$expectedRuntimeContract="embedded-agent-gateway-v1"

function Get-LogTail([string]$Path) {
  if(Test-Path $Path){ return ((Get-Content $Path -Tail 60) -join [Environment]::NewLine) }
  return "(no log file: $Path)"
}
function Test-TcpPort([int]$Port) {
  $client=$null
  try {$client=[System.Net.Sockets.TcpClient]::new();$task=$client.ConnectAsync("127.0.0.1",$Port);if(-not $task.Wait(350)){return $false};return $client.Connected}
  catch{return $false}
  finally{if($client){$client.Dispose()}}
}
function Assert-PortFree([int]$Port,[string]$Name) {
  if(-not(Test-TcpPort $Port)){return}
  throw "$Name cannot start because port $Port is already in use. Stop the stale process first, then rerun .\scripts\start-dev.ps1."
}
function Wait-ServicePort([System.Diagnostics.Process]$Process,[int]$Port,[string]$Name,[string]$ErrorLog,[int]$TimeoutSeconds=25) {
  $deadline=(Get-Date).AddSeconds($TimeoutSeconds)
  while((Get-Date)-lt $deadline){$Process.Refresh();if($Process.HasExited){throw "$Name exited before binding port $Port (exit=$($Process.ExitCode)).`n--- $Name stderr ---`n$(Get-LogTail $ErrorLog)"};if(Test-TcpPort $Port){return};Start-Sleep -Milliseconds 250}
  throw "$Name did not bind port $Port within ${TimeoutSeconds}s.`n--- $Name stderr ---`n$(Get-LogTail $ErrorLog)"
}
function Wait-HttpEndpoint([System.Diagnostics.Process]$Process,[string]$Url,[string]$Name,[string]$ErrorLog,[int]$TimeoutSeconds=25) {
  $deadline=(Get-Date).AddSeconds($TimeoutSeconds)
  while((Get-Date)-lt $deadline){
    $Process.Refresh()
    if($Process.HasExited){throw "$Name exited before becoming reachable (exit=$($Process.ExitCode)).`n--- $Name stderr ---`n$(Get-LogTail $ErrorLog)"}
    # A service that is still binding normally refuses the first few HTTP
    # connections. Keep that expected condition silent so Windows PowerShell
    # does not convert Python's traceback on stderr into a NativeCommandError
    # while $ErrorActionPreference is Stop.
    & $python -c "import httpx,sys; u=sys.argv[1]; ok=False;`ntry:`n r=httpx.get(u,timeout=1.0,trust_env=False); ok=r.status_code<500`nexcept Exception:`n pass`nraise SystemExit(0 if ok else 1)" $Url
    if($LASTEXITCODE -eq 0){return}
    Start-Sleep -Milliseconds 250
  }
  throw "$Name did not become reachable at $Url within ${TimeoutSeconds}s.`n--- $Name stderr ---`n$(Get-LogTail $ErrorLog)"
}

if(-not(Test-Path $python)){throw "DataControl environment is missing. Run .\scripts\setup-dev.ps1 first."}
& $python -c "import sys; raise SystemExit(0 if (3,13) <= sys.version_info[:2] < (3,15) else 1)"
if($LASTEXITCODE -ne 0){throw "DataControl .venv must use Python 3.13 or 3.14."}
if(-not(Get-Command npm -ErrorAction SilentlyContinue)){throw "npm is required."}
if(-not(Test-Path (Join-Path $root "web\node_modules\.bin\vite.cmd"))){throw "Frontend dependencies are missing. Run .\scripts\setup-dev.ps1 first."}
New-Item -ItemType Directory -Force -Path $localDir | Out-Null

# Preserve any external proxy needed for model traffic while guaranteeing that
# Portal/Gateway/MCP loopback traffic is never sent through it.
$existingNoProxy=[string]$env:NO_PROXY
$loopbackNoProxy="127.0.0.1,localhost,::1"
if([string]::IsNullOrWhiteSpace($existingNoProxy)){$env:NO_PROXY=$loopbackNoProxy}else{$env:NO_PROXY="$loopbackNoProxy,$existingNoProxy"}
$env:no_proxy=$env:NO_PROXY

if(-not $SkipAgent){
  & $python -c "import agent3, dataagent_gateway" 2>$null
  $agentImportsOk=$LASTEXITCODE -eq 0
  if(-not $agentImportsOk -or -not(Test-Path $dshBin) -or -not(Test-Path $headlessProfile)){
    Write-Host "Embedded DataAgent setup is incomplete; bootstrapping it in the shared .venv now..."
    & .\scripts\setup-agent.ps1
  }
  & $python -c "import agent3, dataagent_gateway"
  if($LASTEXITCODE -ne 0){throw "Embedded DataAgent package is unavailable after setup."}
}

Assert-PortFree 8000 "DataControl API"
if(-not $SkipAgent){Assert-PortFree 8900 "Agent3 MCP";Assert-PortFree 8910 "DataAgent Gateway"}

$backend=$null;$mcp=$null;$gateway=$null
try {
  Remove-Item $backendOut,$backendErr,$mcpOut,$mcpErr,$gatewayOut,$gatewayErr -Force -ErrorAction SilentlyContinue
  $backend=Start-Process -FilePath $python -ArgumentList "-m","uvicorn","backend.app.main:app","--host","127.0.0.1","--port","8000" -WorkingDirectory $root -RedirectStandardOutput $backendOut -RedirectStandardError $backendErr -PassThru
  Wait-HttpEndpoint $backend "http://127.0.0.1:8000/health" "DataControl API" $backendErr 20

  $healthJson=& $python -c "import httpx,json; r=httpx.get('http://127.0.0.1:8000/health',timeout=2.0,trust_env=False); r.raise_for_status(); print(json.dumps(r.json()))"
  if($LASTEXITCODE -ne 0){throw "DataControl API health request failed without proxy."
  }
  $portalHealth=$healthJson | ConvertFrom-Json
  if($portalHealth.runtimeContract -ne $expectedRuntimeContract){throw "DataControl API runtime contract mismatch. Expected '$expectedRuntimeContract' but got '$($portalHealth.runtimeContract)'."}

  if(-not $SkipAgent){
    & $python -c "import httpx; c=httpx.Client(timeout=10.0,trust_env=False); m=c.get('http://127.0.0.1:8000/api/v1/metrics'); m.raise_for_status(); mp=m.json(); assert isinstance(mp,dict) and isinstance(mp.get('data'),list) and mp['data'], 'Portal has no metric semantics'; t=c.get('http://127.0.0.1:8000/api/v1/tables',params={'limit':1}); t.raise_for_status(); tp=t.json(); assert isinstance(tp,dict) and 'data' in tp; c.close()"
    if($LASTEXITCODE -ne 0){throw "Portal Agent-fact preflight failed. Agent3 requires healthy /api/v1/metrics and /api/v1/tables before MCP can start.`n--- DataControl API stderr ---`n$(Get-LogTail $backendErr)"}
    Write-Host "Portal Agent facts:  READY /api/v1/metrics + /api/v1/tables"

    $env:AGENT3_MCP_POC_MODE="1"
    $env:DATACONTROL_PORTAL_URL="http://127.0.0.1:8000/api/v1"
    $env:DSH_HOME=(Join-Path $root ".local\dsh-home")
    $env:DSH_TELEMETRY_MODE="DISABLED"
    $mcp=Start-Process -FilePath $python -ArgumentList "-m","agent3.adapters.mcp.server" -WorkingDirectory (Join-Path $root "agent") -RedirectStandardOutput $mcpOut -RedirectStandardError $mcpErr -PassThru
    Wait-ServicePort $mcp 8900 "Agent3 MCP" $mcpErr 30
    $gateway=Start-Process -FilePath $python -ArgumentList "-m","uvicorn","dataagent_gateway.app:app","--host","127.0.0.1","--port","8910" -WorkingDirectory $root -RedirectStandardOutput $gatewayOut -RedirectStandardError $gatewayErr -PassThru
    Wait-HttpEndpoint $gateway "http://127.0.0.1:8910/health" "DataAgent Gateway" $gatewayErr 25

    $gatewayHealthJson=& $python -c "import httpx,json; r=httpx.get('http://127.0.0.1:8910/health',timeout=2.0,trust_env=False); r.raise_for_status(); print(json.dumps(r.json()))"
    $gatewayHealth=$gatewayHealthJson | ConvertFrom-Json
    Write-Host "Agent3 MCP:        READY http://127.0.0.1:8900/mcp"
    if($gatewayHealth.ready){Write-Host "DataAgent Gateway: READY http://127.0.0.1:8910"}else{Write-Warning ("DataAgent Gateway is running but degraded: "+[string]$gatewayHealth.reason)}
    if([string]::IsNullOrWhiteSpace($env:DEEPSEEK_API_KEY)){Write-Warning "DEEPSEEK_API_KEY is not set; Agent Gateway will be degraded until DataControl is restarted with the key present."}
  }

  Write-Host ("Python runtime:      "+(& $python --version))
  Write-Host "DataControl API:    READY http://127.0.0.1:8000 ($expectedRuntimeContract)"
  Write-Host "DataControl Web:          http://127.0.0.1:5173"
  Push-Location web
  try{npm run dev}finally{Pop-Location}
} finally {
  foreach($proc in @($gateway,$mcp,$backend)){if($proc -and -not $proc.HasExited){Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue}}
}