from pydantic import Field
from pydantic_settings import BaseSettings


class V2Settings(BaseSettings):
    app_name: str = Field(default="AI Kupidon v2", alias="V2_APP_NAME")
    app_env: str = Field(default="local", alias="V2_APP_ENV")
    app_secret: str = Field(default="change-me-v2-secret", alias="V2_APP_SECRET")

    postgres_dsn: str = Field(
        default="postgresql+asyncpg://postgres:postgres@postgres:5432/ai_kupidon_v2",
        alias="V2_POSTGRES_DSN",
    )
    redis_dsn: str = Field(default="redis://redis:6379/0", alias="V2_REDIS_DSN")

    bot_token: str = Field(default="", alias="V2_BOT_TOKEN")
    bot_username: str = Field(default="", alias="V2_BOT_USERNAME")
    front_end_url: str = Field(default="https://lsjlove.duckdns.org", alias="V2_FRONTEND_URL")

    admin_api_key: str = Field(default="", alias="V2_ADMIN_API_KEY")
    allow_legacy_fallback: bool = Field(default=True, alias="V2_ALLOW_LEGACY_FALLBACK")

