@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add -A
git commit -m "fix: registration handler crash - container not defined for girl welcome msg"
git push origin main
pause
