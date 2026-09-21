$ErrorActionPreference="Stop"
$root=(Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Push-Location $root
try {
  if(-not(Get-Command npm -ErrorAction SilentlyContinue)){throw "Node.js/npm is required for the embedded DataAgent."}

  $python=Join-Path $root ".venv\Scripts\python.exe"
  if(-not(Test-Path $python)){
    $created=$false
    if(Get-Command python -ErrorAction SilentlyContinue){
      & python -c "import sys; raise SystemExit(0 if (3,13) <= sys.version_info[:2] < (3,15) else 1)" 2>$null
      if($LASTEXITCODE -eq 0){ & python -m venv .venv; $created=$LASTEXITCODE -eq 0 }
    }
    if(-not $created -and (Get-Command py -ErrorAction SilentlyContinue)){
      foreach($version in @("-3.13","-3.14")){
        & py $version -c "import sys; raise SystemExit(0 if (3,13) <= sys.version_info[:2] < (3,15) else 1)" 2>$null
        if($LASTEXITCODE -eq 0){ & py $version -m venv .venv; if($LASTEXITCODE -eq 0){$created=$true;break} }
      }
    }
    if(-not $created){throw "DataControl requires Python 3.13 or 3.14. Install a compatible Python or create .venv first."}
    & $python -m pip install -U pip
    & $python -m pip install -e ".[dev]"
  }

  & $python -c "import sys; raise SystemExit(0 if (3,13) <= sys.version_info[:2] < (3,15) else 1)"
  if($LASTEXITCODE -ne 0){throw "Existing .venv must use Python 3.13 or 3.14."}
  Write-Host ("Embedded DataAgent Python: " + (& $python --version))

  Write-Host "Installing wheel-compatible cryptography runtime..."
  & $python -m pip install --only-binary=:all: "cryptography>=48.0.1,<49"
  if($LASTEXITCODE -ne 0){throw "Compatible cryptography wheel installation failed"}

  & $python -m pip install -e ".\agent[all]"
  if($LASTEXITCODE -ne 0){throw "Agent Python package installation failed"}

  Push-Location agent\dsh
  try{npm install --no-audit --no-fund;if($LASTEXITCODE -ne 0){throw "dsh npm install failed"}}finally{Pop-Location}
  Push-Location agent\guard-plugin
  try{npm install --no-audit --no-fund;npm run build;npm test;if($LASTEXITCODE -ne 0){throw "guard plugin verification failed"}}finally{Pop-Location}

  & .\agent\scripts\setup_dataagent.ps1 -DshHome (Join-Path $root ".local\dsh-home")
  & $python -c "import agent3, dataagent_gateway, cryptography; print('Agent Python imports OK; cryptography=' + cryptography.__version__)"
  if($LASTEXITCODE -ne 0){throw "Agent imports failed after setup"}
  Write-Host "Embedded DataAgent setup complete (shared .venv + local dsh profile)."
} finally { Pop-Location }
