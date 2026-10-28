[CmdletBinding()]
param([switch]$Repair)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$local = Join-Path $root ".local"
$marker = Join-Path $local "agent-setup-v0.2.1-rc.3.ready"
$dshRoot = Join-Path $root "agent\dsh"
$dshModules = Join-Path $dshRoot "node_modules"
$dshBin = Join-Path $dshModules ".bin\dsh.cmd"
$guardRoot = Join-Path $root "agent\guard-plugin"
$python = Join-Path $root ".venv\Scripts\python.exe"

New-Item -ItemType Directory -Force -Path $local | Out-Null
$setupLock = $null
try {
  $lockPath = Join-Path $local "agent-setup.lock"
  try {
    $setupLock = [System.IO.File]::Open(
      $lockPath, [System.IO.FileMode]::OpenOrCreate,
      [System.IO.FileAccess]::ReadWrite, [System.IO.FileShare]::None
    )
  } catch [System.IO.IOException] {
    throw "Another DataControl Agent setup is running. Close the other setup window before retrying."
  }

  function Assert-Exit([string]$Step) {
    if ($LASTEXITCODE -ne 0) {
      throw "$Step failed (exit code $LASTEXITCODE)."
    }
  }

  function Invoke-NpmInstall([string]$Name, [string]$Directory) {
    & (Join-Path $PSScriptRoot "run-npm-install.ps1") -Name $Name -WorkingDirectory $Directory -LogDirectory $local
  }

  if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) {
    throw "Node.js 24/npm is not available on PATH."
  }
  Push-Location $root
  try {
    if (-not (Test-Path $python)) {
      throw "Missing Python environment. Run .\start.bat setup first."
    }
    & $python -c "import sys; raise SystemExit(0 if (3,13) <= sys.version_info[:2] < (3,15) else 1)"
    Assert-Exit "Python version validation"

    if ($Repair -or -not (Test-Path $marker)) {
      Remove-Item $marker -Force -ErrorAction SilentlyContinue
      if (Test-Path $dshModules) {
        Write-Host "[DataControl] Clearing only incomplete agent\dsh\node_modules..."
        try {
          Remove-Item -LiteralPath $dshModules -Recurse -Force -ErrorAction Stop
        } catch {
          throw "Cannot remove locked npm files. Close npm/Node.js processes using this folder, and retry .\start.bat repair. Details: $($_.Exception.Message)"
        }
      }
    }

    & $python -m pip install --only-binary=:all: "cryptography>=48.0.1,<49"
    Assert-Exit "cryptography setup"
    & $python -m pip install -e ".\agent[all]"
    Assert-Exit "Agent Python setup"

    if (-not (Test-Path $dshBin)) {
      Invoke-NpmInstall "dsh" $dshRoot
    } else {
      Write-Host "[DataControl] Existing dsh installation found."
    }
    if (-not (Test-Path $dshBin)) {
      throw "dsh.cmd is missing after npm installation."
    }

    if ($Repair -or -not (Test-Path (Join-Path $guardRoot "node_modules\.bin\tsc.cmd"))) {
      Invoke-NpmInstall "guard" $guardRoot
    }
    Push-Location $guardRoot
    try {
      & npm.cmd run build
      Assert-Exit "Guard plugin build"
      & npm.cmd test
      Assert-Exit "Guard plugin test"
    } finally { Pop-Location }

    & (Join-Path $root "agent\scripts\setup_dataagent.ps1") -DshHome (Join-Path $local "dsh-home-v0.2.1-rc.3")
    & $python -c "import agent3, dataagent_gateway, cryptography"
    Assert-Exit "Agent Python imports"

    # Create the marker only after all dependencies and both dsh profiles succeed.
    Set-Content -LiteralPath $marker -Value "dsh=0.2.1-rc.3; profile=dataagent-headless" -Encoding UTF8
    Write-Host "[DataControl] Agent setup complete. Subsequent starts reuse installed dependencies."
  } finally {
    Pop-Location
  }
} catch {
  Remove-Item $marker -Force -ErrorAction SilentlyContinue
  throw
} finally {
  if ($setupLock) { $setupLock.Dispose() }
}
