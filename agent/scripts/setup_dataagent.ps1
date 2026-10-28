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
if (-not (Test-Path $dshBin)) { throw "DeepSeek Harness is not installed. Run .\scripts\setup-agent.ps1 first." }
if (-not (Test-Path $pnpmBin)) { throw "Pinned pnpm is missing from agent\dsh. Run .\scripts\setup-agent.ps1 again." }
$env:PATH="$dshBinDir;$env:PATH"
New-Item -ItemType Directory -Force -Path $env:DSH_HOME | Out-Null

$profiles=@(
  @{ Name="dataagent"; Base="web"; Patch=$webPatch },
  @{ Name="dataagent-headless"; Base="headless"; Patch=$headlessPatch }
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

Push-Location $repoRoot
try {
  foreach($entry in $profiles) {
    $name=$entry.Name
    $base=$entry.Base
    $patch=$entry.Patch
    $profile=Join-Path $env:DSH_HOME ("profiles\"+$name)
    if ((Test-Path $profile) -and -not (Test-Path (Join-Path $profile "package.json"))) {
      Remove-Item -Recurse -Force $profile
    }
    if (-not (Test-Path (Join-Path $profile "package.json"))) {
      $null=Invoke-DshProfile -CliArguments @("--profile",$name,"--from-default-profile",$base,"--dump-config")
    }
    $pkg=Get-Content (Join-Path $profile "package.json") -Raw
    if ($pkg -notmatch '@hunter-zk/agent3-guard') {
      $null=Invoke-DshProfile -CliArguments @("plugin","--profile",$name,"add",$guardDir)
    }
    Copy-Item $patch (Join-Path $profile "cordis.patch.yml") -Force
    $config=Invoke-DshProfile -CliArguments @("--profile",$name,"--dump-config")
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
