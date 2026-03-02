@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add -A
git commit -m "feat: unlimited likes for girls, girl welcome msg on register, free privileges block on premium page"
git push origin main
pause
