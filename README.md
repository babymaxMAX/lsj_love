# LSJLove — Telegram Dating Mini App

Приложение для знакомств внутри Telegram на домене **lsjlove.duckdns.org**

## Стек
- **Бот**: aiogram 3 + Telegram Stars оплата
- **Бэкенд**: FastAPI + MongoDB
- **Фронтенд**: Next.js (Telegram Mini App / TWA)
- **AI**: OpenAI GPT-4o-mini (Icebreaker, анализ профиля)
- **Деплой**: Docker Compose + Nginx + Let's Encrypt SSL

---

## Запуск на сервере (шаг за шагом)

### 1. Создай Telegram бота

1. Открой [@BotFather](https://t.me/BotFather) в Telegram
2. Отправь `/newbot`
3. Придумай имя: `LSJLove Bot`
4. Придумай username: `lsjlove_bot` (должен заканчиваться на `bot`)
5. Скопируй токен (вид: `1234567890:ABCdef...`)

### 2. Настрой Mini App у бота

1. В BotFather отправь `/mybots` → выбери бота
2. `Bot Settings` → `Menu Button` → `Configure menu button`
3. Введи URL: `https://lsjlove.duckdns.org/users/TELEGRAM_ID`
4. Введи название: `💕 Открыть LSJLove`

### 3. Подготовь сервер

```bash
# Подключись к серверу по SSH
ssh user@YOUR_SERVER_IP

# Установи Docker (если нет)
curl -fsSL https://get.docker.com | sh

# Клонируй проект
git clone https://github.com/ТВОЙ_USERNAME/lsjlove.git /opt/lsjlove
cd /opt/lsjlove
```

### 4. Создай .env файл

```bash
cp .env.example .env
nano .env
```

Заполни:
```env
BOT_TOKEN=твой_токен_от_botfather
WEBHOOK_URL=https://lsjlove.duckdns.org
FRONT_END_URL=https://lsjlove.duckdns.org
MONGO_DB_CONNECTION_URI=mongodb://mongodb:27017
MONGO_DB_ADMIN_USERNAME=admin
MONGO_DB_ADMIN_PASSWORD=придумай_пароль
AWS_ACCESS_KEY_ID=твой_s3_ключ
AWS_SECRET_ACCESS_KEY=твой_s3_секрет
S3_BUCKET_NAME=lsjlove-media
OPENAI_API_KEY=твой_openai_ключ  # необязательно
```

### 5. Получи SSL сертификат

DuckDNS поддерживает Let's Encrypt. Сначала запусти nginx только на HTTP:

```bash
# Временный nginx для получения сертификата
docker run -d --name temp-nginx -p 80:80 \
  -v $(pwd)/nginx/certbot:/var/www/certbot nginx

# Получи сертификат
docker run --rm \
  -v $(pwd)/certbot_certs:/etc/letsencrypt \
  -v $(pwd)/certbot_data:/var/www/certbot \
  certbot/certbot certonly \
  --webroot -w /var/www/certbot \
  -d lsjlove.duckdns.org \
  --email your@email.com \
  --agree-tos --non-interactive

# Останови временный nginx
docker stop temp-nginx && docker rm temp-nginx
```

### 6. Запусти проект

```bash
docker compose up -d
```

### 7. Проверь

```bash
# Статус контейнеров
docker compose ps

# Логи
docker compose logs -f api

# Проверь API
curl https://lsjlove.duckdns.org/api/docs
```

---

## Перезапуск бота (после git pull)

Бот работает через webhook внутри API. Чтобы применить изменения после `git pull`:

```bash
cd /opt/lsjlove   # или путь к проекту
docker compose up -d --build api
```

Или полный перезапуск всего стека:

```bash
docker compose down
docker compose up -d --build
```

Локальная разработка (без Docker):

```bash
cd temp_project
poetry install
poetry run uvicorn --factory app.application.api.main:create_app --reload --host 0.0.0.0 --port 8000
```

---

## Настройка автодеплоя (GitHub Actions)

1. Залей проект на GitHub (создай репозиторий)
2. В настройках репозитория → Secrets → добавь:
   - `SERVER_HOST` = IP твоего сервера
   - `SERVER_USER` = имя пользователя (обычно `root` или `ubuntu`)
   - `SERVER_SSH_KEY` = содержимое файла `~/.ssh/id_rsa` (приватный ключ)
3. После каждого `git push main` деплой произойдёт автоматически

---

## Функции приложения

| Функция | Описание |
|---|---|
| Свайпы | Карточки с анимацией, свайп влево/вправо |
| AI Icebreaker | Генерация первого сообщения через OpenAI |
| Telegram Stars | Оплата Premium/VIP прямо в боте |
| Вопрос дня | Ежедневный вопрос для сравнения совместимости |
| Рейтинг | Топ популярных профилей |
| Premium | 500 Stars/мес — безлимитные лайки |
| VIP | 1500 Stars/мес — все функции |

## Команды бота

| Команда | Что делает |
|---|---|
| `/start` | Приветствие и регистрация |
| `/form` | Заполнение анкеты |
| `/profile` | Просмотр своего профиля |
| `/premium` | Покупка Premium через Stars |
