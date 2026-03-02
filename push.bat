@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add -A
git commit -m "feat: settings page edit answers, remove photo button, backend PATCH profile endpoint"
git push origin main
pause
