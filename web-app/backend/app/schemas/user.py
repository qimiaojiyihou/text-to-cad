"""用户 Pydantic Schema"""

from pydantic import BaseModel, EmailStr, Field, ConfigDict
from datetime import datetime


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")
    email: EmailStr
    full_name: str | None = Field(None, max_length=100)


class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=128)


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = Field(None, max_length=100)
    password: str | None = Field(None, min_length=6, max_length=128)


class UserAdminUpdate(BaseModel):
    """管理员更新用户信息的 Schema"""
    email: EmailStr | None = None
    full_name: str | None = Field(None, max_length=100)
    password: str | None = Field(None, min_length=6, max_length=128)
    is_active: bool | None = None
    is_superuser: bool | None = None


class UserInDB(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime


class UserPublic(UserInDB):
    pass


class UserListResponse(BaseModel):
    """用户列表响应"""
    items: list[UserPublic]
    total: int
    skip: int
    limit: int
