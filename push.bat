@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add -A
git commit -m "fix: VIP advisor expires with subscription, add vip_expired flag, AI Подбор feature"
git push
pause

