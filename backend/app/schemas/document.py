from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentCreate(BaseModel):
    title: str
    body: str = ""
    owner_id: int | None = None


class DocumentRead(BaseModel):
    id: int
    title: str
    body: str
    owner_id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class DocumentShareCreate(BaseModel):
    expires_at: datetime | None = None


class DocumentShareRead(BaseModel):
    id: int
    document_id: int
    token: str
    created_by_user_id: int | None = None
    expires_at: datetime | None = None
    revoked_at: datetime | None = None
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
