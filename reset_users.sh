#!/bin/bash
# LSJLove — Полный сброс всех пользователей (для тестов)
# Запуск: bash reset_users.sh

API_URL="https://lsjlove.duckdns.org/api/v1/users/admin/reset-all?secret=lsjlove_reset_2026"

echo "Очищаем базу данных..."
RESPONSE=$(curl -s -X DELETE "$API_URL")
echo "$RESPONSE"
echo "Готово!"
