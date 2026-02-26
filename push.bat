@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add -A
git commit -m "fix: nginx rate limit, view-profile error handling with retry, matches popstate refetch"
git push
pause

