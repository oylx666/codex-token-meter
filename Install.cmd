@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Enable-Autostart.ps1"
if errorlevel 1 (echo Installation failed. See the error above.) else (echo Installed. Open Codex normally to show Token Meter.)
pause
