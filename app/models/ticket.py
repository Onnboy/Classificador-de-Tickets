from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class Ticket(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    titulo: str
    descricao: str
    categoria: str
    prioridade: str
    criado_em: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
