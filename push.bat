@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add -A
git commit -m "fix: toggle girls-write-first hang - single callback.answer, update keyboard only"
git push origin main
pause
