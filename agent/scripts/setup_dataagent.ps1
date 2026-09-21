[CmdletBinding()]
param([string]$DshHome="")
$ErrorActionPreference="Stop"
$agentRoot=(Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$repoRoot=(Resolve-Path (Join-Path $agentRoot "..")).Path
if ([string]::IsNullOrWhiteSpace($DshHome)) { $DshHome=Join-Path $repoRoot ".local\dsh-home" }
$env:DSH_HOME=[System.IO.Path]::GetFullPath($DshHome); $env:DSH_TELEMETRY_MODE="DISABLED"
$dshBin=Join-Path $agentRoot "dsh\node_modules\.bin\dsh.cmd"; $guardDir=Join-Path $agentRoot "guard-plugin"; $profile=Join-Path $env:DSH_HOME "profiles\dataagent"
if (-not (Test-Path $dshBin)) { throw "DeepSeek Harness is not installed. Run .\scripts\setup-agent.ps1 first." }
New-Item -ItemType Directory -Force -Path $env:DSH_HOME | Out-Null
if ((Test-Path $profile) -and -not (Test-Path (Join-Path $profile "package.json"))) { Remove-Item -Recurse -Force $profile }
Push-Location $repoRoot
try {
  if (-not (Test-Path (Join-Path $profile "package.json"))) { & $dshBin --profile dataagent --from-default-profile web --dump-config | Out-Null; if ($LASTEXITCODE -ne 0) { throw "dsh profile initialization failed" } }
  $pkg=Get-Content (Join-Path $profile "package.json") -Raw
  if ($pkg -notmatch '@hunter-zk/agent3-guard') { & $dshBin plugin --profile dataagent add $guardDir; if ($LASTEXITCODE -ne 0) { throw "guard plugin install failed" } }
  Copy-Item (Join-Path $agentRoot "dsh\profile\cordis.patch.yml") (Join-Path $profile "cordis.patch.yml") -Force
  $config=& $dshBin --profile dataagent --dump-config 2>&1 | Out-String
  if ($LASTEXITCODE -ne 0) { throw $config }
  foreach($required in @('deepseek-official','mcp-agent3','agent3-guard','dataagent-query')) { if ($config -notmatch [regex]::Escape($required)) { throw "DataAgent profile missing $required" } }
  if ($config -match '127\.0\.0\.1:8100|deepseek-v3-local|LOCAL_LLM_KEY') { throw "Retired local LLM config detected" }
} finally { Pop-Location }
Write-Host "DataAgent dsh profile ready: $env:DSH_HOME (profile=dataagent)"
