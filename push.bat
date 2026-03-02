@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add -A
git commit -m "fix: AI builder shows saved text in reply, strips all quote types from about"
git push origin main
pause
