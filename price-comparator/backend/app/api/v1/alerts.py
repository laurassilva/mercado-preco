from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.product import PriceAlert
from app.models.market import Market
from app.schemas.alert import PriceAlertResponse, AlertsSummary

router = APIRouter(prefix="/alerts", tags=["Alertas"])


def _period_start(period: str) -> datetime:
    days_map = {"1d": 1, "7d": 7, "15d": 15, "30d": 30, "60d": 60, "90d": 90}
    days = days_map.get(period, 7)
    return datetime.now(timezone.utc) - timedelta(days=days)


@router.get("/", response_model=list[PriceAlertResponse])
async def list_alerts(
    market_id: Optional[str] = Query(None),
    alert_type: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    period: str = Query("7d"),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    start = _period_start(period)
    stmt = (
        select(PriceAlert, Market.name.label("market_name"))
        .join(Market, PriceAlert.market_id == Market.id)
        .where(PriceAlert.detected_at >= start)
        .order_by(desc(PriceAlert.detected_at))
    )
    if market_id:
        stmt = stmt.where(PriceAlert.market_id == market_id)
    if alert_type:
        stmt = stmt.where(PriceAlert.alert_type == alert_type)
    if category:
        stmt = stmt.where(PriceAlert.category == category)

    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    rows = result.all()

    return [
        PriceAlertResponse(
            id=str(alert.id),
            market_product_id=str(alert.market_product_id),
            market_id=str(alert.market_id),
            product_name=alert.product_name,
            old_price=alert.old_price,
            new_price=alert.new_price,
            price_diff=alert.price_diff,
            price_diff_pct=alert.price_diff_pct,
            alert_type=alert.alert_type,
            category=alert.category,
            detected_at=alert.detected_at,
            market_name=market_name,
        )
        for alert, market_name in rows
    ]


@router.get("/summary", response_model=AlertsSummary)
async def alerts_summary(
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    # Totals
    total = (await db.execute(
        select(func.count()).select_from(PriceAlert).where(PriceAlert.detected_at >= today)
    )).scalar() or 0

    increases = (await db.execute(
        select(func.count()).select_from(PriceAlert).where(
            PriceAlert.detected_at >= today, PriceAlert.alert_type == "increase"
        )
    )).scalar() or 0

    decreases = (await db.execute(
        select(func.count()).select_from(PriceAlert).where(
            PriceAlert.detected_at >= today, PriceAlert.alert_type == "decrease"
        )
    )).scalar() or 0

    # Biggest increase
    inc_row = await db.execute(
        select(PriceAlert, Market.name.label("market_name"))
        .join(Market, PriceAlert.market_id == Market.id)
        .where(PriceAlert.detected_at >= today, PriceAlert.alert_type == "increase")
        .order_by(desc(PriceAlert.price_diff_pct))
        .limit(1)
    )
    inc = inc_row.first()
    biggest_inc = None
    if inc:
        alert, mname = inc
        biggest_inc = PriceAlertResponse(
            id=str(alert.id), market_product_id=str(alert.market_product_id),
            market_id=str(alert.market_id), product_name=alert.product_name,
            old_price=alert.old_price, new_price=alert.new_price,
            price_diff=alert.price_diff, price_diff_pct=alert.price_diff_pct,
            alert_type=alert.alert_type, category=alert.category,
            detected_at=alert.detected_at, market_name=mname,
        )

    # Biggest decrease
    dec_row = await db.execute(
        select(PriceAlert, Market.name.label("market_name"))
        .join(Market, PriceAlert.market_id == Market.id)
        .where(PriceAlert.detected_at >= today, PriceAlert.alert_type == "decrease")
        .order_by(PriceAlert.price_diff_pct)
        .limit(1)
    )
    dec = dec_row.first()
    biggest_dec = None
    if dec:
        alert, mname = dec
        biggest_dec = PriceAlertResponse(
            id=str(alert.id), market_product_id=str(alert.market_product_id),
            market_id=str(alert.market_id), product_name=alert.product_name,
            old_price=alert.old_price, new_price=alert.new_price,
            price_diff=alert.price_diff, price_diff_pct=alert.price_diff_pct,
            alert_type=alert.alert_type, category=alert.category,
            detected_at=alert.detected_at, market_name=mname,
        )

    return AlertsSummary(
        total_today=total,
        increases_today=increases,
        decreases_today=decreases,
        biggest_increase=biggest_inc,
        biggest_decrease=biggest_dec,
    )
