from pydantic import Field
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    token: str = Field(alias="BOT_TOKEN")
    url_webhook: str = Field(alias="WEBHOOK_URL", default="https://lsjlove.duckdns.org")

    mongodb_connection_uri: str = Field(alias="MONGO_DB_CONNECTION_URI")
    mongodb_dating_database: str = Field(
        default="dating",
        alias="MONGO_DB_DATING_DATABASE",
    )
    mongodb_users_collection: str = Field(
        default="users",
        alias="MONGO_DB_USERS_COLLECTION",
    )
    mongodb_likes_collection: str = Field(
        default="likes",
        alias="MONGO_DB_LIKES_COLLECTION",
    )

    aws_access_key_id: str = Field(
        alias="AWS_ACCESS_KEY_ID",
    )
    aws_secret_access_key: str = Field(
        alias="AWS_SECRET_ACCESS_KEY",
    )
    bucket_name: str = Field(
        alias="S3_BUCKET_NAME",
    )
    region_name: str = Field(
        default="us-east-005",
        alias="S3_REGION_NAME",
    )
    s3_endpoint_url: str = Field(
        default="https://s3.us-east-005.backblazeb2.com",
        alias="S3_ENDPOINT_URL",
    )

    # OpenAI для AI-фич
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")

    # Стоимость в Telegram Stars
    stars_premium_monthly: int = Field(default=500, alias="STARS_PREMIUM_MONTHLY")
    stars_vip_monthly: int = Field(default=1500, alias="STARS_VIP_MONTHLY")
    stars_superlike: int = Field(default=50, alias="STARS_SUPERLIKE")
    stars_boost: int = Field(default=150, alias="STARS_BOOST")
    stars_ai_pack: int = Field(default=200, alias="STARS_AI_PACK")

    # Лимиты (бесплатный тариф)
    daily_likes_free: int = Field(default=10, alias="DAILY_LIKES_FREE")
    daily_icebreaker_free: int = Field(default=1, alias="DAILY_ICEBREAKER_FREE")

    @property
    def full_webhook_url(self) -> str:
        return f"{self.url_webhook}/api/v1/webhook"

    front_end_url: str = Field(alias="FRONT_END_URL", default="https://lsjlove.duckdns.org")
