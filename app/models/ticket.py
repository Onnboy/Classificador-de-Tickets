from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .user import User


class Ticket(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    titulo: str
    descricao: str
    categoria: str
    prioridade: str
    criado_em: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    usuario_id: int = Field(foreign_key='user.id', nullable=False)

    atribuido_a_id: Optional[int] = Field(
        default=None, foreign_key='user.id', nullable=True
    )

    usuario: 'User' = Relationship(
        back_populates='tickets_criados',
        sa_relationship_kwargs={'foreign_keys': '[Ticket.usuario_id]'},
    )

    tecnico: Optional['User'] = Relationship(
        back_populates='tickets_atribuidos',
        sa_relationship_kwargs={'foreign_keys': '[Ticket.atribuido_a_id]'},
    )
