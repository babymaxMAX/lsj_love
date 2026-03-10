@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add -A
git commit -m "rebrand: rename LSJLove to Kupidon AI + rewrite privacy policy and terms of service"
git push origin main
pause
