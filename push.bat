@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add -A
git commit -m "feat: AI Подбор - matchmaking chat with vision analysis of photos, like/skip cards"
git push
pause

