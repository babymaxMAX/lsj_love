@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add -A
git commit -m "feat: referral notify on registration+purchase with balance and withdraw button"
git push
pause
