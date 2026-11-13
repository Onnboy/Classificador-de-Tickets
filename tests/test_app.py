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
async def test_update_ticket_sucesso():
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

        db_ticket = Ticket(
            id=1,
            titulo='Titulo Antigo do Ticket',
            descricao='Descricao antiga do ticket',
            categoria='Dúvida',
            prioridade='Baixa',
            usuario_id=1,
        )
        session.add(db_ticket)
        session.commit()

    targ = 'app.app.client.aio.models.generate_content'
    mock_response = AsyncMock()
    mock_response.text = (
        '{"categoria": "Bug","urgencia": "Alta", "resumo": "Atualizado"}'
    )

    with patch(targ, return_value=mock_response):
        tp = ASGITransport(app=app)
        async with AsyncClient(transport=tp, base_url='http://test') as ac:
            payload = {
                'titulo': 'Novo Titulo com mais de 10 caracteres',
                'descricao': 'Nova descricao atualizada',
            }
            response = await ac.put('/v1/tickets/1', json=payload)

    assert response.status_code == HTTPStatus.OK

    with Session(engine_test) as session:
        ticket = session.get(Ticket, 1)
        assert ticket.titulo == payload['titulo']
        assert ticket.categoria == 'Bug'

    app.dependency_overrides.clear()
    SQLModel.metadata.drop_all(engine_test)


@pytest.mark.anyio
async def test_update_ticket_sem_permissao():
    SQLModel.metadata.create_all(engine_test)
    app.dependency_overrides[get_session] = sbrescrever_get_session
    app.dependency_overrides[get_current_user] = lambda: 'usuario_b'

    with Session(engine_test) as session:
        dono = User(
            id=1,
            username='usr_teste',
            email='dono@test.com',
            hashed_password='fake',
        )
        fake_dono = User(
            id=2,
            username='usuario_b',
            email='b@test.com',
            hashed_password='fake',
        )
        session.add(dono)
        session.add(fake_dono)

        other_ticket = Ticket(
            id=5,
            titulo='Ticket do Dono',
            descricao='...',
            categoria='Dúvida',
            prioridade='Baixa',
            usuario_id=1,
        )
        session.add(other_ticket)
        session.commit()

    tp = ASGITransport(app=app)
    async with AsyncClient(transport=tp, base_url='http://test') as ac:
        payload = {
            'titulo': 'Teste bypass',
            'descricao': 'Teste de atualização ticket sem permissão',
        }
        response = await ac.put('/v1/tickets/5', json=payload)

    assert response.status_code == HTTPStatus.FORBIDDEN

    app.dependency_overrides.clear()
    SQLModel.metadata.drop_all(engine_test)


@pytest.mark.anyio
async def test_update_ticket_nao_encontrado():
    SQLModel.metadata.create_all(engine_test)
    app.dependency_overrides[get_session] = sbrescrever_get_session
    app.dependency_overrides[get_current_user] = lambda: 'usr_teste'

    with Session(engine_test) as session:
        db_user = User(
            id=1,
            username='usr_teste',
            email='usr@test.com',
            hashed_password='fake',
        )
        session.add(db_user)
        session.commit()

    tp = ASGITransport(app=app)
    async with AsyncClient(transport=tp, base_url='http://test') as ac:
        payload = {
            'titulo': 'Titulo valido para ticket invalida',
            'descricao': 'Descricao valida para ticket invalido',
        }
        response = await ac.put('/v1/tickets/999', json=payload)

    assert response.status_code == HTTPStatus.NOT_FOUND

    app.dependency_overrides.clear()
    SQLModel.metadata.drop_all(engine_test)


@pytest.mark.anyio
async def test_update_ticket_sem_token():
    tp = ASGITransport(app=app)
    async with AsyncClient(transport=tp, base_url='http://test') as ac:
        payload = {'titulo': 'Nao vai passar de qualquer forma'}
        response = await ac.put('/v1/tickets/1', json=payload)

    assert response.status_code == HTTPStatus.UNAUTHORIZED


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
    assert data['email'] == 'hidden@system.test'
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


