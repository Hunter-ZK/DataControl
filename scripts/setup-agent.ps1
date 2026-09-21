$ErrorActionPreference="Stop";$root=(Resolve-Path (Join-Path $PSScriptRoot "..")).Path;Push-Location $root
try {
  if (-not (Get-Command py -ErrorAction SilentlyContinue)) { throw "Python launcher 'py' is required to select Python 3.14 for the embedded DataAgent." }
  & py -3.14 -c "import sys; assert sys.version_info[:2] == (3,14)"; if($LASTEXITCODE -ne 0){throw "Python 3.14 is required for the embedded DataAgent."}
  if(-not(Get-Command npm -ErrorAction SilentlyContinue)){throw "Node.js/npm is required for the embedded DataAgent."}
  if(-not(Test-Path .venv-agent)){& py -3.14 -m venv .venv-agent;if($LASTEXITCODE -ne 0){throw "Failed to create .venv-agent"}}
  .\.venv-agent\Scripts\python.exe -m pip install -U pip
  .\.venv-agent\Scripts\python.exe -m pip install -e ".\agent[all,dev]"
  Push-Location agent\dsh;try{npm install --no-audit --no-fund;if($LASTEXITCODE -ne 0){throw "dsh npm install failed"}}finally{Pop-Location}
  Push-Location agent\guard-plugin;try{npm install --no-audit --no-fund;npm run build;npm test;if($LASTEXITCODE -ne 0){throw "guard plugin verification failed"}}finally{Pop-Location}
  & .\agent\scripts\setup_dataagent.ps1 -DshHome (Join-Path $root ".local\dsh-home")
  Write-Host "Embedded DataAgent setup complete (.venv-agent + local dsh profile)."
} finally { Pop-Location }
