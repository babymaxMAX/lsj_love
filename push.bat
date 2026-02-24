@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add -A
git commit -m "feat: full premium audit - timer, photo-bot, superlike, likes-limit, boost, VIP sort, matches nav"
git push
pause
