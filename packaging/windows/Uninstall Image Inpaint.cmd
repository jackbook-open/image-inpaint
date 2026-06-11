@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0uninstall-user.ps1"
if errorlevel 1 (
  echo.
  echo Uninstall failed. See the message above for details.
  pause
  exit /b 1
)
echo.
echo Uninstall complete.
pause
