@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add -A
git commit -m "feat: add privacy policy and terms of service pages + fix profile toggle"
git push origin main
pause
