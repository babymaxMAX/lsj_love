@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add -A
git commit -m "feat: photo tap nav, geo proximity, hide profile, match check, photo likes notifications"
git push
pause
