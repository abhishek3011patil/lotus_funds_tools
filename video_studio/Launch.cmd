@echo off
setlocal
title Tarkash Video Studio
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0installer\launch.ps1" -NoDialog
if errorlevel 1 (
  echo.
  echo Video Studio could not start. Please check the logs folder.
  pause
  exit /b 1
)
exit /b 0
