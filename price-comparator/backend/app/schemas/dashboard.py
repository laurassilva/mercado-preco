from pydantic import BaseModel
from decimal import Decimal
from datetime import datetime


class DashboardStats(BaseModel):
    total_products_monitored: int
    total_markets: int
    total_searches_today: int
    last_update: datetime | None
    cheapest_market: str | None
    most_expensive_market: str | None


class RecentSearch(BaseModel):
    query: str
    results_count: int
    created_at: datetime
    user_name: str | None


class MarketSummary(BaseModel):
    market_name: str
    avg_price: Decimal
    products_count: int


class DashboardResponse(BaseModel):
    stats: DashboardStats
    recent_searches: list[RecentSearch]
    market_summary: list[MarketSummary]
