from pydantic import BaseModel, EmailStr, Field

from .models.ticket import Ticket


class TicketRequest(BaseModel):
    titulo: str = Field(..., min_length=10)
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
    email: EmailStr
    is_active: bool

    class Config:
        from_attributes = True
