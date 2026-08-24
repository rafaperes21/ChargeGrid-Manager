import uuid

from pydantic import BaseModel, EmailStr

from app.models.enums import UserRole


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: UserRole = UserRole.customer


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class GoogleAuthRequest(BaseModel):
    id_token: str


class UserRead(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: UserRole
    blocked: bool

    model_config = {"from_attributes": True}
