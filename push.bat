@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add -A
git commit -m "fix: girls-write-first toggle gender check (add Man/man), remove AI matchmaking from girls free perks"
git push origin main
pause