@pytest.mark.anyio
@pytest.mark.parametrize('descricao', ['', '   ', '\n\t'])
async def test_add_ticket_descricao_vazia_deve_falhar(descricao):
    SQLModel.metadata.create_all(engine_test)
    app.dependency_overrides[get_session] = sbrescrever_get_session
    app.dependency_overrides[get_current_user] = lambda: 'usr_teste'

    try:
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

        with patch(targ, return_value=mock_response) as mock_ai:
            tp = ASGITransport(app=app)
            async with AsyncClient(transport=tp, base_url='http://test') as ac:
                payload = {
                    'titulo': 'Titulo valido com mais de 10 caracteres',
                    'descricao': descricao,
                }
                response = await ac.post('/v1/tickets/', json=payload)

        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
        assert response.json()['detail'][0]['loc'] == ['body', 'descricao']
        mock_ai.assert_not_called()

        with Session(engine_test) as session:
            assert session.exec(select(Ticket)).first() is None
    finally:
        app.dependency_overrides.clear()
        SQLModel.metadata.drop_all(engine_test)


@pytest.mark.anyio
async def test_update_ticket_descricao_vazia_deve_falhar():
    SQLModel.metadata.create_all(engine_test)
    app.dependency_overrides[get_session] = sbrescrever_get_session
    app.dependency_overrides[get_current_user] = lambda: 'usr_teste'

    try:
        with Session(engine_test) as session:
            db_user = User(
                id=1,
                username='usr_teste',
                email='usr_teste@system.test',
                hashed_password='fake',
            )
            session.add(db_user)

            db_ticket = Ticket(
                id=1,
                titulo='Titulo Antigo do Ticket',
                descricao='Descricao antiga do ticket',
                categoria='Dúvida',
                prioridade='Baixa',
                usuario_id=1,
            )
            session.add(db_ticket)
            session.commit()

        targ = 'app.app.client.aio.models.generate_content'
        mock_response = AsyncMock()
        mock_response.text = (
            '{"categoria": "Bug","urgencia": "Alta", "resumo": "Atualizado"}'
        )

        with patch(targ, return_value=mock_response) as mock_ai:
            tp = ASGITransport(app=app)
            async with AsyncClient(transport=tp, base_url='http://test') as ac:
                payload = {'descricao': '   '}
                response = await ac.put('/v1/tickets/1', json=payload)

        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
        assert response.json()['detail'][0]['loc'] == ['body', 'descricao']
        mock_ai.assert_not_called()

        with Session(engine_test) as session:
            ticket = session.get(Ticket, 1)
            assert ticket.descricao == 'Descricao antiga do ticket'
    finally:
        app.dependency_overrides.clear()
        SQLModel.metadata.drop_all(engine_test)


@pytest.mark.anyio
@pytest.mark.parametrize(
    'payload',
    [
        {'titulo': 'Novo titulo para ticket antigo'},
        {'titulo': 'Novo titulo para ticket antigo', 'descricao': None},
    ],
    ids=['sem_campo_descricao', 'descricao_null'],
)
async def test_update_so_titulo_de_ticket_antigo_com_descricao_vazia(payload):
    SQLModel.metadata.create_all(engine_test)
    app.dependency_overrides[get_session] = sbrescrever_get_session
    app.dependency_overrides[get_current_user] = lambda: 'usr_teste'

    try:
        with Session(engine_test) as session:
            db_user = User(
                id=1,
                username='usr_teste',
                email='usr_teste@system.test',
                hashed_password='fake',
            )
            session.add(db_user)

            # Ticket gravado antes da validação existir: descrição vazia.
            db_ticket = Ticket(
                id=1,
                titulo='Titulo Antigo do Ticket',
                descricao='',
                categoria='Dúvida',
                prioridade='Baixa',
                usuario_id=1,
            )
            session.add(db_ticket)
            session.commit()

        targ = 'app.app.client.aio.models.generate_content'
        mock_response = AsyncMock()
        mock_response.text = (
            '{"categoria": "Bug","urgencia": "Alta", "resumo": "Atualizado"}'
        )

        with patch(targ, return_value=mock_response):
            # raise_app_exceptions=False: erro interno vira resposta 500,
            # como em produção, em vez de exceção dentro do teste.
            tp = ASGITransport(app=app, raise_app_exceptions=False)
            async with AsyncClient(transport=tp, base_url='http://test') as ac:
                response = await ac.put('/v1/tickets/1', json=payload)

        assert response.status_code == HTTPStatus.OK
        assert response.json()['titulo'] == payload['titulo']

        with Session(engine_test) as session:
            ticket = session.get(Ticket, 1)
            assert ticket.titulo == payload['titulo']
            assert not ticket.descricao
    finally:
        app.dependency_overrides.clear()
        SQLModel.metadata.drop_all(engine_test)


