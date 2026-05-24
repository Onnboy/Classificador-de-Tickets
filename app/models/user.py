from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .ticket import Ticket


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    email: str = Field(unique=True)
    hashed_password: str
    is_active: bool = Field(default=True)
    criado_em: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    # Relacionamentos (Lado "Um" da relação 1:N)
    tickets_criados: List['Ticket'] = Relationship(
        back_populates='usuario',
        sa_relationship_kwargs={
            'primaryjoin': 'Ticket.usuario_id == User.id',
            'lazy': 'selectin',
        },
    )
    tickets_atribuidos: List['Ticket'] = Relationship(
        back_populates='tecnico',
        sa_relationship_kwargs={
            'primaryjoin': 'Ticket.atribuido_a_id == User.id',
            'lazy': 'selectin',
        },
    )
