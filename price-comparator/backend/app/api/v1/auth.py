from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.schemas.auth import (
    TokenResponse, LoginBody,
    ChangePasswordBody, ForgotPasswordBody, ForgotPasswordResponse,
    ResetPasswordBody,
)
from app.schemas.user import UserResponse
from app.services.auth_service import authenticate, forgot_password, reset_password, change_password

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


@router.post("/change-password")
async def change_password_endpoint(
    body: ChangePasswordBody,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Altera a senha do usuário autenticado."""
    await change_password(current_user, body.current_password, body.new_password, db)
    return {"message": "Senha alterada com sucesso"}


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password_endpoint(
    body: ForgotPasswordBody,
    db: AsyncSession = Depends(get_db),
):
    """Solicita token de recuperação de senha."""
    result = await forgot_password(body.email, db)
    return ForgotPasswordResponse(
        message="Token de recuperação gerado",
        token=result["token"],
        expires_at=result["expires_at"],
    )


@router.post("/reset-password")
async def reset_password_endpoint(
    body: ResetPasswordBody,
    db: AsyncSession = Depends(get_db),
):
    """Redefine a senha usando token de recuperação."""
    await reset_password(body.token, body.new_password, db)
    return {"message": "Senha redefinida com sucesso"}
