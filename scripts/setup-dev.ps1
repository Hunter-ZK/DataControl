$ErrorActionPreference = "Stop"
if (-not (Get-Command python -ErrorAction SilentlyContinue)) { throw "Python 3 is required." }
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) { throw "Node.js 24+ / npm is required." }
if (-not (Test-Path .venv)) { python -m venv .venv }
.\.venv\Scripts\python.exe -m pip install -U pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe samples\generate_demo_data.py
.\.venv\Scripts\python.exe samples\enrich_p1_data.py
Push-Location web
try { npm install } finally { Pop-Location }
Write-Host "Setup complete. Run .\scripts\start-dev.ps1"
