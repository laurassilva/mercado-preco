from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.schemas.auth import TokenResponse, LoginBody
from app.schemas.user import UserResponse
from app.services.auth_service import authenticate

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginBody, db: AsyncSession = Depends(get_db)):
    """Login com email e senha."""
    return await authenticate(body.email, body.password, db)


@router.post("/token", response_model=TokenResponse, include_in_schema=False)
async def login_form(form: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    """OAuth2 form-compatible login (for Swagger UI)."""
    return await authenticate(form.username, form.password, db)


@router.get("/me", response_model=UserResponse)
async def me(current_user=Depends(get_current_user)):
    """Retorna dados do usuário autenticado."""
    return current_user
