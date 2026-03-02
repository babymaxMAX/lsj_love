@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add -A
git commit -m "fix: gendered notification texts + safe swipe fallback chain"
git push origin main
pause
