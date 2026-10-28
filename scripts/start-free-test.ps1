[CmdletBinding()]
param()
$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if (-not (Test-Path -LiteralPath (Join-Path $repoRoot ".local\free-model-test-v2.7.2.ready"))) {
  throw "Optional free-test profile not installed: run .\scripts\setup-free-model-test.ps1"
}
$previousMode = [Environment]::GetEnvironmentVariable("DATACONTROL_AGENT_MODEL_MODE", "Process")
$previousConsent = [Environment]::GetEnvironmentVariable("DATACONTROL_FREE_TEST_ACCEPT_PUBLIC_GATEWAY", "Process")
try {
  $env:DATACONTROL_AGENT_MODEL_MODE = "free-test"
  $env:DATACONTROL_FREE_TEST_ACCEPT_PUBLIC_GATEWAY = "1"
  Write-Warning "PUBLIC FREE TEST: use synthetic questions and metadata only; never company data."
  & (Join-Path $PSScriptRoot "start-dev.ps1")
} finally {
  [Environment]::SetEnvironmentVariable("DATACONTROL_AGENT_MODEL_MODE", $previousMode, "Process")
  [Environment]::SetEnvironmentVariable("DATACONTROL_FREE_TEST_ACCEPT_PUBLIC_GATEWAY", $previousConsent, "Process")
}
