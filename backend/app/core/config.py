from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "SustainIQ API"
    API_V1_STR: str = "/api/v1"
    # Matches JWT_SECRET in .env and docker-compose
    SECRET_KEY: str = "sustainiq_super_secret_key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://sustainiq:password@db:5432/sustainiq_db"

    # AWS
    AWS_DEFAULT_REGION: str = "us-east-1"
    BEDROCK_MODEL_ID: str = "amazon.nova-lite-v1:0"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
        populate_by_name=True,
        # JWT_SECRET in env maps to SECRET_KEY in code
        env_prefix="",
    )

    def model_post_init(self, __context):
        pass

settings = Settings()
