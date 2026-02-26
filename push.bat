@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add -A
git commit -m "feat: AI Подбор btn top-left, VIP advisor access tied to subscription period"
git push
pause

