@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add -A
git commit -m "feat: daily grants Premium/VIP, superlike display, fix PRO->Premium badge, admin give credits, AI matchmaking exclude liked, girls-write-first in profile+bot"
git push origin main
pause
