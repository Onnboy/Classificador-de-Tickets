from app.core.security import hash_password, verify_password


def test_hash_e_verificacao_de_senha():
    senha_plana = 'minhasenha123'
    hash_gerado = hash_password(senha_plana)

    assert hash_gerado != senha_plana
    assert verify_password(senha_plana, hash_gerado) is True
    assert verify_password('senha_errada', hash_gerado) is False
