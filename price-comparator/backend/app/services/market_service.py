from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.market import Market


async def get_active_markets(db: AsyncSession) -> list[Market]:
    result = await db.execute(select(Market).where(Market.is_active == True).order_by(Market.name))
    return result.scalars().all()
