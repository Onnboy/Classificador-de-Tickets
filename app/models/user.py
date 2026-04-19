from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    id: Optional[int] = Field(
        default=None, primary_key=True
    )
    username: str = Field(index=True, unique=True)
    email: str = Field(unique=True)
    hashed_password: str
    is_active: bool = Field(default=True)
    criado_em: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
