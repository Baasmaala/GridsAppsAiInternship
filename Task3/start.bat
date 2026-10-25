@echo off
rem double-click: starts the backend and the website, then opens the browser
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File tools\dev.ps1 -Open
pause
