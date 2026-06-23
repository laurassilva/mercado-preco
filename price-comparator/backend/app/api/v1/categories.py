import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import datetime, timezone, timedelta

from app.core.database import get_db
from app.core.deps import get_current_user, require_admin
from app.models.category import Category
from app.models.product import MarketProduct, PriceAlert
from app.schemas.category import CategoryCreate, CategoryUpdate, CategoryResponse, CategoryStats
from app.services.category_service import invalidate_cache, classify_product, load_categories, DEFAULT_CATEGORIES

router = APIRouter(prefix="/categories", tags=["Categorias"])


@router.get("/", response_model=list[CategoryResponse])
async def list_categories(db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(Category).order_by(Category.name))
    categories = result.scalars().all()
    return [CategoryResponse.from_orm_with_keywords(c) for c in categories]


@router.post("/", response_model=CategoryResponse, status_code=201)
async def create_category(data: CategoryCreate, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    cat = Category(name=data.name, keywords=json.dumps(data.keywords, ensure_ascii=False))
    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    invalidate_cache()
    return CategoryResponse.from_orm_with_keywords(cat)


@router.patch("/{category_id}", response_model=CategoryResponse)
async def update_category(category_id: str, data: CategoryUpdate, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    result = await db.execute(select(Category).where(Category.id == category_id))
    cat = result.scalar_one_or_none()
    if not cat:
        raise HTTPException(404, "Categoria não encontrada")
    if data.name is not None:
        cat.name = data.name
    if data.keywords is not None:
        cat.keywords = json.dumps(data.keywords, ensure_ascii=False)
    if data.is_active is not None:
        cat.is_active = data.is_active
    await db.commit()
    await db.refresh(cat)
    invalidate_cache()
    return CategoryResponse.from_orm_with_keywords(cat)


@router.delete("/{category_id}", status_code=204)
async def delete_category(category_id: str, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    result = await db.execute(select(Category).where(Category.id == category_id))
    cat = result.scalar_one_or_none()
    if not cat:
        raise HTTPException(404, "Categoria não encontrada")
    await db.delete(cat)
    await db.commit()
    invalidate_cache()


@router.post("/reclassify")
async def reclassify_products(db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    cats = await load_categories(db)
    if not cats:
        raise HTTPException(400, "Nenhuma categoria cadastrada")

    result = await db.execute(select(MarketProduct))
    products = result.scalars().all()
    classified = 0
    for mp in products:
        new_cat = classify_product(mp.name, cats)
        if new_cat and new_cat != mp.category:
            mp.category = new_cat
            classified += 1
    await db.commit()
    invalidate_cache()
    return {"message": f"{classified} produtos reclassificados"}


@router.get("/stats", response_model=list[CategoryStats])
async def category_stats(db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    # Products per category
    product_stats = await db.execute(
        select(
            MarketProduct.category,
            func.count(MarketProduct.id),
            func.avg(MarketProduct.price),
            func.min(MarketProduct.price),
            func.max(MarketProduct.price),
        )
        .where(MarketProduct.category.isnot(None), MarketProduct.is_available == True)
        .group_by(MarketProduct.category)
        .order_by(MarketProduct.category)
    )
    prod_rows = product_stats.all()

    # Alerts today per category
    alert_stats = await db.execute(
        select(PriceAlert.category, func.count(PriceAlert.id))
        .where(PriceAlert.category.isnot(None), PriceAlert.detected_at >= today)
        .group_by(PriceAlert.category)
    )
    alert_map = {row[0]: row[1] for row in alert_stats.all()}

    return [
        CategoryStats(
            category=row[0],
            products_count=row[1],
            alerts_today=alert_map.get(row[0], 0),
            avg_price=round(float(row[2]), 2) if row[2] else None,
            min_price=float(row[3]) if row[3] else None,
            max_price=float(row[4]) if row[4] else None,
        )
        for row in prod_rows
    ]
