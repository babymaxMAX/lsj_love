#!/bin/bash
# ============================================================
# Скрипт первичной настройки сервера Ubuntu 22.04 для LSJLove
# Запускать: bash setup-server.sh
# ============================================================

set -e

DOMAIN="lsjlove.duckdns.org"
PROJECT_DIR="/opt/lsjlove"
EMAIL="your@email.com"  # Замени на свой email для SSL

echo "🚀 Настройка сервера для $DOMAIN..."

# 1. Обновление системы
apt-get update -y && apt-get upgrade -y

# 2. Установка Docker
if ! command -v docker &> /dev/null; then
    echo "📦 Устанавливаю Docker..."
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
fi

# 3. Установка Docker Compose
if ! command -v docker compose &> /dev/null; then
    apt-get install -y docker-compose-plugin
fi

# 4. Установка Git
apt-get install -y git curl

# 5. Создание директории проекта
mkdir -p $PROJECT_DIR
cd $PROJECT_DIR

echo ""
echo "✅ Docker и зависимости установлены!"
echo ""
echo "📋 СЛЕДУЮЩИЕ ШАГИ:"
echo ""
echo "1. Загрузи проект на сервер:"
echo "   git clone https://github.com/ТВОЙ_USERNAME/lsjlove.git $PROJECT_DIR"
echo ""
echo "2. Создай .env файл:"
echo "   cp $PROJECT_DIR/.env.example $PROJECT_DIR/.env"
echo "   nano $PROJECT_DIR/.env"
echo "   (Заполни все переменные: BOT_TOKEN, MongoDB, S3, OpenAI)"
echo ""
echo "3. Получи SSL сертификат (сначала временный nginx без SSL):"
echo "   cd $PROJECT_DIR"
echo "   # Запусти nginx только на 80 порту:"
echo "   docker run -d --name temp-nginx -p 80:80 -v \$(pwd)/nginx/certbot:/var/www/certbot nginx"
echo "   docker run --rm -v \$(pwd)/nginx/certs:/etc/letsencrypt -v \$(pwd)/nginx/certbot:/var/www/certbot certbot/certbot certonly --webroot -w /var/www/certbot -d $DOMAIN --email $EMAIL --agree-tos --non-interactive"
echo "   docker stop temp-nginx && docker rm temp-nginx"
echo ""
echo "4. Запусти проект:"
echo "   cd $PROJECT_DIR"
echo "   docker compose up -d"
echo ""
echo "5. Проверь что всё работает:"
echo "   docker compose ps"
echo "   curl https://$DOMAIN/api/docs"
echo ""
echo "🎉 Готово! Сайт будет доступен на https://$DOMAIN"
