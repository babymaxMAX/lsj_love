@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Отменяем конфликтный мёрдж...
git merge --abort
echo Сбрасываем к версии GitHub...
git reset --hard origin/main
echo Готово! Теперь повторите push через push.bat
pause
