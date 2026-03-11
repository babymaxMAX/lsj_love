from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.application.api.lifespan import (
    delete_bot_webhook,
    set_bot_webhook,
    start_logger,
)
from app.application.api.v1.urls import router as v1_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_logger()
    await set_bot_webhook()

    yield
    await delete_bot_webhook()


def create_app():
    import os
    app = FastAPI(
        title="Dating Telegram Bot API",
        description="API for creating, updating, and deleting dating profiles",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/api/docs",
        debug=os.getenv("DEBUG", "false").lower() in ("1", "true", "yes"),
    )
    # CORS: в проде ограничьте allow_origins списком доверенных доменов
    cors_origins = os.getenv("CORS_ORIGINS", "*")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in cors_origins.split(",") if o.strip()] if cors_origins != "*" else ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(v1_router, prefix="/api")

    return app
