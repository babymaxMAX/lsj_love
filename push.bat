@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add -A
git commit -m "fix: short Telegram name crash; feat: referral 50%, improve referral notify"
git push
pause
