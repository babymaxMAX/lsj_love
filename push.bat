@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add -A
git commit -m "feat: multi-photo profiles, photo likes/comments, view-profile page, slider in swipe card"
git push
pause
