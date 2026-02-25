@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add -A
git commit -m "fix: keep FSM state after NSFW rejection so user can retry photo upload"
git push
pause

