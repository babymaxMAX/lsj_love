@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add -A
git commit -m "fix: girls-write-first toggle NameError + remove redundant gender check"
git push origin main
pause
