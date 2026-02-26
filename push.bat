@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add -A
git commit -m "fix: AI matchmaking - public URL photo fallback, text fallback for visual criteria, smarter prompt"
git push
pause

