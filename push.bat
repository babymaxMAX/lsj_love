@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add -A
git commit -m "fix: button responsiveness, matches reload on visibility, remove 300ms tap delay, fix nav active state"
git push
pause

