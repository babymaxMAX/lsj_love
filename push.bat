@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add -A
git commit -m "fix: sync girls-write-first between bot and miniapp, no-cache profile fetch"
git push origin main
pause
