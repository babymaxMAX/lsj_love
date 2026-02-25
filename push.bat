@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add -A
git commit -m "feat: NSFW photo moderation via GPT-4o-mini in bot, Mini App (base64 + multipart)"
git push
pause
