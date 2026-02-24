@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add -A
git commit -m "fix: resolve circular import in notificator - lazy bot imports"
git push
pause
