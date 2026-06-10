from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import get_current_user, require_admin
from app.models.search_history import SearchHistory
from app.models.user import User

router = APIRouter(prefix="/history", tags=["Histórico"])


@router.get("/")
async def list_history(
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retorna histórico de pesquisas. Admin vê todos; usuário vê apenas as próprias."""
    query = select(SearchHistory).options(selectinload(SearchHistory.user)).order_by(
        SearchHistory.created_at.desc()
    )
    if current_user.role != "admin":
        query = query.where(SearchHistory.user_id == current_user.id)
    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    rows = result.scalars().all()

    return [
        {
            "id": str(r.id),
            "query": r.query,
            "results_count": r.results_count,
            "created_at": r.created_at,
            "user_name": r.user.name if r.user else "Sistema",
            "user_email": r.user.email if r.user else None,
        }
        for r in rows
    ]


@router.delete("/{history_id}", status_code=204)
async def delete_history(history_id: str, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    from sqlalchemy import delete
    await db.execute(delete(SearchHistory).where(SearchHistory.id == history_id))
    await db.commit()
