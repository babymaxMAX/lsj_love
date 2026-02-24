@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add -A
git commit -m "fix: profile_hidden field, dislikes tracking, photo navigation UI, comment dedup"
git push
pause
