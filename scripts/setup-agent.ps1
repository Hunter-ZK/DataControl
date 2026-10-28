[CmdletBinding()]
param([switch]$Repair)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$local = Join-Path $root ".local"
$marker = Join-Path $local "agent-setup-v0.2.1-rc.3-profile2.ready"
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

    # A failed profile bootstrap must never trigger a full npm reinstall.
    # Only a missing or wrong-version dsh dependency requires clearing its tree.
    $installedPackage = Join-Path $dshModules "@deepseek-ai\\dsh\\package.json"
    $installedVersion = ""
    if (Test-Path $installedPackage) {
      try { $installedVersion = (Get-Content $installedPackage -Raw -Encoding UTF8 | ConvertFrom-Json).version } catch {}
    }
    $requiresReinstall = (-not (Test-Path $dshBin)) -or ($installedVersion -ne "0.2.1-rc.3")
    if ($requiresReinstall -and (Test-Path $dshModules)) {
      Write-Host "[DataControl] Damaged/mismatched dsh package; rebuilding only node_modules..."
      try {
        Remove-Item -LiteralPath $dshModules -Recurse -Force -ErrorAction Stop
      } catch {
        throw "Cannot remove locked npm files. Close other Node/npm processes and retry. Details: $($_.Exception.Message)"
      }
    }
    if (-not $requiresReinstall) {
      Write-Host "[DataControl] dsh 0.2.1-rc.3 installed; refreshing profile without npm reinstall."
    }

    & $python -c "import importlib.util as u; import importlib.metadata as m; a=all(u.find_spec(n) for n in ('agent3','dataagent_gateway','cryptography')); b=m.version('cryptography').startswith('48.') if a else False; raise SystemExit(0 if a and b else 1)"
    if ($LASTEXITCODE -ne 0) {
      & $python -m pip install --only-binary=:all: "cryptography>=48.0.1,<49"
      Assert-Exit "cryptography setup"
      & $python -m pip install -e ".\agent[all]"
      Assert-Exit "Agent Python setup"
    } else {
      Write-Host "[DataControl] Existing Agent Python dependencies found; skipping pip."
    }

    if (-not (Test-Path $dshBin)) {
      Invoke-NpmInstall "dsh" $dshRoot
    } else {
      Write-Host "[DataControl] Existing dsh installation found."
    }
    if (-not (Test-Path $dshBin)) {
      throw "dsh.cmd is missing after npm installation."
    }

    if (-not (Test-Path (Join-Path $guardRoot "node_modules\.bin\tsc.cmd"))) {
      Invoke-NpmInstall "guard" $guardRoot
    }
    Push-Location $guardRoot
    try {
      & npm.cmd run build
      Assert-Exit "Guard plugin build"
    } finally { Pop-Location }

    & (Join-Path $root "agent\scripts\setup_dataagent.ps1") -DshHome (Join-Path $local "dsh-home-v0.2.1-rc.3")
    & $python -c "import agent3, dataagent_gateway, cryptography"
    Assert-Exit "Agent Python imports"

    # Create the marker only after all dependencies and both dsh profiles succeed.
    Set-Content -LiteralPath $marker -Value "dsh=0.2.1-rc.3; profile=dataagent-headless" -Encoding UTF8
    try {
      & (Join-Path $root "scripts\setup-free-model-test.ps1")
      if ($LASTEXITCODE -ne 0) { Write-Warning "Optional free model setup returned exit code $LASTEXITCODE" }
    } catch {
      Write-Warning "Optional public model could not be installed: $($_.Exception.Message). Official DeepSeek remains available."
    }
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
