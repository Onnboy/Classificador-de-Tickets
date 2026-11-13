from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from google import genai
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.config import settings
from app.core.security import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.database import criar_db_table, get_session
from app.models.ticket import Ticket
from app.models.user import User
from app.schemas import (
    RespostaIA,
    TicketRequest,
    TicketResponse,
    TicketUpdate,
    TicketUpdateResponse,
    UserCreate,
    UserPublic,
)


@asynccontextmanager
async def initialization(_: FastAPI):
    criar_db_table()
    yield


app = FastAPI(lifespan=initialization)
router = APIRouter(prefix='/v1')


@app.middleware('http')
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)

    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'

    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "img-src 'self' data: https://fastapi.tiangolo.com;"
    )
    return response


client = genai.Client(api_key=settings.GEMINI_API_KEY)

INSTRUCAO_IA = (
    'Voce é um classificador de tickets. '
    'Analise o ticket e retorne obrigatoriamente um JSON '
    "com os campos exatos: 'categoria', 'urgencia' e 'resumo'."
    'Categorias:  Dúvida, Bug, Critico. '
    'Urgência: Baixa, Média, Alta. '
    'Resumo: No máximo 15 palavras. '
)


async def classificar_com_ia(titulo: str, descricao: str) -> RespostaIA | None:
    # Devolve None quando a chamada falha ou a resposta não tem o formato
    # esperado. Quem chama grava o ticket fora deste try: assim um erro
    # da IA nunca deixa a sessão do banco em estado inválido.
    try:
        resposta_ia = await client.aio.models.generate_content(
            model='gemini-2.5-flash',
            contents=f'Titulo: {titulo}\nDescrição: {descricao}',
            config={
                'response_mime_type': 'application/json',
                'system_instruction': INSTRUCAO_IA,
            },
        )
        return RespostaIA.model_validate_json(resposta_ia.text)
    except Exception as e:
        print(f'Erro no IA: {e}')
        return None


@app.get('/health/')
def read_state():
    return {'estado': 'EM ATIVIDADE'}


@router.post(
    '/tickets/',
    status_code=status.HTTP_201_CREATED,
    response_model=TicketResponse,
)
async def create_ticket(
    ticket: TicketRequest,
    session: Session = Depends(get_session),
    current_user_username: str = Depends(get_current_user),
):

    user_db = session.exec(
        select(User).where(User.username == current_user_username)
    ).first()

    if not user_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Usuario do token não encontrado no sistema!',
        )

    classificacao = await classificar_com_ia(ticket.titulo, ticket.descricao)

    if classificacao:
        classificacao_ia = classificacao.model_dump()
        categoria = classificacao.categoria
        prioridade = classificacao.urgencia
        print(f'IA classificou como: {classificacao_ia}')
    else:
        classificacao_ia = {
            'categoria': 'Não classificado',
            'urgencia': 'N/A',
            'resumo': 'Erro ao processar com IA',
        }
        categoria = 'Erro'
        prioridade = 'N/A'

    novo_ticket = Ticket(
        titulo=ticket.titulo,
        descricao=ticket.descricao,
        categoria=categoria,
        prioridade=prioridade,
        usuario_id=user_db.id,
    )

    session.add(novo_ticket)
    session.commit()
    session.refresh(novo_ticket)

    return {
        'mensagem': 'Ticket processado',
        'classe': classificacao_ia,
        'dados_originais': novo_ticket,
    }


@router.put('/tickets/{id}', response_model=TicketUpdateResponse)
async def update_ticket(
    id: int,
    ticket: TicketUpdate,
    session: Session = Depends(get_session),
    current_user_username: str = Depends(get_current_user),
):
    user_db = session.exec(
        select(User).where(User.username == current_user_username)
    ).first()

    if not user_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Usuario do token não encontrado no sistema!',
        )

    ticket_bd = session.get(Ticket, id)

    if not ticket_bd:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Ticket não encontrado',
        )

    if ticket_bd.usuario_id != user_db.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Sem permissão para editar este ticket',
        )

    # A classificação só é refeita quando título ou descrição mudam de
    # fato: os dois entram no prompt, e cada chamada ao Gemini é paga e
    # sobrescreve categoria e prioridade.
    titulo_mudou = (
        ticket.titulo is not None and ticket.titulo != ticket_bd.titulo
    )
    descricao_mudou = (
        ticket.descricao is not None
        and ticket.descricao != ticket_bd.descricao
    )

    if titulo_mudou:
        ticket_bd.titulo = ticket.titulo

    if descricao_mudou:
        ticket_bd.descricao = ticket.descricao

    if titulo_mudou or descricao_mudou:
        classificacao = await classificar_com_ia(
            ticket_bd.titulo, ticket_bd.descricao
        )

        if classificacao:
            ticket_bd.categoria = classificacao.categoria
            ticket_bd.prioridade = classificacao.urgencia
            print(f'IA reclassificou como: {classificacao.model_dump()}')
        else:
            ticket_bd.categoria = 'Erro'
            ticket_bd.prioridade = 'N/A'

    session.add(ticket_bd)
    session.commit()
    session.refresh(ticket_bd)

    return ticket_bd


@router.get('/tickets/', response_model=list[TicketResponse])
async def list_tickets(
    session: Session = Depends(get_session),
    current_username: str = Depends(get_current_user),
):

    user_db = session.exec(
        select(User).where(User.username == current_username)
    ).first()

    if not user_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Usuário não encontrado',
        )

    tickets = session.exec(
        select(Ticket).where(Ticket.usuario_id == user_db.id)
    ).all()

    return [
        {
            'mensagem': 'Ticket recuperado do histórico',
            'classe': {
                'categoria': t.categoria,
                'urgencia': t.prioridade,
                'resumo': 'Recuperado do banco',
            },
            'dados_originais': {
                'id': t.id,
                'titulo': t.titulo,
                'descricao': t.descricao,
                'categoria': t.categoria,
                'prioridade': t.prioridade,
                'criado_em': t.criado_em,
            },
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
        username=user.username, email=user.email, hashed_password=hashed_pwd
    )
    try:
        session.add(novo_usuario)
        session.commit()
        session.refresh(novo_usuario)

        return UserPublic(
            id=novo_usuario.id,
            username=novo_usuario.username,
            email='hidden@system.test',
            is_active=novo_usuario.is_active,
            criado_em=novo_usuario.criado_em,
        )
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Usuário ou e-mail já cadastrado no sistema',
        )


@router.post('/auth/token/')
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session),
):
    user = session.exec(
        select(User).where(User.username == form_data.username)
    ).first()

    if not user or not verify_password(
        form_data.password, user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Usuário ou senha incorretos',
        )

    access_token = create_access_token(data={'sub': user.username})
    return {'access_token': access_token, 'token_type': 'bearer'}


app.include_router(router)
