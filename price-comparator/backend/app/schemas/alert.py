from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel


class PriceAlertResponse(BaseModel):
    id: str
    market_product_id: str
    market_id: str
    product_name: str
    old_price: Decimal
    new_price: Decimal
    price_diff: Decimal
    price_diff_pct: Decimal
    alert_type: str
    category: str | None
    detected_at: datetime
    market_name: str | None = None

    model_config = {"from_attributes": True}


class AlertsSummary(BaseModel):
    total_today: int
    increases_today: int
    decreases_today: int
    biggest_increase: PriceAlertResponse | None
    biggest_decrease: PriceAlertResponse | None
