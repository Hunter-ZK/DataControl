$ErrorActionPreference = "Stop"
if (-not (Test-Path .venv\Scripts\python.exe)) { throw "Virtual environment not found. Run .\scripts\setup-dev.ps1 first." }
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) { throw "npm is required. Run .\scripts\setup-dev.ps1 first." }

$backend = Start-Process -FilePath ".\.venv\Scripts\python.exe" -ArgumentList "-m","uvicorn","backend.app.main:app","--reload","--host","127.0.0.1","--port","8000" -WorkingDirectory (Get-Location) -PassThru
Write-Host "DataControl API: http://127.0.0.1:8000"
Write-Host "DataControl Web: http://127.0.0.1:5173"
try {
  Push-Location web
  npm run dev
}
finally {
  Pop-Location
  if ($backend -and -not $backend.HasExited) { Stop-Process -Id $backend.Id -Force }
}
