# AGENTS.md

## Cursor Cloud specific instructions

### Overview

LSJLove is a Telegram Dating Mini App with three main components:

| Service | Tech | Port | Start Command |
|---------|------|------|---------------|
| Backend API | FastAPI + aiogram 3 (Python 3.12, Poetry) | 8000 | `MONGO_DB_CONNECTION_URI="mongodb://localhost:27017/" poetry run uvicorn --factory app.application.api.main:create_app --host 0.0.0.0 --port 8000 --reload` |
| Frontend | Next.js (Node 20, npm) | 3000 | `cd frontend && BACKEND_URL="http://localhost:8000" npx next dev -p 3000` |
| MongoDB | Docker container (mongo:6-jammy) | 27017 | `docker run -d --name dev-mongodb -p 27017:27017 mongo:6-jammy` |

### Startup caveats

- **Docker daemon must be started manually**: Run `sudo dockerd &>/dev/null &` then wait a few seconds before running any Docker commands.
- **Docker socket permissions**: After starting dockerd, run `sudo chmod 666 /var/run/docker.sock` to allow non-root Docker access.
- **BOT_TOKEN is required**: The backend validates the Telegram bot token at import time (aiogram). The token must match the format `NNNNNN:XXXXXXXXXXX`. The environment has secrets injected including `BOT_TOKEN`.
- **Webhook setup on startup**: The backend lifespan calls `bot.set_webhook()` on startup. This will fail if the BOT_TOKEN is invalid/expired, causing the server to exit. With a valid token, the server starts fine.
- **MONGO_DB_CONNECTION_URI override**: The injected secret may point to a container hostname (`mongodb`). When running locally, override with `MONGO_DB_CONNECTION_URI="mongodb://localhost:27017/"`.
- **Node.js version**: The project requires Node 20. Use `nvm use 20` before running frontend commands.
- **Frontend npm install**: Use `npm install --legacy-peer-deps` (required due to peer dependency conflicts).
- **Frontend build cache**: If the Next.js dev server shows webpack errors, clear the cache with `rm -rf frontend/.next` and restart.

### Lint / Test / Build

- **Backend lint**: `ruff check app/` (pre-existing warnings exist in the codebase)
- **Frontend lint**: `cd frontend && npx next lint`
- **Backend tests**: `poetry run pytest app/tests/ -v` (15 domain tests pass; 18 logic/API tests fail due to pre-existing abstract method gaps in memory repositories)
- **Frontend build**: `cd frontend && npm run build`
- **Pre-commit hooks**: Configured in `.pre-commit-config.yaml` (ruff, isort, autoflake, pyupgrade, docformatter)

### Environment variables

All secrets are documented in `.env.example`. Key required vars: `BOT_TOKEN`, `MONGO_DB_CONNECTION_URI`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `S3_BUCKET_NAME`. The backend reads env vars directly (pydantic-settings); the `.env` file is used by Docker Compose, not by direct local runs.
