@echo off
setlocal
title Tarkash Video Studio - Setup
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0installer\install.ps1"
if errorlevel 1 (
  echo.
  echo Setup did not finish. See the message above and the logs folder.
  pause
  exit /b 1
)
exit /b 0
