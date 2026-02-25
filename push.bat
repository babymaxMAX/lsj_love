@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add -A
git commit -m "fix: clear photo likes when photo is replaced or deleted"
git push
pause

