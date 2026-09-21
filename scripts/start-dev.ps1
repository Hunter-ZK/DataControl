[CmdletBinding()]
param([switch]$SkipAgent)

$ErrorActionPreference="Stop"
$root=(Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $root

$portalPython=Join-Path $root ".venv\Scripts\python.exe"
$agentPython=Join-Path $root ".venv-agent\Scripts\python.exe"
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
  if(Test-Path $Path){ return ((Get-Content $Path -Tail 40) -join [Environment]::NewLine) }
  return "(no log file: $Path)"
}

function Test-TcpPort([int]$Port) {
  $client=$null
  try {
    $client=[System.Net.Sockets.TcpClient]::new()
    $task=$client.ConnectAsync("127.0.0.1",$Port)
    if(-not $task.Wait(350)){ return $false }
    return $client.Connected
  } catch { return $false }
  finally { if($client){$client.Dispose()} }
}

function Assert-PortFree([int]$Port,[string]$Name) {
  if(-not (Test-TcpPort $Port)){ return }
  $owners=@()
  try {
    $owners=@(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction Stop | Select-Object -ExpandProperty OwningProcess -Unique)
  } catch {}
  $detail=""
  if($owners.Count -gt 0){
    $parts=@()
    foreach($owner in $owners){
      try {
        $proc=Get-Process -Id $owner -ErrorAction Stop
        $parts += ("PID {0} ({1})" -f $owner,$proc.ProcessName)
      } catch {
        $parts += ("PID {0}" -f $owner)
      }
    }
    $detail=" Occupied by " + ($parts -join ",") + "."
  }
  throw "$Name cannot start because port $Port is already in use.$detail Stop the stale process first, then rerun .\scripts\start-dev.ps1."
}

function Wait-ServicePort(
  [System.Diagnostics.Process]$Process,
  [int]$Port,
  [string]$Name,
  [string]$ErrorLog,
  [int]$TimeoutSeconds=25
) {
  $deadline=(Get-Date).AddSeconds($TimeoutSeconds)
  while((Get-Date) -lt $deadline){
    $Process.Refresh()
    if($Process.HasExited){
      throw "$Name exited before binding port $Port (exit=$($Process.ExitCode)).`n--- $Name stderr ---`n$(Get-LogTail $ErrorLog)"
    }
    if(Test-TcpPort $Port){ return }
    Start-Sleep -Milliseconds 250
  }
  throw "$Name did not bind port $Port within ${TimeoutSeconds}s.`n--- $Name stderr ---`n$(Get-LogTail $ErrorLog)"
}

function Wait-HttpEndpoint(
  [System.Diagnostics.Process]$Process,
  [string]$Url,
  [string]$Name,
  [string]$ErrorLog,
  [int]$TimeoutSeconds=25
) {
  $deadline=(Get-Date).AddSeconds($TimeoutSeconds)
  while((Get-Date) -lt $deadline){
    $Process.Refresh()
    if($Process.HasExited){
      throw "$Name exited before becoming reachable (exit=$($Process.ExitCode)).`n--- $Name stderr ---`n$(Get-LogTail $ErrorLog)"
    }
    try {
      $r=Invoke-WebRequest -UseBasicParsing $Url -TimeoutSec 1
      if($r.StatusCode -ge 200 -and $r.StatusCode -lt 500){ return }
    } catch {}
    Start-Sleep -Milliseconds 250
  }
  throw "$Name did not become reachable at $Url within ${TimeoutSeconds}s.`n--- $Name stderr ---`n$(Get-LogTail $ErrorLog)"
}

if(-not(Test-Path $portalPython)){throw "Portal environment is missing. Run .\scripts\setup-dev.ps1 first."}
if(-not(Get-Command npm -ErrorAction SilentlyContinue)){throw "npm is required."}
if(-not(Test-Path (Join-Path $root "web\node_modules\.bin\vite.cmd"))){throw "Frontend dependencies are missing. Run .\scripts\setup-dev.ps1 (or npm install inside web) first."}
New-Item -ItemType Directory -Force -Path $localDir | Out-Null

