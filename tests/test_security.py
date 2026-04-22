import time

import jwt

from app.config import settings
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)


def test_hash_e_verificacao_de_senha():
    senha_plana = 'minhasenha123'
    hash_gerado = hash_password(senha_plana)

    assert hash_gerado != senha_plana
    assert verify_password(senha_plana, hash_gerado) is True
    assert verify_password('senha_errada', hash_gerado) is False


def test_create_access_token_valido():
    data = {'sub': 'test@example.com'}
    token = create_access_token(data)

    payload = jwt.decode(
        token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
    )

    assert payload.get('sub') == 'test@example.com'
    assert 'exp' in payload
    assert payload['exp'] > time.time()
