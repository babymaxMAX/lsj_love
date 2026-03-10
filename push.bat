@echo off
chcp 65001 >nul
cd /d "%~dp0"

git add -A
git commit -m "fix: photos now use presigned URL redirect + frontend always via /photo/index API endpoint"
git push origin main --force
pause
