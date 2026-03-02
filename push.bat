@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add -A
git commit -m "fix: swipe shows no profiles - safe age parsing + correct fallback chain"
git push origin main
pause
