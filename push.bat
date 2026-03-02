@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add -A
git commit -m "fix: settings tabs visible, edit answers, remove photo button, PATCH profile endpoint"
git push origin main
pause
