from http import HTTPStatus
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient, Response
from sqlmodel import Session, SQLModel, create_engine, select

from app.app import app
from app.core.security import get_current_user
from app.database import get_session
from app.models.ticket import Ticket
from app.models.user import User

engine_test = create_engine(
    'sqlite://', connect_args={'check_same_thread': False}
)


def sbrescrever_get_session():
    with Session(engine_test) as session:
        yield session


def test_health_app():
    client = TestClient(app)
    response = client.get('/health/')

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'estado': 'EM ATIVIDADE'}


@pytest.mark.anyio
async def test_add_ticket_app_sucesso():
    SQLModel.metadata.create_all(engine_test)
    app.dependency_overrides[get_session] = sbrescrever_get_session
    app.dependency_overrides[get_current_user] = lambda: 'usr_teste'

    with Session(engine_test) as session:
        db_user = User(
            id=1,
            username='usr_teste',
            email='usr_teste@system.test',
            hashed_password='fake',
        )
        session.add(db_user)
        session.commit()

    targ = 'app.app.client.aio.models.generate_content'
    mock_response = AsyncMock()
    mock_response.text = (
        '{"categoria": "Dúvida","urgencia": "Baixa", "resumo": "Teste"}'
    )

    with patch(targ, return_value=mock_response):
        tp = ASGITransport(app=app)
        async with AsyncClient(transport=tp, base_url='http://test') as ac:
            payload = {
                'titulo': 'Teste com titulo com + de 10 carcterers',
                'descricao': 'Descrição técnica de teste de Sucesso',
            }
            response = await ac.post('/v1/tickets/', json=payload)

    data = response.json()
    assert response.status_code == HTTPStatus.CREATED
    assert 'id' in data['dados_originais']
    assert 'criado_em' in data['dados_originais']
    assert data['classe']['categoria'] == 'Dúvida'

    with Session(engine_test) as session:
        search = select(Ticket).where(Ticket.titulo == payload['titulo'])
        ticket = session.exec(search).first()

        assert ticket is not None
        assert ticket.id == 1
        assert ticket.categoria == 'Dúvida'
        assert ticket.usuario_id == 1

    app.dependency_overrides.clear()
    SQLModel.metadata.drop_all(engine_test)


@pytest.mark.anyio
async def test_add_ticket_ai_falha():
    SQLModel.metadata.create_all(engine_test)
    app.dependency_overrides[get_session] = sbrescrever_get_session
    app.dependency_overrides[get_current_user] = lambda: 'usr_teste'

    with Session(engine_test) as session:
        db_user = User(
            id=1,
            username='usr_teste',
            email='usr_teste@system.test',
            hashed_password='fake',
        )
        session.add(db_user)
        session.commit()

    target = 'app.app.client.aio.models.generate_content'
    with patch(target, new_callable=AsyncMock) as mock_ai:
        mock_ai.side_effect = Exception('Erro de conexão com o Google')

        tp = ASGITransport(app=app)
        async with AsyncClient(transport=tp, base_url='http://test') as ac:
            payload = {
                'titulo': 'Falha na impressora',
                'descricao': 'Não liga',
            }
            response = await ac.post('/v1/tickets/', json=payload)

    assert response.status_code == HTTPStatus.CREATED
    assert response.json()['classe']['categoria'] == 'Não classificado'

    with Session(engine_test) as session:
        ticket = session.exec(select(Ticket)).first()
        assert ticket is not None
        assert ticket.categoria == 'Erro'
        assert ticket.usuario_id == 1

    app.dependency_overrides.clear()
    SQLModel.metadata.drop_all(engine_test)


@pytest.mark.anyio
async def test_add_ticket_app_error():
    app.dependency_overrides[get_current_user] = lambda: 'usr_teste'

    client = TestClient(app)
    response = client.post('/v1/tickets/')

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_get_tickets_sucesso():
    SQLModel.metadata.create_all(engine_test)
    app.dependency_overrides[get_session] = sbrescrever_get_session
    app.dependency_overrides[get_current_user] = lambda: 'usr_teste'

    with Session(engine_test) as session:
        db_user = User(
            id=1,
            username='usr_teste',
            email='usr_teste@system.test',
            hashed_password='fake',
        )
        session.add(db_user)
        session.commit()

    tp = ASGITransport(app=app)
    async with AsyncClient(transport=tp, base_url='http://test') as ac:
        response: Response = await ac.get('/v1/tickets/')

        assert response.status_code == HTTPStatus.OK
        assert isinstance(response.json(), list)

    app.dependency_overrides.clear()
    SQLModel.metadata.drop_all(engine_test)


@pytest.mark.anyio
async def test_create_user_sucesso():
    SQLModel.metadata.create_all(engine_test)
    app.dependency_overrides[get_session] = sbrescrever_get_session

    tp = ASGITransport(app=app)
    async with AsyncClient(transport=tp, base_url='http://test') as ac:
        payload = {
            'username': 'testuser',
            'email': 'testuser@system.com',
            'password': 'password123',
        }
        response = await ac.post('/v1/users/', json=payload)

    data = response.json()
    assert response.status_code == HTTPStatus.CREATED
    assert data['username'] == 'testuser'
    assert data['email'] == "hidden@system.test"
    assert 'id' in data
    assert 'password' not in data
    assert 'hashed_password' not in data

    with Session(engine_test) as session:
        user = session.exec(
            select(User).where(User.username == 'testuser')
        ).first()
        assert user is not None
        assert user.hashed_password != 'password123'
        assert user.hashed_password.startswith('$2b$')

    app.dependency_overrides.clear()
    SQLModel.metadata.drop_all(engine_test)


@pytest.mark.anyio
async def test_get_tickets_sem_token_deve_falhar():
    tp = ASGITransport(app=app)
    async with AsyncClient(transport=tp, base_url='http://test') as ac:
        response = await ac.get('/v1/tickets/')

        assert response.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.anyio
async def test_middleware_security_headers():
    tp = ASGITransport(app=app)
    async with AsyncClient(transport=tp, base_url='http://test') as ac:
        response = await ac.get('/health/')

        assert response.headers.get('X-XSS-Protection') == '1; mode=block'
        assert response.headers.get('X-Content-Type-Options') == 'nosniff'
        assert response.headers.get('X-Frame-Options') == 'DENY'


@pytest.mark.anyio
async def test_list_tickets_usuario_nao_encontrado_deve_falhar():
    SQLModel.metadata.create_all(engine_test)
    app.dependency_overrides[get_session] = sbrescrever_get_session
    app.dependency_overrides[get_current_user] = lambda: 'usuario_fantasma'

    tp = ASGITransport(app=app)
    async with AsyncClient(transport=tp, base_url='http://test') as ac:
        response = await ac.get('/v1/tickets/')

        assert response.status_code == HTTPStatus.NOT_FOUND
        assert response.json()['detail'] == 'Usuário não encontrado'

    app.dependency_overrides.clear()
    SQLModel.metadata.drop_all(engine_test)
