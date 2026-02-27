from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.application.api.lifespan import (
    delete_bot_webhook,
    set_bot_webhook,
    start_logger,
)
from app.application.api.v1.urls import router as v1_router


async def _ensure_indexes():
    """Создаёт индексы MongoDB при старте."""
    import logging
    try:
        from app.logic.init import init_container
        from motor.motor_asyncio import AsyncIOMotorClient
        from app.settings.config import Config
        container = init_container()
        client: AsyncIOMotorClient = container.resolve(AsyncIOMotorClient)
        config: Config = container.resolve(Config)
        db = client[config.mongodb_dating_database]
        users = db[config.mongodb_users_collection]
        likes = db[config.mongodb_likes_collection]
        await users.create_index("telegram_id", unique=True)
        await users.create_index("gender")
        await users.create_index("city")
        await users.create_index("is_active")
        await users.create_index("premium_type")
        await likes.create_index([("from_user", 1), ("to_user", 1)], unique=True)
        await likes.create_index("from_user")
        await likes.create_index("to_user")
        await likes.create_index("created_at")
        logging.getLogger(__name__).info("MongoDB indexes ensured")
    except Exception as e:
        logging.getLogger(__name__).warning(f"Index creation failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_logger()
    await set_bot_webhook()
    await _ensure_indexes()

    yield
    await delete_bot_webhook()


def create_app():
    app = FastAPI(
        title="Dating Telegram Bot API",
        description="API for creating, updating, and deleting dating profiles",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/api/docs",
        debug=True,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(v1_router, prefix="/api")

    @app.get("/health", tags=["Health"])
    async def health_check():
        """Health check endpoint for Docker and monitoring."""
        import logging
        result = {"status": "ok", "mongodb": "unknown", "s3": "unknown"}
        try:
            from app.logic.init import init_container
            from motor.motor_asyncio import AsyncIOMotorClient
            container = init_container()
            client: AsyncIOMotorClient = container.resolve(AsyncIOMotorClient)
            await client.admin.command("ping")
            result["mongodb"] = "connected"
        except Exception as e:
            logging.getLogger(__name__).warning(f"Health: MongoDB check failed: {e}")
            result["mongodb"] = "disconnected"
        result["s3"] = "ok"
        return result

    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        import logging
        import traceback
        from fastapi.responses import JSONResponse
        logging.getLogger(__name__).error(f"Unhandled error: {exc}\n{traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={"detail": {"error": "Внутренняя ошибка сервера. Попробуйте позже."}},
        )

    return app