if(-not $SkipAgent){
  if(-not(Test-Path $agentPython)){throw "Embedded DataAgent environment is missing. Run .\scripts\setup-agent.ps1 first (Python 3.14 required). Use -SkipAgent only when intentionally starting Portal/Web without intelligent Q&A."}
  if(-not(Test-Path $dshBin)){throw "Embedded DataAgent dsh dependencies are missing. Run .\scripts\setup-agent.ps1 first."}
  if(-not(Test-Path $headlessProfile)){throw "Headless DataAgent profile is missing. Run .\scripts\setup-agent.ps1 first."}
}

Assert-PortFree -Port 8000 -Name "DataControl API"
if(-not $SkipAgent){
  Assert-PortFree -Port 8900 -Name "Agent3 MCP"
  Assert-PortFree -Port 8910 -Name "DataAgent Gateway"
}

$backend=$null;$mcp=$null;$gateway=$null
try {
  Remove-Item $backendOut,$backendErr,$mcpOut,$mcpErr,$gatewayOut,$gatewayErr -Force -ErrorAction SilentlyContinue

  # Deliberately do not use uvicorn --reload here. The reload supervisor can leave
  # a worker process bound to port 8000 after the parent is stopped, which makes a
  # later acceptance run talk to stale Portal code.
  $backend=Start-Process -FilePath $portalPython -ArgumentList "-m","uvicorn","backend.app.main:app","--host","127.0.0.1","--port","8000" -WorkingDirectory $root -RedirectStandardOutput $backendOut -RedirectStandardError $backendErr -PassThru
  Wait-HttpEndpoint -Process $backend -Url "http://127.0.0.1:8000/health" -Name "DataControl API" -ErrorLog $backendErr -TimeoutSeconds 20

  $portalHealth=Invoke-RestMethod http://127.0.0.1:8000/health -TimeoutSec 2
  if($portalHealth.runtimeContract -ne $expectedRuntimeContract){
    throw "DataControl API runtime contract mismatch. Expected '$expectedRuntimeContract' but got '$($portalHealth.runtimeContract)'. A stale Portal process or stale checkout is being used."
  }

  if(-not $SkipAgent){
    $env:AGENT3_MCP_POC_MODE="1"
    $env:DATACONTROL_PORTAL_URL="http://127.0.0.1:8000/api/v1"
    $env:DSH_HOME=(Join-Path $root ".local\dsh-home")
    $env:DSH_TELEMETRY_MODE="DISABLED"

    $mcp=Start-Process -FilePath $agentPython -ArgumentList "-m","agent3.adapters.mcp.server" -WorkingDirectory (Join-Path $root "agent") -RedirectStandardOutput $mcpOut -RedirectStandardError $mcpErr -PassThru
    Wait-ServicePort -Process $mcp -Port 8900 -Name "Agent3 MCP" -ErrorLog $mcpErr -TimeoutSeconds 30

    $gateway=Start-Process -FilePath $agentPython -ArgumentList "-m","uvicorn","dataagent_gateway.app:app","--host","127.0.0.1","--port","8910" -WorkingDirectory $root -RedirectStandardOutput $gatewayOut -RedirectStandardError $gatewayErr -PassThru
    Wait-HttpEndpoint -Process $gateway -Url "http://127.0.0.1:8910/health" -Name "DataAgent Gateway" -ErrorLog $gatewayErr -TimeoutSeconds 25

    $gatewayHealth=Invoke-RestMethod http://127.0.0.1:8910/health -TimeoutSec 2
    Write-Host "Agent3 MCP:        READY http://127.0.0.1:8900/mcp"
    if($gatewayHealth.ready){
      Write-Host "DataAgent Gateway: READY http://127.0.0.1:8910"
    } else {
      Write-Warning ("DataAgent Gateway is running but degraded: " + [string]$gatewayHealth.reason)
    }
    if([string]::IsNullOrWhiteSpace($env:DEEPSEEK_API_KEY)){Write-Warning "DEEPSEEK_API_KEY is not set; Agent Gateway is expected to be degraded until DataControl is restarted with the key present."}
  } else {
    Write-Warning "Embedded DataAgent intentionally skipped (-SkipAgent). Intelligent Q&A will be unavailable."
  }

  Write-Host "DataControl API:   READY http://127.0.0.1:8000 ($expectedRuntimeContract)"
  Write-Host "DataControl Web:         http://127.0.0.1:5173"
  Push-Location web
  try{npm run dev}finally{Pop-Location}
} finally {
  foreach($proc in @($gateway,$mcp,$backend)){if($proc -and -not $proc.HasExited){Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue}}
}
