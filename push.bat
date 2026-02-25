@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add -A
git commit -m "fix: cache-bust photo URLs after replace/delete so browser shows fresh image"
git push
pause

