$ErrorActionPreference = "Stop"
if (-not (Test-Path .venv)) { python -m venv .venv }
.\.venv\Scripts\python.exe -m pip install -U pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe samples\generate_demo_data.py
.\.venv\Scripts\python.exe samples\enrich_p1_data.py
Write-Host "Setup complete. Run .\scripts\start-dev.ps1"
