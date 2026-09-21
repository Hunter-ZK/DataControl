[CmdletBinding()]
param([string]$DshHome="")
$ErrorActionPreference="Stop"
$agentRoot=(Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$repoRoot=(Resolve-Path (Join-Path $agentRoot "..")).Path
if ([string]::IsNullOrWhiteSpace($DshHome)) { $DshHome=Join-Path $repoRoot ".local\dsh-home" }
$env:DSH_HOME=[System.IO.Path]::GetFullPath($DshHome)
$env:DSH_TELEMETRY_MODE="DISABLED"
$dshBin=Join-Path $agentRoot "dsh\node_modules\.bin\dsh.cmd"
$guardDir=Join-Path $agentRoot "guard-plugin"
$patch=Join-Path $agentRoot "dsh\profile\cordis.patch.yml"
if (-not (Test-Path $dshBin)) { throw "DeepSeek Harness is not installed. Run .\scripts\setup-agent.ps1 first." }
New-Item -ItemType Directory -Force -Path $env:DSH_HOME | Out-Null

$profiles=@(
  @{ Name="dataagent"; Base="web" },
  @{ Name="dataagent-headless"; Base="headless" }
)

Push-Location $repoRoot
try {
  foreach($entry in $profiles) {
    $name=$entry.Name
    $base=$entry.Base
    $profile=Join-Path $env:DSH_HOME ("profiles\"+$name)
    if ((Test-Path $profile) -and -not (Test-Path (Join-Path $profile "package.json"))) {
      Remove-Item -Recurse -Force $profile
    }
    if (-not (Test-Path (Join-Path $profile "package.json"))) {
      & $dshBin --profile $name --from-default-profile $base --dump-config | Out-Null
      if ($LASTEXITCODE -ne 0) { throw "dsh profile initialization failed: $name" }
    }
    $pkg=Get-Content (Join-Path $profile "package.json") -Raw
    if ($pkg -notmatch '@hunter-zk/agent3-guard') {
      & $dshBin plugin --profile $name add $guardDir
      if ($LASTEXITCODE -ne 0) { throw "guard plugin install failed: $name" }
    }
    Copy-Item $patch (Join-Path $profile "cordis.patch.yml") -Force
    $config=& $dshBin --profile $name --dump-config 2>&1 | Out-String
    if ($LASTEXITCODE -ne 0) { throw $config }
    foreach($required in @('deepseek-official','mcp-agent3','agent3-guard','dataagent-query')) {
      if ($config -notmatch [regex]::Escape($required)) { throw "DataAgent profile $name missing $required" }
    }
    if ($config -match '127\.0\.0\.1:8100|deepseek-v3-local|LOCAL_LLM_KEY') {
      throw "Retired local LLM config detected in $name"
    }
  }
} finally { Pop-Location }
Write-Host "DataAgent dsh profiles ready: dataagent + dataagent-headless ($env:DSH_HOME)"
