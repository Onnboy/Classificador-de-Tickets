import json
from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI, status
from google import genai
from sqlmodel import Session

from app.config import settings
from app.database import criar_db_table, get_session
from app.models.ticket import Ticket
from app.schemas import TicketRequest, TicketResponse


@asynccontextmanager
async def initialization(_: FastAPI):
    criar_db_table()
    yield


app = FastAPI(lifespan=initialization)
router = APIRouter(prefix='/v1')

client = genai.Client(api_key=settings.GEMINI_API_KEY)


@app.get('/health')
def read_state():
    return {'estado': 'EM ATIVIDADE'}


@router.post(
    '/tickets/',
    status_code=status.HTTP_201_CREATED,
    response_model=TicketResponse,
)
async def create_ticket(
    ticket: TicketRequest, session: Session = Depends(get_session)
):
    try:
        prompt_ia = f'Titulo: {ticket.titulo}\nDescrição: {ticket.descricao}'

        resposta_ia = await client.aio.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt_ia,
            config={
                'response_mime_type': 'application/json',
                'system_instruction': (
                    'Voce é um classificador de tickets. '
                    'Analise o ticket e retorne obrigatoriamente um JSON '
                    "com os campos exatos: 'categoria', 'urgencia' e 'resumo'."
                    'Categorias:  Dúvida, Bug, Critico. '
                    'Urgência: Baixa, Média, Alta. '
                    'Resumo: No máximo 15 palavras. '
                ),
            },
        )
        classificacao_ia = json.loads(resposta_ia.text)

        novo_ticket = Ticket(
            titulo=ticket.titulo,
            descricao=ticket.descricao,
            categoria=classificacao_ia.get('categoria'),
            prioridade=classificacao_ia.get('urgencia'),
        )

        session.add(novo_ticket)
        session.commit()
        session.refresh(novo_ticket)

        print(f'IA classificou como: {classificacao_ia}')

    except Exception as e:
        print(f'Erro no IA: {e}')
        classificacao_ia = {
            'categoria': 'Não classificado',
            'urgencia': 'N/A',
            'resumo': 'Erro ao processar com IA',
        }

        novo_ticket = Ticket(
            titulo=ticket.titulo,
            descricao=ticket.descricao,
            categoria='Erro',
            prioridade='N/A',
        )
        session.add(novo_ticket)
        session.commit()
        session.refresh(novo_ticket)

    return {
        'mensagem': 'Ticket processado',
        'classe': classificacao_ia,
        'dados_originais': novo_ticket,
    }


app.include_router(router)