def _semear_usuario_e_ticket_classificado():
    with Session(engine_test) as session:
        db_user = User(
            id=1,
            username='usr_teste',
            email='usr_teste@system.test',
            hashed_password='fake',
        )
        session.add(db_user)

        db_ticket = Ticket(
            id=1,
            titulo='Titulo Antigo do Ticket',
            descricao='Descricao antiga do ticket',
            categoria='Dúvida',
            prioridade='Baixa',
            usuario_id=1,
        )
        session.add(db_ticket)
        session.commit()


async def _put_ticket_com_ia_simulada(payload):
    targ = 'app.app.client.aio.models.generate_content'
    mock_response = AsyncMock()
    mock_response.text = (
        '{"categoria": "Bug","urgencia": "Alta", "resumo": "Atualizado"}'
    )

    with patch(targ, return_value=mock_response) as mock_ai:
        tp = ASGITransport(app=app)
        async with AsyncClient(transport=tp, base_url='http://test') as ac:
            response = await ac.put('/v1/tickets/1', json=payload)

    return response, mock_ai


@pytest.mark.anyio
@pytest.mark.parametrize(
    'payload',
    [
        {},
        {'titulo': 'Titulo Antigo do Ticket'},
        {'descricao': 'Descricao antiga do ticket'},
        {
            'titulo': 'Titulo Antigo do Ticket',
            'descricao': 'Descricao antiga do ticket',
        },
        {'titulo': '  Titulo Antigo do Ticket \n'},
    ],
    ids=[
        'corpo_vazio',
        'titulo_igual',
        'descricao_igual',
        'ambos_iguais',
        'titulo_igual_com_espacos_nas_pontas',
    ],
)
async def test_update_sem_mudar_titulo_nem_descricao_nao_reclassifica(
    payload,
):
    SQLModel.metadata.create_all(engine_test)
    app.dependency_overrides[get_session] = sbrescrever_get_session
    app.dependency_overrides[get_current_user] = lambda: 'usr_teste'

    try:
        _semear_usuario_e_ticket_classificado()

        response, mock_ai = await _put_ticket_com_ia_simulada(payload)

        assert response.status_code == HTTPStatus.OK
        mock_ai.assert_not_called()

        with Session(engine_test) as session:
            ticket = session.get(Ticket, 1)
            assert ticket.titulo == 'Titulo Antigo do Ticket'
            assert ticket.descricao == 'Descricao antiga do ticket'
            assert ticket.categoria == 'Dúvida'
            assert ticket.prioridade == 'Baixa'
    finally:
        app.dependency_overrides.clear()
        SQLModel.metadata.drop_all(engine_test)


@pytest.mark.anyio
@pytest.mark.parametrize(
    'payload',
    [
        {'titulo': 'Novo titulo sem mexer na descricao'},
        {'descricao': 'Nova descricao sem mexer no titulo'},
        {
            'titulo': 'Novo titulo sem mexer na descricao',
            'descricao': 'Descricao antiga do ticket',
        },
    ],
    ids=['so_titulo', 'so_descricao', 'titulo_novo_e_descricao_igual'],
)
async def test_update_mudando_titulo_ou_descricao_reclassifica(payload):
    SQLModel.metadata.create_all(engine_test)
    app.dependency_overrides[get_session] = sbrescrever_get_session
    app.dependency_overrides[get_current_user] = lambda: 'usr_teste'

    try:
        _semear_usuario_e_ticket_classificado()

        response, mock_ai = await _put_ticket_com_ia_simulada(payload)

        assert response.status_code == HTTPStatus.OK
        mock_ai.assert_awaited_once()

        with Session(engine_test) as session:
            ticket = session.get(Ticket, 1)
            assert ticket.titulo == payload.get(
                'titulo', 'Titulo Antigo do Ticket'
            )
            assert ticket.descricao == payload.get(
                'descricao', 'Descricao antiga do ticket'
            )
            assert ticket.categoria == 'Bug'
            assert ticket.prioridade == 'Alta'
    finally:
        app.dependency_overrides.clear()
        SQLModel.metadata.drop_all(engine_test)


