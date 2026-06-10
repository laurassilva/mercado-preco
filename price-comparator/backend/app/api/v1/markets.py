import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.deps import get_current_user, require_admin
from app.models.market import Market
from app.schemas.market import MarketCreate, MarketUpdate, MarketResponse

router = APIRouter(prefix="/markets", tags=["Mercados"])


@router.get("/", response_model=list[MarketResponse])
async def list_markets(db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(Market).order_by(Market.name))
    return result.scalars().all()


@router.post("/", response_model=MarketResponse, status_code=201)
async def create_market(data: MarketCreate, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    market = Market(**data.model_dump())
    db.add(market)
    await db.commit()
    await db.refresh(market)
    return market


@router.get("/{market_id}", response_model=MarketResponse)
async def get_market(market_id: uuid.UUID, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(Market).where(Market.id == market_id))
    market = result.scalar_one_or_none()
    if not market:
        raise HTTPException(404, "Mercado não encontrado")
    return market


@router.patch("/{market_id}", response_model=MarketResponse)
async def update_market(
    market_id: uuid.UUID, data: MarketUpdate,
    db: AsyncSession = Depends(get_db), _=Depends(require_admin)
):
    result = await db.execute(select(Market).where(Market.id == market_id))
    market = result.scalar_one_or_none()
    if not market:
        raise HTTPException(404, "Mercado não encontrado")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(market, k, v)
    await db.commit()
    await db.refresh(market)
    return market


@router.delete("/{market_id}", status_code=204)
async def delete_market(market_id: uuid.UUID, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    result = await db.execute(select(Market).where(Market.id == market_id))
    market = result.scalar_one_or_none()
    if not market:
        raise HTTPException(404, "Mercado não encontrado")
    await db.delete(market)
    await db.commit()
