@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add -A
git commit -m "fix: AI Подбор button always visible, dark header bg, button in empty state screen"
git push
pause