# Todos têm 10 caracteres ou mais contando os espaços, mas menos de 10
# de conteúdo: o tamanho mínimo vale para o título já sem as pontas.
TITULOS_SEM_CONTEUDO_MINIMO = [
    ' ' * 12,
    '\n\t' * 6,
    'a' + ' ' * 9,
    ' ' * 9 + 'curto',
]
IDS_TITULOS_SEM_CONTEUDO_MINIMO = [
    'espacos',
    'quebras_e_tabs',
    'uma_letra_e_espacos',
    'curto_com_espacos_antes',
]


@pytest.mark.anyio
@pytest.mark.parametrize(
    'titulo', TITULOS_SEM_CONTEUDO_MINIMO, ids=IDS_TITULOS_SEM_CONTEUDO_MINIMO
)
async def test_add_ticket_titulo_sem_conteudo_minimo_deve_falhar(titulo):
    SQLModel.metadata.create_all(engine_test)
    app.dependency_overrides[get_session] = sbrescrever_get_session
    app.dependency_overrides[get_current_user] = lambda: 'usr_teste'

    try:
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

        with patch(targ, return_value=mock_response) as mock_ai:
            tp = ASGITransport(app=app)
            async with AsyncClient(transport=tp, base_url='http://test') as ac:
                payload = {
                    'titulo': titulo,
                    'descricao': 'Descricao valida do ticket',
                }
                response = await ac.post('/v1/tickets/', json=payload)

        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
        assert response.json()['detail'][0]['loc'] == ['body', 'titulo']
        mock_ai.assert_not_called()

        with Session(engine_test) as session:
            assert session.exec(select(Ticket)).first() is None
    finally:
        app.dependency_overrides.clear()
        SQLModel.metadata.drop_all(engine_test)


@pytest.mark.anyio
@pytest.mark.parametrize(
    'titulo', TITULOS_SEM_CONTEUDO_MINIMO, ids=IDS_TITULOS_SEM_CONTEUDO_MINIMO
)
async def test_update_ticket_titulo_sem_conteudo_minimo_deve_falhar(titulo):
    SQLModel.metadata.create_all(engine_test)
    app.dependency_overrides[get_session] = sbrescrever_get_session
    app.dependency_overrides[get_current_user] = lambda: 'usr_teste'

    try:
        _semear_usuario_e_ticket_classificado()

        response, mock_ai = await _put_ticket_com_ia_simulada({
            'titulo': titulo
        })

        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
        assert response.json()['detail'][0]['loc'] == ['body', 'titulo']
        mock_ai.assert_not_called()

        with Session(engine_test) as session:
            ticket = session.get(Ticket, 1)
            assert ticket.titulo == 'Titulo Antigo do Ticket'
            assert ticket.descricao == 'Descricao antiga do ticket'
            assert ticket.categoria == 'Dúvida'
            assert ticket.prioridade == 'Baixa'
    finally:
        app.dependency_overrides.clear()
        SQLModel.metadata.drop_all(engine_test)


ALVO_IA = 'app.app.client.aio.models.generate_content'


def _semear_usuario(is_active=True, senha='fake'):
    with Session(engine_test) as session:
        session.add(
            User(
                id=1,
                username='usr_teste',
                email='usr_teste@system.test',
                hashed_password=senha,
                is_active=is_active,
            )
        )
        session.commit()


