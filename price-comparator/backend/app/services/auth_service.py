from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status

from app.models.user import User
from app.core.security import verify_password, hash_password, create_access_token, generate_reset_token
from app.schemas.auth import TokenResponse
from app.schemas.user import UserCreate


async def authenticate(email: str, password: str, db: AsyncSession) -> TokenResponse:
    result = await db.execute(select(User).where(User.email == email, User.is_active == True))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
        )

    # Check if user is blocked
    if user.status == "blocked":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Conta bloqueada. Contate o administrador.",
        )

    # Check if user is temporarily locked
    now = datetime.now(timezone.utc)
    if user.locked_until and user.locked_until > now:
        raise HTTPException(
            status_code=423,
            detail="Conta temporariamente bloqueada",
        )

    # Check password
    if not verify_password(password, user.password_hash):
        user.login_attempts = (user.login_attempts or 0) + 1
        if user.login_attempts >= 5:
            user.locked_until = now + timedelta(minutes=15)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
        )

    # Success: reset counters
    user.login_attempts = 0
    user.locked_until = None
    user.last_login_at = now
    await db.commit()

    token = create_access_token(str(user.id))
    return TokenResponse(
        access_token=token,
        user_id=str(user.id),
        name=user.name,
        email=user.email,
        role=user.role,
    )


async def create_user(data: UserCreate, db: AsyncSession) -> User:
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email já cadastrado")
    user = User(
        email=data.email,
        name=data.name,
        password_hash=hash_password(data.password),
        role=data.role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def forgot_password(email: str, db: AsyncSession) -> dict:
    result = await db.execute(select(User).where(User.email == email, User.is_active == True))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    token = generate_reset_token()
    expires = datetime.now(timezone.utc) + timedelta(hours=1)
    user.password_reset_token = token
    user.password_reset_expires = expires
    await db.commit()

    return {"token": token, "expires_at": expires}


async def reset_password(token: str, new_password: str, db: AsyncSession) -> None:
    result = await db.execute(
        select(User).where(User.password_reset_token == token, User.is_active == True)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=400, detail="Token inválido")

    now = datetime.now(timezone.utc)
    if user.password_reset_expires and user.password_reset_expires < now:
        raise HTTPException(status_code=400, detail="Token expirado")

    user.password_hash = hash_password(new_password)
    user.password_reset_token = None
    user.password_reset_expires = None
    user.must_change_password = False
    await db.commit()


async def change_password(user: User, current_password: str, new_password: str, db: AsyncSession) -> None:
    if not verify_password(current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Senha atual incorreta")

    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    await db.commit()
