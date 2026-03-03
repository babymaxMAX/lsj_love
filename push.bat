@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add -A
git commit -m "fix: platega return/fail URLs were [REDACTED], now use config.front_end_url"
git push origin main
pause
