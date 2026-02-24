@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add -A
git commit -m "feat: referral withdraw button via @babymaxx in bot and Mini App"
git push
pause
