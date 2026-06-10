import uuid
from datetime import datetime
from pydantic import BaseModel


class MarketCreate(BaseModel):
    name: str
    url: str
    logo_url: str | None = None
    integration_type: str = "scraping"
    scraper_class: str = "mock"
    is_active: bool = True
    config: dict = {}


class MarketUpdate(BaseModel):
    name: str | None = None
    url: str | None = None
    logo_url: str | None = None
    integration_type: str | None = None
    scraper_class: str | None = None
    is_active: bool | None = None
    config: dict | None = None


class MarketResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    name: str
    url: str
    logo_url: str | None
    integration_type: str
    scraper_class: str
    is_active: bool
    config: dict
    created_at: datetime
    updated_at: datetime
