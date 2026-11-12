from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "YouTube Clone MVP"
    APP_ENV: str = "development"
    CORS_ORIGINS: str = "http://localhost,http://127.0.0.1"

    SECRET_KEY: str = "dev-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    COOKIE_SECURE: bool = False

    DATABASE_URL: str = "postgresql+asyncpg://youtube:youtube_secret_password@postgres:5432/youtube"
    REDIS_URL: str = "redis://redis:6379/0"

    MINIO_ENDPOINT: str = "http://minio:9000"
    MINIO_ROOT_USER: str = "minioadmin"
    MINIO_ROOT_PASSWORD: str = "minioadmin_secret"
    MINIO_REGION: str = "us-east-1"
    MINIO_VIDEOS_BUCKET: str = "videos"
    MINIO_THUMBNAILS_BUCKET: str = "thumbnails"

    MAX_VIDEO_SIZE_MB: int = 1024
    MAX_THUMBNAIL_SIZE_MB: int = 10

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


settings = Settings()
