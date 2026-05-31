"""生成记录 Pydantic Schema"""

from pydantic import BaseModel, ConfigDict
from datetime import datetime


class GenerationRecordBase(BaseModel):
    model_id: str
    prompt: str
    status: str
    message: str | None = None


class GenerationRecordCreate(GenerationRecordBase):
    user_id: int


class GenerationRecordUpdate(BaseModel):
    status: str | None = None
    message: str | None = None
    py_path: str | None = None
    step_path: str | None = None
    glb_path: str | None = None


class GenerationRecordInDB(GenerationRecordBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    py_path: str | None = None
    step_path: str | None = None
    glb_path: str | None = None
    created_at: datetime
    updated_at: datetime


class GenerationRecordListResponse(BaseModel):
    items: list[GenerationRecordInDB]
    total: int
    skip: int
    limit: int


class GenerationRecordWithUser(GenerationRecordInDB):
    username: str | None = None
    email: str | None = None


class GenerationRecordWithUserListResponse(BaseModel):
    items: list[GenerationRecordWithUser]
    total: int
    skip: int
    limit: int
