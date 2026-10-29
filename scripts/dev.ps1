[CmdletBinding()]
param(
  [ValidateSet("start", "setup", "repair", "stop")]
  [string]$Action = "start",
  [switch]$SkipAgent
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "agent-profile-state.ps1")
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $root
$env:DATACONTROL_ADMIN_WORKBENCH_ENABLED = "1"
$local = Join-Path $root ".local"
$python = Join-Path $root ".venv\Scripts\python.exe"
$vite = Join-Path $root "web\node_modules\.bin\vite.cmd"
$portalMarker = Join-Path $local "portal-setup-ready.txt"
$agentMarker = Join-Path $local "agent-setup-v0.2.1-rc.3-profile2.ready"
$dsh = Join-Path $root "agent\dsh\node_modules\.bin\dsh.cmd"
$headless = Join-Path $local "dsh-home-v0.2.1-rc.3\profiles\dataagent-headless\package.json"

function Test-PortalReady {
  if (-not ((Test-Path $python) -and (Test-Path $vite))) { return $false }
  & $python -c "import importlib.util as u; raise SystemExit(0 if all(u.find_spec(n) for n in ('backend.app.main','alembic','httpx')) else 1)"
  if ($LASTEXITCODE -ne 0) { return $false }
  if (Test-Path $portalMarker) { return $true }

  # Older setup-dev runs predate the marker. Reuse only an intact demo corpus.
  $legacyFiles = @(
    (Join-Path $local "datacontrol.db"),
    (Join-Path $local "search.db"),
    (Join-Path $local "p2-question-bank.json"),
    (Join-Path $local "p3-question-bank.json")
  )
  foreach ($file in $legacyFiles) {
    if (-not (Test-Path $file)) { return $false }
  }
  Set-Content -LiteralPath $portalMarker -Value "Existing Portal corpus validated" -Encoding UTF8
  return $true
}

function Test-AgentReady {
  if (-not ((Test-Path $agentMarker) -and (Test-Path $dsh) -and (Test-Path $headless))) {
    return $false
  }
  if (-not (Test-DataAgentProfilesCurrent -RepoRoot $root)) {
    Write-Host "[DataControl] Agent profile differs from current source; rebuilding its configuration..."
    return $false
  }
  if (-not (Test-Path (Join-Path $root "agent\guard-plugin\dist\index.js"))) {
    return $false
  }
  & $python -c "import importlib.util as u; raise SystemExit(0 if all(u.find_spec(n) for n in ('agent3','dataagent_gateway')) else 1)"
  return ($LASTEXITCODE -eq 0)
}

function Import-LocalKey {
  if (-not [string]::IsNullOrWhiteSpace($env:DEEPSEEK_API_KEY)) { return }
  $dotenv = Join-Path $root ".env"
  if (-not (Test-Path $dotenv)) { return }
  foreach ($line in (Get-Content -LiteralPath $dotenv -Encoding UTF8)) {
    if ($line -match '^\s*(?:export\s+)?DEEPSEEK_API_KEY\s*=\s*(.*?)\s*$') {
      $value = $Matches[1].Trim().Trim('"').Trim("'")
      if ($value) { $env:DEEPSEEK_API_KEY = $value }
      break
    }
  }
}

if ($Action -eq "stop") {
  & (Join-Path $root "scripts\stop-dev.ps1")
  return
}

if (-not (Get-Command node -ErrorAction SilentlyContinue) -or
    -not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) {
  throw "Node.js 24 and npm are required. Install Node.js 24 LTS and reopen this terminal."
}
$nodeMajor = & node -p "Number(process.versions.node.split('.')[0])"
if ($LASTEXITCODE -ne 0 -or [int]$nodeMajor -lt 24) {
  throw "This branch requires Node.js 24+; current version: $(& node --version)"
}

New-Item -ItemType Directory -Force -Path $local | Out-Null
if (-not (Test-PortalReady)) {
  Write-Host "[DataControl] Initializing Portal, sample data and frontend..."
  & (Join-Path $root "scripts\setup-dev.ps1") -SkipAgent
  if (-not (Test-PortalReady)) { throw "Portal setup failed. Check the error above." }
} else {
  Write-Host "[DataControl] Portal and frontend already installed; skipping setup."
}

Write-Host "[DataControl] Applying database migrations..."
& $python -m alembic upgrade head
if ($LASTEXITCODE -ne 0) { throw "Database migration failed. Check the Alembic output above." }

if (-not $SkipAgent) {
  if ($Action -eq "repair") {
    Write-Host "[DataControl] Repairing Agent packages and generated dsh profiles..."
    & (Join-Path $root "scripts\setup-agent.ps1") -Repair
  } elseif (-not (Test-AgentReady)) {
    Write-Host "[DataControl] Installing or repairing missing Agent dependencies..."
    & (Join-Path $root "scripts\setup-agent.ps1")
  } else {
    Write-Host "[DataControl] Agent already installed; skipping setup."
  }
  if (-not (Test-AgentReady)) {
    throw "Agent initialization is incomplete. Run .\start.bat repair. For profile errors inspect .local\dsh-profile-command.stderr.log; for npm errors inspect .local\npm-dsh.stderr.log."
  }
}

if ($Action -eq "setup") {
  Write-Host "[DataControl] Setup complete. Run .\start.bat to launch."
  return
}

Import-LocalKey
if (-not $SkipAgent -and [string]::IsNullOrWhiteSpace($env:DEEPSEEK_API_KEY)) {
  Write-Warning "DeepSeek key is missing. Real Agent queries require DEEPSEEK_API_KEY in the environment or the local git-ignored .env file."
}
Write-Host "[DataControl] Starting at http://127.0.0.1:5173 (Ctrl+C to stop)."
& (Join-Path $root "scripts\start-dev.ps1") -SkipAgent:$SkipAgent
