@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add -A
git commit -m "feat: full admin panel with stats/broadcast/search/ban, admin button in /start"
git push origin main
pause
