import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional
from decimal import Decimal

from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.product import MarketProduct, PriceHistory
from app.models.market import Market
from app.schemas.price_history import PriceHistoryEntry, ProductPriceHistory, PriceHistorySearchResponse, PriceHistoryStats
from app.services.price_history_service import generate_history_pdf, generate_history_excel

router = APIRouter(prefix="/price-history", tags=["Histórico de Preços"])


def _period_start(period: str) -> datetime:
    days_map = {"7d": 7, "15d": 15, "30d": 30, "60d": 60, "90d": 90}
    days = days_map.get(period, 30)
    return datetime.now(timezone.utc) - timedelta(days=days)


async def _build_history(
    db: AsyncSession, query: str, period: str, market_id: str | None, category: str | None,
) -> list[ProductPriceHistory]:
    from app.scrapers.search_utils import _key_terms
    from sqlalchemy import func as sqlfunc

    start = _period_start(period)
    days = int(period.replace("d", "")) if period.endswith("d") else 30

    key_terms = _key_terms(query)
    if not key_terms:
        return []

    # Find matching products
    stmt = (
        select(MarketProduct, Market.name.label("market_name"))
        .join(Market, MarketProduct.market_id == Market.id)
        .where(MarketProduct.is_available == True, Market.is_active == True)
    )
    ilike_clauses = [sqlfunc.f_unaccent(MarketProduct.name).ilike(f"%{t}%") for t in key_terms]
    if len(ilike_clauses) >= 2:
        stmt = stmt.where(and_(*ilike_clauses))
    else:
        stmt = stmt.where(ilike_clauses[0])

    if market_id:
        stmt = stmt.where(Market.id == market_id)
    if category:
        stmt = stmt.where(MarketProduct.category == category)

    stmt = stmt.limit(50)
    result = await db.execute(stmt)
    rows = result.all()

    products = []
    for mp, market_name in rows:
        # Get price history for this product
        hist_stmt = (
            select(PriceHistory)
            .where(PriceHistory.market_product_id == mp.id, PriceHistory.checked_at >= start)
            .order_by(PriceHistory.checked_at)
        )
        hist_result = await db.execute(hist_stmt)
        entries = hist_result.scalars().all()

        history = [PriceHistoryEntry(price=h.price, checked_at=h.checked_at) for h in entries]
        # Always include current price as last entry
        history.append(PriceHistoryEntry(price=mp.price, checked_at=mp.last_updated or datetime.now(timezone.utc)))

        products.append(ProductPriceHistory(
            product_id=str(mp.id),
            product_name=mp.name,
            market_id=str(mp.market_id),
            market_name=market_name,
            current_price=mp.price,
            category=mp.category,
            history=history,
        ))

    return products


@router.get("/search", response_model=PriceHistorySearchResponse)
async def search_history(
    q: str = Query(..., min_length=2),
    period: str = Query("30d"),
    market_id: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    days = int(period.replace("d", "")) if period.endswith("d") else 30
    products = await _build_history(db, q, period, market_id, category)

    all_prices = []
    total_changes = 0
    for p in products:
        for h in p.history:
            all_prices.append(float(h.price))
        total_changes += max(0, len(p.history) - 1)

    stats = {
        "min_price": min(all_prices) if all_prices else None,
        "max_price": max(all_prices) if all_prices else None,
        "avg_price": round(sum(all_prices) / len(all_prices), 2) if all_prices else None,
        "total_changes": total_changes,
    }

    return PriceHistorySearchResponse(
        query=q, period_days=days, products=products, stats=stats,
    )


@router.get("/product/{product_id}")
async def product_history(
    product_id: str,
    period: str = Query("30d"),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    start = _period_start(period)

    result = await db.execute(
        select(MarketProduct, Market.name.label("market_name"))
        .join(Market, MarketProduct.market_id == Market.id)
        .where(MarketProduct.id == product_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(404, "Produto não encontrado")

    mp, market_name = row

    hist_result = await db.execute(
        select(PriceHistory)
        .where(PriceHistory.market_product_id == mp.id, PriceHistory.checked_at >= start)
        .order_by(PriceHistory.checked_at)
    )
    entries = hist_result.scalars().all()
    history = [PriceHistoryEntry(price=h.price, checked_at=h.checked_at) for h in entries]
    history.append(PriceHistoryEntry(price=mp.price, checked_at=mp.last_updated or datetime.now(timezone.utc)))

    return ProductPriceHistory(
        product_id=str(mp.id), product_name=mp.name,
        market_id=str(mp.market_id), market_name=market_name,
        current_price=mp.price, category=mp.category, history=history,
    )


@router.get("/export/pdf")
async def export_pdf(
    q: str = Query(..., min_length=2),
    period: str = Query("30d"),
    market_id: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    products = await _build_history(db, q, period, market_id, category)
    pdf_bytes = generate_history_pdf(q, period, products)
    return Response(
        content=pdf_bytes, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="historico_{q.replace(" ", "_")}.pdf"'},
    )


@router.get("/export/excel")
async def export_excel(
    q: str = Query(..., min_length=2),
    period: str = Query("30d"),
    market_id: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    products = await _build_history(db, q, period, market_id, category)
    excel_bytes = generate_history_excel(q, period, products)
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="historico_{q.replace(" ", "_")}.xlsx"'},
    )
