from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional

from app.core.database import get_db
from app.core.deps import get_current_user, require_admin
from app.models.product import ProductGroup, MarketProduct
from app.models.market import Market
from app.services.product_matching_service import regroup_all_products

router = APIRouter(prefix="/product-groups", tags=["Produtos Mestre"])


@router.get("/")
async def list_groups(
    q: Optional[str] = Query(None, min_length=2),
    category: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """List product groups with their market prices."""
    from sqlalchemy import func as sqlfunc
    from app.scrapers.search_utils import _normalize, _key_terms

    stmt = (
        select(
            ProductGroup.id,
            ProductGroup.canonical_name,
            ProductGroup.brand,
            ProductGroup.quantity,
            ProductGroup.category,
            sqlfunc.count(MarketProduct.id).label("market_count"),
            sqlfunc.min(MarketProduct.price).label("min_price"),
            sqlfunc.max(MarketProduct.price).label("max_price"),
            sqlfunc.avg(MarketProduct.price).label("avg_price"),
        )
        .outerjoin(MarketProduct, MarketProduct.product_group_id == ProductGroup.id)
        .group_by(ProductGroup.id)
        .having(sqlfunc.count(MarketProduct.id) > 0)
        .order_by(ProductGroup.canonical_name)
    )

    if q:
        key_terms = _key_terms(q)
        if key_terms:
            for term in key_terms:
                stmt = stmt.where(
                    sqlfunc.f_unaccent(ProductGroup.canonical_name).ilike(f"%{term}%")
                )

    if category:
        stmt = stmt.where(ProductGroup.category == category)

    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    rows = result.all()

    return [
        {
            "id": str(row.id),
            "canonical_name": row.canonical_name,
            "brand": row.brand,
            "quantity": row.quantity,
            "category": row.category,
            "market_count": row.market_count,
            "min_price": float(row.min_price) if row.min_price else None,
            "max_price": float(row.max_price) if row.max_price else None,
            "avg_price": round(float(row.avg_price), 2) if row.avg_price else None,
        }
        for row in rows
    ]


@router.get("/{group_id}/prices")
async def group_prices(
    group_id: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """Get all market prices for a product group."""
    result = await db.execute(
        select(MarketProduct, Market.name.label("market_name"))
        .join(Market, MarketProduct.market_id == Market.id)
        .where(
            MarketProduct.product_group_id == group_id,
            MarketProduct.is_available == True,
        )
        .order_by(MarketProduct.price)
    )
    rows = result.all()

    if not rows:
        raise HTTPException(404, "Grupo não encontrado ou sem produtos")

    return {
        "group_id": group_id,
        "products": [
            {
                "id": str(mp.id),
                "market_name": market_name,
                "product_name": mp.name,
                "brand": mp.brand,
                "price": float(mp.price) if mp.price else None,
                "image_url": mp.image_url,
                "product_url": mp.product_url,
                "last_updated": mp.last_updated.isoformat() if mp.last_updated else None,
            }
            for mp, market_name in rows
        ],
    }


@router.post("/regroup")
async def regroup(db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    """Re-run product grouping for all products."""
    total = await regroup_all_products(db)
    return {"message": f"{total} produtos agrupados"}


@router.get("/stats")
async def group_stats(db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    """Statistics about product grouping."""
    from sqlalchemy import func as sqlfunc

    total_groups = (await db.execute(select(sqlfunc.count()).select_from(ProductGroup))).scalar() or 0
    total_grouped = (await db.execute(
        select(sqlfunc.count()).select_from(MarketProduct).where(MarketProduct.product_group_id.isnot(None))
    )).scalar() or 0
    total_ungrouped = (await db.execute(
        select(sqlfunc.count()).select_from(MarketProduct).where(MarketProduct.product_group_id.is_(None))
    )).scalar() or 0

    # Groups with products from multiple markets (actual comparisons)
    multi_market = (await db.execute(
        select(sqlfunc.count()).select_from(
            select(ProductGroup.id)
            .join(MarketProduct, MarketProduct.product_group_id == ProductGroup.id)
            .group_by(ProductGroup.id)
            .having(sqlfunc.count(sqlfunc.distinct(MarketProduct.market_id)) >= 2)
            .subquery()
        )
    )).scalar() or 0

    return {
        "total_groups": total_groups,
        "total_grouped": total_grouped,
        "total_ungrouped": total_ungrouped,
        "multi_market_groups": multi_market,
    }
