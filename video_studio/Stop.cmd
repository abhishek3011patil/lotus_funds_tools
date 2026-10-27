@echo off
setlocal
title Tarkash Video Studio - Stop
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0installer\stop.ps1"
if errorlevel 1 (
  echo.
  pause
  exit /b 1
)
exit /b 0
