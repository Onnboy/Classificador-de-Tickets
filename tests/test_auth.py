from http import HTTPStatus

import pytest
from httpx import ASGITransport, AsyncClient
from sqlmodel import SQLModel

from app.app import app
from app.database import get_session


@pytest.mark.anyio
async def test_login_sucesso(engine, override_get_session):

    SQLModel.metadata.create_all(engine)
    app.dependency_overrides[get_session] = override_get_session

    tp = ASGITransport(app=app)
    async with AsyncClient(transport=tp, base_url='http://test') as ac:
        await ac.post(
            '/v1/users/',
            json={
                'username': 'authuser',
                'email': 'auth@example.com',
                'password': 'secretpassword',
            },
        )

        login_data = {'username': 'authuser', 'password': 'secretpassword'}
        response = await ac.post('/v1/auth/token', data=login_data)

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert 'access_token' in data
        assert data['token_type'] == 'bearer'

    app.dependency_overrides.clear()
    SQLModel.metadata.drop_all(engine)
