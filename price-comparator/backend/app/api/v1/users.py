import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func

from app.core.database import get_db
from app.core.deps import get_current_user, require_admin
from app.core.security import hash_password, generate_reset_token
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.services.auth_service import create_user
from app.services.access_log_service import get_user_logs

router = APIRouter(prefix="/users", tags=["Usuários"])


@router.get("/", response_model=list[UserResponse])
async def list_users(
    q: str | None = Query(None, description="Buscar por nome ou email"),
    status: str | None = Query(None, description="Filtrar por status"),
    role: str | None = Query(None, description="Filtrar por role"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    stmt = select(User).order_by(User.created_at.desc())

    if q:
        search = f"%{q}%"
        stmt = stmt.where(
            or_(
                func.lower(User.name).like(func.lower(search)),
                func.lower(User.email).like(func.lower(search)),
            )
        )
    if status:
        stmt = stmt.where(User.status == status)
    if role:
        stmt = stmt.where(User.role == role)

    offset = (page - 1) * per_page
    stmt = stmt.offset(offset).limit(per_page)

    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/", response_model=UserResponse, status_code=201)
async def create(data: UserCreate, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    return await create_user(data, db)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: uuid.UUID, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "Usuário não encontrado")
    return user


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: uuid.UUID,
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin" and current_user.id != user_id:
        raise HTTPException(403, "Sem permissão")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "Usuário não encontrado")
    update_data = data.model_dump(exclude_unset=True)
    if "password" in update_data:
        update_data["password_hash"] = hash_password(update_data.pop("password"))
    for k, v in update_data.items():
        setattr(user, k, v)
    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=204)
async def delete_user(user_id: uuid.UUID, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "Usuário não encontrado")
    await db.delete(user)
    await db.commit()


@router.post("/{user_id}/block", response_model=UserResponse)
async def block_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    """Bloqueia um usuário."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "Usuário não encontrado")
    user.status = "blocked"
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/{user_id}/unblock", response_model=UserResponse)
async def unblock_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    """Desbloqueia um usuário."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "Usuário não encontrado")
    user.status = "active"
    user.login_attempts = 0
    user.locked_until = None
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/{user_id}/reset-password")
async def admin_reset_password(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    """Admin gera token de reset de senha para um usuário."""
    from datetime import datetime, timedelta, timezone

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "Usuário não encontrado")

    token = generate_reset_token()
    user.password_reset_token = token
    user.password_reset_expires = datetime.now(timezone.utc) + timedelta(hours=1)
    user.must_change_password = True
    await db.commit()

    return {
        "message": "Token de reset gerado",
        "token": token,
        "expires_at": user.password_reset_expires,
    }


@router.get("/{user_id}/access-logs")
async def user_access_logs(
    user_id: uuid.UUID,
    limit: int = Query(50, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    """Lista logs de acesso de um usuário."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "Usuário não encontrado")

    logs = await get_user_logs(db, user_id, limit=limit, offset=offset)
    return [
        {
            "id": str(log.id),
            "action": log.action,
            "ip_address": log.ip_address,
            "user_agent": log.user_agent,
            "details": log.details,
            "created_at": log.created_at,
        }
        for log in logs
    ]
