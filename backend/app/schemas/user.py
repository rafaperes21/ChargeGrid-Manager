import uuid

from pydantic import BaseModel, EmailStr

from app.models.enums import UserRole


class UserUpdate(BaseModel):
    full_name: str | None = None
    vehicle_model: str | None = None
    rfid_virtual_id: str | None = None
    blocked: bool | None = None


class UserRead(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: UserRole
    vehicle_model: str | None
    rfid_virtual_id: str | None
    blocked: bool

    model_config = {"from_attributes": True}
