@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add -A
git commit -m "fix: settings tabs inside sticky header so they are always visible"
git push origin main
pause
