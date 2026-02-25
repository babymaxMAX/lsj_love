@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add -A
git commit -m "fix: bot photo upload now updates photos[0] S3 key so Mini App shows new photo"
git push
pause

