@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add -A
git commit -m "fix: settings content padding so Imya label is visible below sticky header"
git push origin main
pause
