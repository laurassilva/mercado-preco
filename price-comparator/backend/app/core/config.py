from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://priceuser:pricepassword@localhost:5432/pricecomparator"
    SYNC_DATABASE_URL: str = "postgresql+psycopg2://priceuser:pricepassword@localhost:5432/pricecomparator"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security
    SECRET_KEY: str = "change-me-in-production-at-least-32-characters-long"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # Admin seed
    FIRST_ADMIN_EMAIL: str = "admin@empresa.com"
    FIRST_ADMIN_PASSWORD: str = "Admin@123"
    FIRST_ADMIN_NAME: str = "Administrador"

    # App
    APP_NAME: str = "Price Comparator"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Scraping
    PLAYWRIGHT_HEADLESS: bool = True
    SCRAPING_TIMEOUT: int = 30
    MAX_CONCURRENT_SCRAPERS: int = 3

    # CORS
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:80",
        "http://localhost",
    ]


settings = Settings()
