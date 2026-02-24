@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add -A
git commit -m "fix: photo likes notif, remove comments, profile reappear logic, full audit"
git push
pause
