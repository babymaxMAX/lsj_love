@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add -A
git commit -m "fix: compact settings header, brighter labels, content starts higher"
git push origin main
pause
