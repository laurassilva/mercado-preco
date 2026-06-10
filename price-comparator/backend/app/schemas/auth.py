from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    username: str  # email field for OAuth2 form compatibility
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    name: str
    email: str
    role: str


class LoginBody(BaseModel):
    email: EmailStr
    password: str
