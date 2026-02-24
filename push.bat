@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add -A
git commit -m "fix: handle short Telegram names (1 char) in from_telegram_user with fallback"
git push
pause
