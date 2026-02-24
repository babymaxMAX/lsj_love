@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add -A
git commit -m "fix: video upload via multipart FormData, nginx 80m limit for photos endpoint"
git push
pause
