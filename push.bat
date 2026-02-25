@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add -A
git commit -m "feat: online/offline status in swipe cards, matches, view-profile; fix back button on profile error screen"
git push
pause

