@echo off
setlocal
pushd "%~dp0" >nul
if errorlevel 1 (
  echo Cannot enter the DataControl project directory.
  pause
  exit /b 1
)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\dev.ps1" %*
set "result=%errorlevel%"
popd >nul
if not "%result%"=="0" (
  echo.
  echo DataControl did not start. See the error above.
  echo To repair broken npm dependencies: start.bat repair
  pause
)
exit /b %result%
