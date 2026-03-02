@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add -A
git commit -m "fix: toggle girls-write-first - pass all required args to profile_inline_kb"
git push origin main
pause
