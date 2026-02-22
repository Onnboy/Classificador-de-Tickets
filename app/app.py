import json
import os

from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI, status
from google import genai

from .schemas import Ticket, TicketResponse

load_dotenv()
app = FastAPI()
router = APIRouter(prefix='/v1')

client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))


@app.get('/health')
def read_state():
    return {'estado': 'EM ATIVIDADE'}


@router.post(
    '/tickets/',
    status_code=status.HTTP_201_CREATED,
    response_model=TicketResponse,
)
async def create_ticket(ticket: Ticket):
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
        print(f'IA classificou como: {classificacao_ia}')

    except Exception as e:
        print(f'Erro no IA: {e}')
        classificacao_ia = {
            'categoria': 'Não classificado',
            'urgencia': 'N/A',
            'resumo': 'Erro ao processar com IA',
        }

    return {
        'mensagem': 'Ticket processado',
        'classe': classificacao_ia,
        'dados_originais': ticket,
    }


app.include_router(router)
