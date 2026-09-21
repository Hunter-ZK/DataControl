$ErrorActionPreference="Stop"
if(-not(Get-Command python -ErrorAction SilentlyContinue)){throw "Python 3 is required."};if(-not(Get-Command npm -ErrorAction SilentlyContinue)){throw "Node.js 24+ / npm is required."}
if(-not(Test-Path .venv)){python -m venv .venv};.\.venv\Scripts\python.exe -m pip install -U pip;.\.venv\Scripts\python.exe -m pip install -e ".[dev]";.\.venv\Scripts\python.exe -m alembic upgrade head;.\.venv\Scripts\python.exe samples\generate_demo_data.py;.\.venv\Scripts\python.exe samples\enrich_p1_data.py;.\.venv\Scripts\python.exe samples\rebuild_search_index.py
Push-Location web;try{npm install}finally{Pop-Location}
$has314=$false;if(Get-Command py -ErrorAction SilentlyContinue){& py -3.14 -c "import sys; assert sys.version_info[:2] == (3,14)" 2>$null;$has314=$LASTEXITCODE -eq 0}
if($has314){& .\scripts\setup-agent.ps1}else{Write-Warning "Python 3.14 not found; Portal/Web are ready but embedded DataAgent setup was skipped. Install Python 3.14 and run .\scripts\setup-agent.ps1."}
Write-Host "Setup complete. Run .\scripts\start-dev.ps1"
