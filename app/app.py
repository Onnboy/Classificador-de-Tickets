import json
from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI, status, HTTPException
from google import genai
from sqlmodel import Session, select
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError
from app.config import settings
from app.core.security import hash_password, get_current_user
from app.database import criar_db_table, get_session
from app.models.ticket import Ticket
from app.models.user import User
from app.schemas import TicketRequest, TicketResponse, UserCreate, UserPublic, TicketPublic
from app.core.security import get_current_user
from app.core.security import create_access_token, verify_password


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


@router.get('/tickets/', response_model=list[TicketResponse])
async def list_tickets(session: Session = Depends(get_session)):
    tickets = session.exec(select(Ticket)).all()
    return [
        {
            'mensagem': 'Ticket recuperado do histórico',
            'classe': {
                'categoria': t.categoria,
                'urgencia': t.prioridade,
                'resumo': 'Recuperado do banco',
            },
            'dados_originais': t,
        }
        for t in tickets
    ]


@router.post(
    '/users/', status_code=status.HTTP_201_CREATED, response_model=UserPublic
)
async def create_user(
    user: UserCreate, session: Session = Depends(get_session)
):
    hashed_pwd = hash_password(user.password)

    novo_usuario = User(
        username=user.username, 
        email=user.email, 
        hashed_password=hashed_pwd
    )
    try:
        session.add(novo_usuario)
        session.commit()
        session.refresh(novo_usuario)
        return novo_usuario
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Usuário ou e-mail já cadastrado no sistema"
        )


@router.post('/auth/token')
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session)
):
    user = session.exec(select(User).where(User.username == form_data.username)).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário ou senha incorretos"
        )
    
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

app.include_router(router)