import unicodedata
from datetime import datetime
from typing import Annotated, Literal, Optional

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


CATEGORIAS_IA = ('Dúvida', 'Bug', 'Critico')
URGENCIAS_IA = ('Baixa', 'Média', 'Alta')


def _sem_acento_nem_caixa(texto: str) -> str:
    decomposto = unicodedata.normalize('NFKD', texto.strip().casefold())
    return ''.join(c for c in decomposto if not unicodedata.combining(c))


def _valor_canonico(valor: object, permitidos: tuple[str, ...]) -> object:
    # Aceita variações de caixa, acento e espaços ('crítico', ' MEDIA ')
    # e devolve a grafia da lista. O que não bater segue como veio e é
    # recusado pelo Literal do campo.
    if isinstance(valor, str):
        chave = _sem_acento_nem_caixa(valor)
        for permitido in permitidos:
            if _sem_acento_nem_caixa(permitido) == chave:
                return permitido
    return valor


class RespostaIA(BaseModel):
    # Entrada: o que a IA devolveu. Não usar como response_model; a
    # saída das rotas é IAClassificacao, sem estas regras.
    categoria: Literal['Dúvida', 'Bug', 'Critico']
    urgencia: Literal['Baixa', 'Média', 'Alta']
    resumo: str

    @field_validator('categoria', mode='before')
    @classmethod
    def _categoria_canonica(cls, valor):
        return _valor_canonico(valor, CATEGORIAS_IA)

    @field_validator('urgencia', mode='before')
    @classmethod
    def _urgencia_canonica(cls, valor):
        return _valor_canonico(valor, URGENCIAS_IA)


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
