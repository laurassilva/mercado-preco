from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://priceuser:pricepassword@localhost:5432/pricecomparator"
    SYNC_DATABASE_URL: str = ""

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

    @model_validator(mode="after")
    def fix_database_urls(self):
        url = self.DATABASE_URL
        for prefix in ("postgres://", "postgresql://"):
            if url.startswith(prefix) and "+" not in url.split("://")[0]:
                url = "postgresql+asyncpg://" + url[len(prefix):]
                break
        self.DATABASE_URL = url
        if not self.SYNC_DATABASE_URL:
            self.SYNC_DATABASE_URL = url.replace("+asyncpg", "+psycopg2")
        else:
            sync = self.SYNC_DATABASE_URL
            for prefix in ("postgres://", "postgresql://"):
                if sync.startswith(prefix) and "+" not in sync.split("://")[0]:
                    sync = "postgresql+psycopg2://" + sync[len(prefix):]
                    break
            if "+asyncpg" in sync:
                sync = sync.replace("+asyncpg", "+psycopg2")
            self.SYNC_DATABASE_URL = sync
        return self


settings = Settings()
