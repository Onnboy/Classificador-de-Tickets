from datetime import datetime
from typing import Annotated, Optional

from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    StringConstraints,
    field_validator,
)

from .models.ticket import Ticket


def _descricao_nao_vazia(valor: Optional[str]) -> Optional[str]:
    # None significa "campo não enviado" na atualização e continua válido.
    if valor is not None and not valor.strip():
        raise ValueError('A descrição não pode ser vazia')
    return valor


# O tamanho mínimo vale para o título já sem os espaços das pontas. Com
# um min_length simples, dez espaços passavam na validação.
Titulo = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=10)
]


class TicketRequest(BaseModel):
    titulo: Titulo
    descricao: str

    _validar_descricao = field_validator('descricao')(_descricao_nao_vazia)


class TicketUpdate(BaseModel):
    titulo: Optional[Titulo] = None
    descricao: Optional[str] = None

    _validar_descricao = field_validator('descricao')(_descricao_nao_vazia)


class TicketUpdateResponse(BaseModel):
    # Saída do PUT: sem as regras de entrada, para que tickets gravados
    # antes da validação continuem podendo ser devolvidos.
    titulo: str
    descricao: str


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
