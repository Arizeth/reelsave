@echo off
setlocal
cd /d "%~dp0"
py -3.12 run_windows.py
if errorlevel 1 (
  echo.
  echo Startup failed. See the message above.
  pause
)
endlocal
