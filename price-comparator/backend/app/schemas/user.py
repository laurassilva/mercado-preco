import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    name: str
    password: str
    role: str = "user"
    phone: str | None = None
    company: str | None = None
    position: str | None = None


class UserUpdate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    role: str | None = None
    is_active: bool | None = None
    password: str | None = None
    phone: str | None = None
    company: str | None = None
    position: str | None = None
    status: str | None = None


class UserResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    email: str
    name: str
    role: str
    is_active: bool
    created_at: datetime
    phone: str | None = None
    company: str | None = None
    position: str | None = None
    status: str | None = None
    last_login_at: datetime | None = None
    must_change_password: bool | None = None
    login_attempts: int | None = None
