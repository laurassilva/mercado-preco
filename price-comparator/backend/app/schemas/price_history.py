from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel


class PriceHistoryEntry(BaseModel):
    price: Decimal
    checked_at: datetime


class ProductPriceHistory(BaseModel):
    product_id: str
    product_name: str
    market_id: str
    market_name: str
    current_price: Decimal
    category: str | None
    history: list[PriceHistoryEntry]


class PriceHistorySearchResponse(BaseModel):
    query: str
    period_days: int
    products: list[ProductPriceHistory]
    stats: dict


class PriceHistoryStats(BaseModel):
    min_price: Decimal | None
    max_price: Decimal | None
    avg_price: float | None
    total_changes: int
    period_days: int
