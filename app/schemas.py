from pydantic import BaseModel, Field


class Ticket(BaseModel):
    titulo: str = Field(..., min_length=10)
    descricao: str


class TicketResponse(BaseModel):
    mensagem: str
    classe: str
    dados_originais: Ticket
