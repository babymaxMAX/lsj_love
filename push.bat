@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add -A
git commit -m "feat: full Russia city proximity map ~250 cities"
git push
pause
