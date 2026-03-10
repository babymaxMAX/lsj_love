@echo off
chcp 65001 >nul
cd /d "%~dp0"

git add -A
git commit -m "fix: photo streaming, gender filter swipe+AI, distance sort, like notify with photo+VIP"
git push origin main --force
pause
