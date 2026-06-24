from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.access_log import AccessLog


async def log_access(
    db: AsyncSession,
    user_id=None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    action: str = "login",
    details: str | None = None,
):
    entry = AccessLog(
        user_id=user_id,
        ip_address=ip_address,
        user_agent=user_agent,
        action=action,
        details=details,
    )
    db.add(entry)
    await db.flush()


async def get_user_logs(db: AsyncSession, user_id, limit: int = 50, offset: int = 0):
    result = await db.execute(
        select(AccessLog)
        .where(AccessLog.user_id == user_id)
        .order_by(AccessLog.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return result.scalars().all()


async def get_all_logs(db: AsyncSession, limit: int = 100, offset: int = 0, action: str | None = None):
    stmt = select(AccessLog).order_by(AccessLog.created_at.desc())
    if action:
        stmt = stmt.where(AccessLog.action == action)
    result = await db.execute(stmt.offset(offset).limit(limit))
    return result.scalars().all()
