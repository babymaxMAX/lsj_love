@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add -A
git commit -m "fix: icebreaker/superlike atomic inc, stars subscription renewal, profile_hidden"
git push
pause
