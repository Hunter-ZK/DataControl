$ErrorActionPreference="Stop"
if(-not(Get-Command npm -ErrorAction SilentlyContinue)){throw "Node.js 24+ / npm is required."}

$python=".\.venv\Scripts\python.exe"
if(-not(Test-Path $python)){
  $created=$false
  if(Get-Command python -ErrorAction SilentlyContinue){
    & python -c "import sys; raise SystemExit(0 if (3,13) <= sys.version_info[:2] < (3,15) else 1)" 2>$null
    if($LASTEXITCODE -eq 0){& python -m venv .venv;$created=$LASTEXITCODE -eq 0}
  }
  if(-not $created -and (Get-Command py -ErrorAction SilentlyContinue)){
    foreach($version in @("-3.13","-3.14")){
      & py $version -c "import sys; raise SystemExit(0 if (3,13) <= sys.version_info[:2] < (3,15) else 1)" 2>$null
      if($LASTEXITCODE -eq 0){& py $version -m venv .venv;if($LASTEXITCODE -eq 0){$created=$true;break}}
    }
  }
  if(-not $created){throw "DataControl requires Python 3.13 or 3.14."}
}

& $python -c "import sys; raise SystemExit(0 if (3,13) <= sys.version_info[:2] < (3,15) else 1)"
if($LASTEXITCODE -ne 0){throw "Existing .venv must use Python 3.13 or 3.14."}
& $python -m pip install -U pip
& $python -m pip install -e ".[dev]"
& $python -m alembic upgrade head
& $python samples\generate_demo_data.py
& $python samples\enrich_p1_data.py
& $python samples\enrich_p3_reference.py
& $python samples\enrich_next_p1_lineage.py
& $python samples\enrich_next_p2_semantics.py
& $python samples\rebuild_search_index.py
& $python samples\generate_p3_question_bank.py

Push-Location web
try{npm install}finally{Pop-Location}

& .\scripts\setup-agent.ps1
Write-Host ("Setup complete. Python: " + (& $python --version))
Write-Host "P3 question bank: .local\p3-question-bank.json"
Write-Host "Next-P2 semantic fixtures: READY"
Write-Host "Run .\scripts\start-dev.ps1"
