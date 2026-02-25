@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add -A
git commit -m "fix: online status timezone bug - Motor returns naive datetime, ensure UTC ISO format for JS"
git push
pause

