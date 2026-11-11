from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from .models.ticket import Ticket


def _descricao_nao_vazia(valor: Optional[str]) -> Optional[str]:
    # None significa "campo não enviado" na atualização e continua válido.
    if valor is not None and not valor.strip():
        raise ValueError('A descrição não pode ser vazia')
    return valor


class TicketRequest(BaseModel):
    titulo: str = Field(..., min_length=10)
    descricao: str

    _validar_descricao = field_validator('descricao')(_descricao_nao_vazia)


class TicketUpdate(BaseModel):
    titulo: Optional[str] = Field(None, min_length=10)
    descricao: Optional[str]

    _validar_descricao = field_validator('descricao')(_descricao_nao_vazia)


class IAClassificacao(BaseModel):
    categoria: str
    urgencia: str
    resumo: str


class TicketResponse(BaseModel):
    mensagem: str
    classe: IAClassificacao
    dados_originais: Ticket


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3)
    email: EmailStr
    password: str = Field(..., min_length=6)


class UserPublic(BaseModel):
    id: int
    username: str
    email: str | None = None
    is_active: bool

    class Config:
        from_attributes = True


class TicketPublic(BaseModel):
    id: int
    titulo: str
    descricao: str
    categoria: str
    prioridade: str
    criado_em: datetime
    usuario_id: int
    atribuir_a_id: Optional[int] = None

    usuario: Optional[UserPublic] = None
    tecnico: Optional[UserPublic] = None

    class Config:
        from_attributes = True
