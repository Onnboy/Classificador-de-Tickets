from http import HTTPStatus
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from app.app import app


def test_health_app():
    client = TestClient(app)
    response = client.get('/health')

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'estado': 'EM ATIVIDADE'}


@pytest.mark.anyio
async def test_add_ticket_app_sucesso():
    tp = ASGITransport(app=app)
    async with AsyncClient(transport=tp, base_url='http://test') as ac:
        payload = {
            'titulo': 'Teste com titulo com + de 10 carcterers',
            'descricao': 'Descrição técnica de teste de Sucesso',
        }
        response = await ac.post('/v1/tickets/', json=payload)

    assert response.status_code == HTTPStatus.CREATED
    assert 'categoria' in response.json()['classe']
    assert 'urgencia' in response.json()['classe']


@pytest.mark.anyio
async def test_add_ticket_ai_falha():
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


def test_add_ticket_app_error():
    client = TestClient(app)

    response = client.post('/v1/tickets/')
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
