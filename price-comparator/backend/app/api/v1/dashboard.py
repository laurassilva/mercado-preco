from datetime import datetime, timezone, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.market import Market
from app.models.product import MarketProduct
from app.models.search_history import SearchHistory
from app.models.user import User
from app.schemas.dashboard import DashboardResponse, DashboardStats, RecentSearch, MarketSummary

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/", response_model=DashboardResponse)
async def dashboard(db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    total_products = (await db.execute(select(func.count()).select_from(MarketProduct))).scalar() or 0
    total_markets = (await db.execute(select(func.count()).select_from(Market).where(Market.is_active == True))).scalar() or 0
    searches_today = (await db.execute(
        select(func.count()).select_from(SearchHistory).where(SearchHistory.created_at >= today)
    )).scalar() or 0

    last_update_row = await db.execute(
        select(MarketProduct.last_updated).order_by(MarketProduct.last_updated.desc()).limit(1)
    )
    last_update = last_update_row.scalar_one_or_none()

    # Market summary: avg price per market
    market_stats_q = (
        select(Market.name, func.avg(MarketProduct.price).label("avg_price"), func.count(MarketProduct.id).label("count"))
        .join(MarketProduct, MarketProduct.market_id == Market.id)
        .where(Market.is_active == True)
        .group_by(Market.id, Market.name)
        .order_by(func.avg(MarketProduct.price))
    )
    market_stats_result = await db.execute(market_stats_q)
    market_stats = market_stats_result.all()

    cheapest = market_stats[0][0] if market_stats else None
    priciest = market_stats[-1][0] if market_stats else None

    market_summary = [
        MarketSummary(
            market_name=row[0],
            avg_price=Decimal(str(row[1] or 0)).quantize(Decimal("0.01")),
            products_count=row[2],
        )
        for row in market_stats
    ]

    # Recent searches
    recent_q = (
        select(SearchHistory, User.name)
        .outerjoin(User, SearchHistory.user_id == User.id)
        .order_by(SearchHistory.created_at.desc())
        .limit(10)
    )
    recent_result = await db.execute(recent_q)
    recent_rows = recent_result.all()

    recent_searches = [
        RecentSearch(
            query=row[0].query,
            results_count=row[0].results_count,
            created_at=row[0].created_at,
            user_name=row[1],
        )
        for row in recent_rows
    ]

    return DashboardResponse(
        stats=DashboardStats(
            total_products_monitored=total_products,
            total_markets=total_markets,
            total_searches_today=searches_today,
            last_update=last_update,
            cheapest_market=cheapest,
            most_expensive_market=priciest,
        ),
        recent_searches=recent_searches,
        market_summary=market_summary,
    )
