[CmdletBinding()]
param([switch]$SkipAgent)

$ErrorActionPreference="Stop"
$root=(Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $root
if(-not(Get-Command npm -ErrorAction SilentlyContinue)){throw "Node.js 24+ / npm is required."}

$python=Join-Path $root ".venv\Scripts\python.exe"
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
if($LASTEXITCODE -ne 0){throw "pip upgrade failed"}
& $python -m pip install -e ".[dev]"
if($LASTEXITCODE -ne 0){throw "Portal Python dependencies failed"}
& $python -m alembic upgrade head
if($LASTEXITCODE -ne 0){throw "Alembic migration failed"}
& $python samples\generate_demo_data.py
if($LASTEXITCODE -ne 0){throw "generate_demo_data failed"}
& $python samples\enrich_p1_data.py
if($LASTEXITCODE -ne 0){throw "enrich_p1_data failed"}
& $python samples\enrich_p3_reference.py
if($LASTEXITCODE -ne 0){throw "enrich_p3_reference failed"}
& $python samples\enrich_p2_realistic_corpus.py
if($LASTEXITCODE -ne 0){throw "enrich_p2_realistic_corpus failed"}
& $python samples\enrich_next_p1_lineage.py
if($LASTEXITCODE -ne 0){throw "enrich_next_p1_lineage failed"}
& $python samples\enrich_next_p2_semantics.py
if($LASTEXITCODE -ne 0){throw "enrich_next_p2_semantics failed"}
& $python samples\rebuild_search_index.py
if($LASTEXITCODE -ne 0){throw "rebuild_search_index failed"}
& $python samples\generate_p2_question_bank.py
if($LASTEXITCODE -ne 0){throw "generate_p2_question_bank failed"}
& $python samples\generate_p3_question_bank.py
if($LASTEXITCODE -ne 0){throw "generate_p3_question_bank failed"}
& $python samples\validate_p2_corpus_quality.py
if($LASTEXITCODE -ne 0){throw "validate_p2_corpus_quality failed"}

Push-Location web
try{
  & npm.cmd install --no-audit --no-fund --no-progress
  if($LASTEXITCODE -ne 0){throw "Frontend npm install failed"}
}finally{Pop-Location}

New-Item -ItemType Directory -Force -Path ".local" | Out-Null
Set-Content -Path ".local\portal-setup-ready.txt" -Value "Portal + sample data + frontend ready" -Encoding UTF8
if(-not $SkipAgent){ & .\scripts\setup-agent.ps1 }
Write-Host ("Setup complete. Python: " + (& $python --version))
Write-Host "P2 realistic corpus: READY"
Write-Host "P2 question bank: .local\p2-question-bank.json"
Write-Host "P2 corpus quality gate: PASSED"
Write-Host "P3 compatibility question bank: .local\p3-question-bank.json"
Write-Host "Run .\start.bat"
