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
        resposta_ia = await client.aio.models.generate_content(
            model='gemini-2.5-flash',
            contents=f"Ticket: {ticket.titulo}",
            config={
                'system_instruction': 'Você é um classificador de tickets. '
                'Responda APENAS com uma palavra: Dúvida, Bug ou Critico.'
            }
        )
        categoria = resposta_ia.text.strip().replace(".", "").capitalize()
        print(f'IA classificou como: {categoria}')

    except Exception as e:
        print(f'Erro no IA: {e}')
        categoria = 'Não classificado (Erro na IA)'

    return {
        'mensagem': 'Ticket processado',
        'classe': categoria,
        'dados_originais': ticket,
    }


app.include_router(router)