async def _post_ticket_com_ia_simulada(texto_ia, headers=None):
    mock_response = AsyncMock()
    mock_response.text = texto_ia

    with patch(ALVO_IA, return_value=mock_response) as mock_ai:
        # raise_app_exceptions=False: erro interno vira resposta 500,
        # como em produção, em vez de exceção dentro do teste.
        tp = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=tp, base_url='http://test') as ac:
            payload = {
                'titulo': 'Titulo valido com mais de 10 caracteres',
                'descricao': 'Descricao valida',
            }
            response = await ac.post(
                '/v1/tickets/', json=payload, headers=headers
            )

    return response, mock_ai


@pytest.mark.anyio
@pytest.mark.parametrize(
    'texto_ia',
    [
        '{"foo": "bar"}',
        '{"categoria": "Bug", "resumo": "sem urgencia"}',
        '{"categoria": "Qualquer", "urgencia": "Urgentíssima", "resumo": "x"}',
        '{"categoria": null, "urgencia": null, "resumo": null}',
        'isto não é json',
        '[]',
    ],
    ids=[
        'sem_campos',
        'sem_urgencia',
        'valores_fora_da_lista',
        'campos_nulos',
        'nao_e_json',
        'json_que_nao_e_objeto',
    ],
)
async def test_add_ticket_resposta_invalida_da_ia_salva_como_erro(texto_ia):
    SQLModel.metadata.create_all(engine_test)
    app.dependency_overrides[get_session] = sbrescrever_get_session
    app.dependency_overrides[get_current_user] = lambda: 'usr_teste'

    try:
        _semear_usuario()

        response, _ = await _post_ticket_com_ia_simulada(texto_ia)

        assert response.status_code == HTTPStatus.CREATED
        assert response.json()['classe'] == {
            'categoria': 'Não classificado',
            'urgencia': 'N/A',
            'resumo': 'Erro ao processar com IA',
        }

        with Session(engine_test) as session:
            tickets = session.exec(select(Ticket)).all()
            assert len(tickets) == 1
            assert tickets[0].categoria == 'Erro'
            assert tickets[0].prioridade == 'N/A'
    finally:
        app.dependency_overrides.clear()
        SQLModel.metadata.drop_all(engine_test)


@pytest.mark.anyio
async def test_add_ticket_normaliza_variacoes_da_resposta_da_ia():
    SQLModel.metadata.create_all(engine_test)
    app.dependency_overrides[get_session] = sbrescrever_get_session
    app.dependency_overrides[get_current_user] = lambda: 'usr_teste'

    try:
        _semear_usuario()

        response, _ = await _post_ticket_com_ia_simulada(
            '{"categoria": "crítico", "urgencia": " MEDIA ", "resumo": "x"}'
        )

        assert response.status_code == HTTPStatus.CREATED
        assert response.json()['classe']['categoria'] == 'Critico'
        assert response.json()['classe']['urgencia'] == 'Média'

        with Session(engine_test) as session:
            ticket = session.exec(select(Ticket)).one()
            assert ticket.categoria == 'Critico'
            assert ticket.prioridade == 'Média'
    finally:
        app.dependency_overrides.clear()
        SQLModel.metadata.drop_all(engine_test)


@pytest.mark.anyio
async def test_update_ticket_resposta_invalida_da_ia_salva_como_erro():
    SQLModel.metadata.create_all(engine_test)
    app.dependency_overrides[get_session] = sbrescrever_get_session
    app.dependency_overrides[get_current_user] = lambda: 'usr_teste'

    try:
        _semear_usuario_e_ticket_classificado()

        mock_response = AsyncMock()
        mock_response.text = '{"foo": "bar"}'

        with patch(ALVO_IA, return_value=mock_response):
            tp = ASGITransport(app=app, raise_app_exceptions=False)
            async with AsyncClient(
                transport=tp, base_url='http://test'
            ) as ac:
                response = await ac.put(
                    '/v1/tickets/1',
                    json={'titulo': 'Novo titulo que muda o ticket'},
                )

        assert response.status_code == HTTPStatus.OK

        with Session(engine_test) as session:
            ticket = session.get(Ticket, 1)
            assert ticket.titulo == 'Novo titulo que muda o ticket'
            assert ticket.categoria == 'Erro'
            assert ticket.prioridade == 'N/A'
    finally:
        app.dependency_overrides.clear()
        SQLModel.metadata.drop_all(engine_test)
