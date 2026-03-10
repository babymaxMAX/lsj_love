@echo off
chcp 65001 >nul
cd /d "%~dp0"

:: Если голова отсоединена — переключаемся на main
git symbolic-ref HEAD >nul 2>&1 || git checkout main

:: Подтягиваем удалённые изменения (rebase чтобы не было лишних merge-коммитов)
git pull origin main --rebase

:: Добавляем и коммитим
git add -A
<<<<<<< Updated upstream
git commit -m "feat: profile settings page with labeled tabs, edit questions+save, backend update profile/quiz endpoints"
git pull --rebase origin main
git push
=======
git commit -m "fix: resolve git conflicts, stream S3 photos directly, gender filter in swipe+AI, like notification with photo"

:: Пушим
git push origin main
>>>>>>> Stashed changes
pause

