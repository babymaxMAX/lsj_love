@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add -A
git commit -m "feat: privacy policy, terms of service (14+), fix profile toggle keyboard"
git push origin main
pause
