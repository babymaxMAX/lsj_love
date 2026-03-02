@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add -A
git commit -m "feat: profile settings page with labeled tabs, edit questions+save, backend update profile/quiz endpoints"
git pull --rebase origin main
git push
pause

