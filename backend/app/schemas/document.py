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
