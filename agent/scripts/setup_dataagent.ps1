[CmdletBinding()]
param([string]$DshHome="")
$ErrorActionPreference="Stop"
$agentRoot=(Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$repoRoot=(Resolve-Path (Join-Path $agentRoot "..")).Path
if ([string]::IsNullOrWhiteSpace($DshHome)) { $DshHome=Join-Path $repoRoot ".local\dsh-home-v0.2.1-rc.3" }
$env:DSH_HOME=[System.IO.Path]::GetFullPath($DshHome)
$env:DSH_TELEMETRY_MODE="DISABLED"
$dshBinDir=Join-Path $agentRoot "dsh\node_modules\.bin"
$dshBin=Join-Path $dshBinDir "dsh.cmd"
$pnpmBin=Join-Path $dshBinDir "pnpm.cmd"
$guardDir=Join-Path $agentRoot "guard-plugin"
$webPatch=Join-Path $agentRoot "dsh\profile\cordis.patch.yml"
$headlessPatch=Join-Path $agentRoot "dsh\profile\headless.patch.yml"
$multiPatch=Join-Path $agentRoot "dsh\profile\headless-multi.patch.yml"
if (-not (Test-Path $dshBin)) { throw "DeepSeek Harness is not installed. Run .\scripts\setup-agent.ps1 first." }
if (-not (Test-Path $pnpmBin)) { throw "Pinned pnpm is missing from agent\dsh. Run .\scripts\setup-agent.ps1 again." }
$env:PATH="$dshBinDir;$env:PATH"
New-Item -ItemType Directory -Force -Path $env:DSH_HOME | Out-Null

$profiles=@(
  @{ Name="dataagent"; Base="web"; Patch=$webPatch },
  @{ Name="dataagent-headless"; Base="headless"; Patch=$headlessPatch },
  @{ Name="dataagent-headless-multi"; Base="headless"; Patch=$multiPatch }
)

$python=Join-Path $repoRoot ".venv\\Scripts\\python.exe"
if (-not (Test-Path $python)) {
  $pythonCommand=Get-Command python -ErrorAction SilentlyContinue
  if (-not $pythonCommand) { throw "Python 3.13/3.14 is required for dsh profile bootstrap." }
  $python=$pythonCommand.Source
}
$cliHelper=Join-Path $PSScriptRoot "dsh_profile_cli.py"
$localLogs=Join-Path $repoRoot ".local"
New-Item -ItemType Directory -Force -Path $localLogs | Out-Null

function Invoke-DshProfile([string[]]$CliArguments) {
  $outLog=Join-Path $localLogs "dsh-profile-command.stdout.log"
  $errLog=Join-Path $localLogs "dsh-profile-command.stderr.log"
  & $python $cliHelper --executable $dshBin --cwd $repoRoot --stdout $outLog --stderr $errLog -- @CliArguments
  $exitCode=$LASTEXITCODE
  if ($exitCode -ne 0) {
    $details=if (Test-Path $errLog) { Get-Content -LiteralPath $errLog -Raw -Encoding UTF8 } else { "(no stderr)" }
    throw "dsh CLI failed (exit=$exitCode) while setting up profile. $details"
  }
  if (Test-Path $outLog) { return Get-Content -LiteralPath $outLog -Raw -Encoding UTF8 }
  return ""
}


function Backup-StaleProfile([string]$ProfilePath, [string]$Name) {
  $backupRoot=Join-Path $env:DSH_HOME "profile-backups"
  New-Item -ItemType Directory -Force -Path $backupRoot | Out-Null
  $backupName="$Name-$([DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss-fff'))"
  $backup=Join-Path $backupRoot $backupName
  Move-Item -LiteralPath $ProfilePath -Destination $backup -ErrorAction Stop
  Write-Warning "Preserved stale dsh profile '$Name' at $backup"
  return $backup
}

Push-Location $repoRoot
try {
  foreach($entry in $profiles) {
    $name=$entry.Name
    $base=$entry.Base
    $patch=$entry.Patch
    $profileDir=Join-Path $env:DSH_HOME ("profiles\"+$name)
    if ((Test-Path -LiteralPath $profileDir) -and -not (Test-Path (Join-Path $profileDir "package.json"))) {
      # An incomplete profile may still contain sessions. Preserve it rather than delete.
      $null=Backup-StaleProfile -ProfilePath $profileDir -Name $name
    }
    if (-not (Test-Path (Join-Path $profileDir "package.json"))) {
      $null=Invoke-DshProfile -CliArguments @("--profile",$name,"--from-default-profile",$base,"--dump-config")
    }
    # Always replace a previously generated overlay; old patches can mention
    # plugin IDs removed by newer dsh releases (for example tool-ralph).
    Copy-Item -LiteralPath $patch -Destination (Join-Path $profileDir "cordis.patch.yml") -Force
    try {
      $config=Invoke-DshProfile -CliArguments @("--profile",$name,"--dump-config")
    } catch {
      $detail=$_.Exception.Message
      if ($detail -notmatch 'patch: entry .+ not found') { throw }
      # The old profile base itself is incompatible. Keep every file in a backup
      # before recreating; never silently delete sessions or locally saved data.
      $backup=Backup-StaleProfile -ProfilePath $profileDir -Name $name
      try {
        $null=Invoke-DshProfile -CliArguments @("--profile",$name,"--from-default-profile",$base,"--dump-config")
        Copy-Item -LiteralPath $patch -Destination (Join-Path $profileDir "cordis.patch.yml") -Force
        $config=Invoke-DshProfile -CliArguments @("--profile",$name,"--dump-config")
      } catch {
        throw "Could not recreate dsh profile '$name'. Previous profile is preserved at $backup. $($_.Exception.Message)"
      }
    }
    foreach($required in @('deepseek-official','mcp-agent3','agent3-guard')) {
      if ($config -notmatch [regex]::Escape($required)) { throw "DataAgent profile $name missing $required" }
    }
    if ($name -eq 'dataagent') {
      if ($config -notmatch 'agent-preset-registry') { throw "DataAgent web profile missing agent-preset-registry" }
    } else {
      if ($config -notmatch 'DataControl DataAgent') { throw "DataAgent headless profile missing restricted DataControl persona" }
      if ($config -match 'agent-presets') { throw "DataAgent headless profile must not compose the agent-preset roster" }
    }
    if ($config -match '127\.0\.0\.1:8100|deepseek-v3-local|LOCAL_LLM_KEY') {
      throw "Retired local LLM config detected in $name"
    }
  }
} finally { Pop-Location }
Write-Host "DataAgent dsh profiles ready: dataagent + restricted dataagent-headless ($env:DSH_HOME)"
