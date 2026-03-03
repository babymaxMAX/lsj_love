@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add -A
git commit -m "fix: payment activation timezone bug + bot notifications after Platega payment"
git push origin main
pause
