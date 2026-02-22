from pydantic import BaseModel, Field


class Ticket(BaseModel):
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
