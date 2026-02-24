@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add -A
git commit -m "fix: add openai httpx deps, improve advisor error handling"
git push
pause
