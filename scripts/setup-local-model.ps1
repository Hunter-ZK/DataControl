[CmdletBinding()]
param()
$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$python = Join-Path $root ".venv\Scripts\python.exe"
$dshDir = Join-Path $root "agent\dsh\node_modules\.bin"
$dsh = Join-Path $dshDir "dsh.cmd"
$helper = Join-Path $root "agent\scripts\dsh_profile_cli.py"
$dshHome = Join-Path $root ".local\dsh-home-v0.2.1-rc.3"
$logs = Join-Path $root ".local"
if (-not(Test-Path $python)) { throw "Shared .venv is missing. Run start.bat setup first." }
if (-not(Test-Path $dsh)) { throw "Pinned dsh is missing. Run .\scripts\setup-agent.ps1 first." }
$env:DSH_HOME = $dshHome
$env:DSH_TELEMETRY_MODE = "DISABLED"
$env:PATH = "$dshDir;$env:PATH"
if ([string]::IsNullOrEmpty($env:DATACONTROL_LOCAL_MODEL_API_KEY)) {
  $env:DATACONTROL_LOCAL_MODEL_API_KEY = "local-no-key-required"
}
New-Item -ItemType Directory -Force -Path $logs,$dshHome | Out-Null

& $python -m dataagent_gateway.local_provider probe
if ($LASTEXITCODE -ne 0) { throw "Local llama.cpp is offline or model selection is ambiguous. Check /v1/models." }

function Invoke-Profile([string[]]$CliArguments) {
  $out = Join-Path $logs "local-model-profile.stdout.log"
  $err = Join-Path $logs "local-model-profile.stderr.log"
  & $python $helper --executable $dsh --cwd $root --stdout $out --stderr $err -- @CliArguments
  if ($LASTEXITCODE -ne 0) {
    $detail = if (Test-Path $err) { Get-Content -LiteralPath $err -Raw -Encoding UTF8 } else { "" }
    throw "dsh local model profile failed: $detail"
  }
  return Get-Content -LiteralPath $out -Raw -Encoding UTF8
}
foreach ($entry in @(
  @{Name="dataagent-headless-local";Tier="standard"},
  @{Name="dataagent-headless-local-multi";Tier="multi"}
)) {
  $name = [string]$entry.Name
  $tier = [string]$entry.Tier
  $dir = Join-Path $dshHome ("profiles\" + $name)
  if ((Test-Path $dir) -and -not(Test-Path (Join-Path $dir "package.json"))) {
    $backupDir = Join-Path $dshHome "profile-backups"
    New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
    Move-Item -LiteralPath $dir -Destination (Join-Path $backupDir "$name-$([DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss-fff'))")
  }
  if (-not(Test-Path (Join-Path $dir "package.json"))) {
    $null = Invoke-Profile -CliArguments @("--profile", $name, "--from-default-profile", "headless", "--dump-config")
  }
  & $python -m dataagent_gateway.local_provider write-profile --profile-dir $dir --task-tier $tier
  if ($LASTEXITCODE -ne 0) { throw "Cannot render local profile $name" }
  $configured = Invoke-Profile @("--profile", $name, "--dump-config")
  foreach ($marker in @("local-llama", "llm-pi-ai", "mcp-agent3", "agent3-guard", "DataControl DataAgent")) {
    if ($configured -notmatch [regex]::Escape($marker)) {
      throw "Local profile $name is missing required component '$marker' in actual dsh configuration."
    }
  }
  Write-Host "[DataControl] Local $tier Agent profile ready: $name"
}
Write-Host "Local model configured. Start/refresh DataControl and select '本地 DeepSeek' in Agent."
