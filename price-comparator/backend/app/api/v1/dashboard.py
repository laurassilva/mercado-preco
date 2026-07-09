from datetime import datetime, timezone, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.market import Market
from app.models.product import MarketProduct, MasterProduct, PriceHistory
from app.models.search_history import SearchHistory
from app.models.user import User
from app.schemas.dashboard import DashboardResponse, DashboardStats, RecentSearch, MarketSummary, PriceUpdatesByDay

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

    # Catálogo Mestre: indicadores de vínculo/curadoria
    total_master_products = (await db.execute(select(func.count()).select_from(MasterProduct))).scalar() or 0
    matched_count = (await db.execute(
        select(func.count()).select_from(MarketProduct)
        .where(MarketProduct.match_status.in_(["matched_gtin", "matched_similarity", "matched_legacy"]))
    )).scalar() or 0
    pending_review_count = (await db.execute(
        select(func.count()).select_from(MarketProduct).where(MarketProduct.match_status == "pending_review")
    )).scalar() or 0
    unmatched_count = (await db.execute(
        select(func.count()).select_from(MarketProduct).where(MarketProduct.match_status == "unmatched")
    )).scalar() or 0
    day_ago = datetime.now(timezone.utc) - timedelta(hours=24)
    new_market_products_24h = (await db.execute(
        select(func.count()).select_from(MarketProduct).where(MarketProduct.created_at >= day_ago)
    )).scalar() or 0

    # Preços atualizados por dia (últimos 7 dias)
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    updates_by_day_q = (
        select(func.date(PriceHistory.checked_at).label("day"), func.count(PriceHistory.id).label("count"))
        .where(PriceHistory.checked_at >= week_ago)
        .group_by(func.date(PriceHistory.checked_at))
        .order_by(func.date(PriceHistory.checked_at))
    )
    updates_by_day_result = await db.execute(updates_by_day_q)
    price_updates_by_day = [
        PriceUpdatesByDay(date=row.day.isoformat(), count=row.count) for row in updates_by_day_result.all()
    ]

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
            total_master_products=total_master_products,
            matched_count=matched_count,
            pending_review_count=pending_review_count,
            unmatched_count=unmatched_count,
            new_market_products_24h=new_market_products_24h,
        ),
        recent_searches=recent_searches,
        market_summary=market_summary,
        price_updates_by_day=price_updates_by_day,
    )
