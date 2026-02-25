@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add -A
git commit -m "fix: compact matches page layout to fit multiple cards on screen"
git push
pause

