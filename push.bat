@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add -A
git commit -m "fix: wider age range +-15, no-age fallback, AI matchmaking 30s timeout + offline fallback"
git push origin main
pause
