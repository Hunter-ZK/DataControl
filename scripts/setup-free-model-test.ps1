[CmdletBinding()]
param()
$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$agentRoot = Join-Path $repoRoot "agent"
$localDir = Join-Path $repoRoot ".local"
$dshHomePath = Join-Path $localDir "dsh-home-v0.2.1-rc.3"
$profileName = "dataagent-headless-free"
$profileDir = Join-Path $dshHomePath ("profiles\" + $profileName)
$sourceDir = Join-Path $localDir "dsh-our-free-model-v2.7.2"
$pinnedCommit = "e1b347aec9cc956eda70a766219f028a811078e2"
$marker = Join-Path $localDir "free-model-test-v2.7.2.ready"
$pythonExe = Join-Path $repoRoot ".venv\Scripts\python.exe"
$dshExe = Join-Path $agentRoot "dsh\node_modules\.bin\dsh.cmd"
$cliHelper = Join-Path $agentRoot "scripts\dsh_profile_cli.py"
$outLog = Join-Path $localDir "free-model-setup.stdout.log"
$errLog = Join-Path $localDir "free-model-setup.stderr.log"
if (-not (Test-Path $pythonExe) -or -not (Test-Path $dshExe)) {
  throw "First install the standard Agent: .\start.bat repair"
}
if (-not (Get-Command git.exe -ErrorAction SilentlyContinue)) { throw "git.exe is required" }
New-Item -ItemType Directory -Force -Path $localDir | Out-Null
$env:DSH_HOME = $dshHomePath
$env:DSH_TELEMETRY_MODE = "DISABLED"
Remove-Item $marker -ErrorAction SilentlyContinue
function Invoke-Dsh([string[]]$ArgsForDsh) {
  & $pythonExe $cliHelper --executable $dshExe --cwd $repoRoot --stdout $outLog --stderr $errLog --timeout 600 -- @ArgsForDsh
  if ($LASTEXITCODE -ne 0) {
    $detail = if (Test-Path $errLog) { Get-Content $errLog -Raw -Encoding UTF8 } else { "unknown" }
    throw "Free-test dsh setup failed: $detail"
  }
  if (Test-Path $outLog) { return Get-Content $outLog -Raw -Encoding UTF8 }
  return ""
}
if (-not (Test-Path $sourceDir)) {
  Write-Host "[free-test] Cloning reviewed v2.7.2 release from GitHub into .local..."
  & git.exe clone -q --depth 1 --branch v2.7.2 https://github.com/Ebony-Vinyl/dsh-our-free-model.git $sourceDir
  if ($LASTEXITCODE -ne 0) { throw "Could not clone the free model source" }
}
$actualCommit = (& git.exe -C $sourceDir rev-parse HEAD).Trim()
if ($actualCommit -ne $pinnedCommit) {
  throw "Plugin revision does not match pinned release commit; setup aborted"
}
$sourcePackage = Get-Content (Join-Path $sourceDir "package.json") -Raw -Encoding UTF8 | ConvertFrom-Json
if ($sourcePackage.name -ne "dsh-our-free-model" -or $sourcePackage.version -ne "2.7.2") {
  throw "Plugin version mismatch"
}
if (-not (Test-Path (Join-Path $profileDir "package.json"))) {
  $null = Invoke-Dsh -ArgsForDsh @("--profile",$profileName,"--from-default-profile","headless","--dump-config")
}
$sourcePatch = Join-Path $agentRoot "dsh\profile\headless.patch.yml"
$patch = [System.IO.File]::ReadAllText($sourcePatch,[System.Text.Encoding]::UTF8)
$newline = if ($patch.Contains("`r`n")) { "`r`n" } else { "`n" }
$needle = "provider: deepseek-official" + $newline + "    model: deepseek-flash"
if (-not $patch.Contains($needle)) { throw "Read-only headless model declaration changed; review before installing" }
$patch = $patch.Replace($needle, ("provider: our-free-model" + $newline + "    model: kilo-auto/free"))
[System.IO.File]::WriteAllText((Join-Path $profileDir "cordis.patch.yml"),$patch,[System.Text.UTF8Encoding]::new($false))
# Upstream README: install local source; never install the unrelated npm package.
$installed = Join-Path $profileDir "node_modules\dsh-our-free-model\package.json"
if (-not (Test-Path $installed)) {
  $null = Invoke-Dsh -ArgsForDsh @("plugin","--profile",$profileName,"add",$sourceDir)
} else {
  Write-Host "[free-test] Reusing already installed pinned plugin."
}
$config = Invoke-Dsh -ArgsForDsh @("--profile",$profileName,"--dump-config")
foreach ($required in @("our-free-model","kilo-auto/free","mcp-agent3","agent3-guard")) {
  if ($config -notmatch [regex]::Escape($required)) { throw "Test profile missing: $required" }
}
$installed = Join-Path $profileDir "node_modules\dsh-our-free-model\package.json"
if (-not (Test-Path $installed)) { throw "Free plugin not found in optional profile" }
$installedPackage = Get-Content $installed -Raw -Encoding UTF8 | ConvertFrom-Json
if ($installedPackage.version -ne "2.7.2") { throw "Installed free plugin version mismatch" }
Set-Content -LiteralPath $marker -Value "v2.7.2; commit=$pinnedCommit" -Encoding UTF8
Write-Host "[free-test] Installed. Launch: .\scripts\start-free-test.ps1"
