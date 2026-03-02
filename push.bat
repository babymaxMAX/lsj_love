@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add -A
git commit -m "feat: girls see likers free, girls-write-first toggle for men, admin panel, AI matchmaking hides IDs"
git push origin main
pause
