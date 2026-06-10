import uuid
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel


class ProductResult(BaseModel):
    market_id: uuid.UUID | None = None
    market_name: str
    market_logo: str | None = None
    product_name: str
    brand: str | None = None
    quantity: str | None = None
    price: Decimal
    image_url: str | None = None
    product_url: str | None = None
    last_updated: datetime | None = None
    difference: Decimal | None = None
    difference_pct: float | None = None
    is_cheapest: bool = False


class SearchResponse(BaseModel):
    query: str
    results: list[ProductResult]
    total: int
    cheapest_market: str | None = None
    most_expensive_market: str | None = None
    avg_price: Decimal | None = None
    searched_at: datetime


class MarketProductResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    market_id: uuid.UUID
    name: str
    brand: str | None
    quantity: str | None
    price: Decimal | None
    image_url: str | None
    product_url: str | None
    is_available: bool
    last_updated: datetime


class PriceHistoryResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    price: Decimal
    checked_at: datetime


class ScrapingJobCreate(BaseModel):
    market_ids: list[uuid.UUID] | None = None
    query: str


class ScrapingJobResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    market_id: uuid.UUID | None
    query: str | None
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None
    results_count: int
    created_at: datetime
