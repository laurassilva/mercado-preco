import uuid
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, field_serializer


def _dec_to_float(v: Decimal | None) -> float | None:
    return float(v) if v is not None else None


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
    confidence_score: float | None = None

    @field_serializer("price")
    def _price(self, v: Decimal) -> float:
        return float(v)

    @field_serializer("difference")
    def _difference(self, v: Decimal | None) -> float | None:
        return _dec_to_float(v)


class SearchResponse(BaseModel):
    query: str
    corrected_query: str | None = None
    results: list[ProductResult]
    total: int
    cheapest_market: str | None = None
    most_expensive_market: str | None = None
    avg_price: Decimal | None = None
    searched_at: datetime

    @field_serializer("avg_price")
    def _avg_price(self, v: Decimal | None) -> float | None:
        return _dec_to_float(v)


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

    @field_serializer("price")
    def _price(self, v: Decimal | None) -> float | None:
        return _dec_to_float(v)


class PriceHistoryResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    price: Decimal
    checked_at: datetime

    @field_serializer("price")
    def _price(self, v: Decimal) -> float:
        return float(v)


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
