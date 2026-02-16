from http import HTTPStatus

from fastapi.testclient import TestClient

from app.app import app


def test_health_app():
    client = TestClient(app)

    response = client.get('/health')
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'estado': 'EM ATIVIDADE'}


def test_add_ticket_app_sucesso():
    client = TestClient(app)
    payload = {
        'titulo': 'Teste com titulo com mais de 10 carcterers',
        'descricao': 'Teste de Sucesso',
    }

    response = client.post('/v1/tickets/', json=payload)

    assert response.status_code == HTTPStatus.CREATED
    assert response.json()['dados_originais']['titulo'] == payload['titulo']
    assert 'classe' in response.json()


def test_add_ticket_app_error():
    client = TestClient(app)

    response = client.post('/v1/tickets/')
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    response404 = client.post('/tickets/')
    assert response404.status_code == HTTPStatus.NOT_FOUND
