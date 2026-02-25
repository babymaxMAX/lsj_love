@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add -A
git commit -m "fix: matches page refetch on back navigation, fix avatar photo errors, fix online dot indicator"
git push
pause

