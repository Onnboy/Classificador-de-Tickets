import pytest
from sqlmodel import Session, create_engine


@pytest.fixture(name='engine')
def engine_fixture():
    # Cria o banco em memória para os testes
    engine = create_engine(
        'sqlite://', connect_args={'check_same_thread': False}
    )
    return engine


@pytest.fixture(name='session')
def session_fixture(engine):
    # Gerencia a sessão do banco para cada teste
    with Session(engine) as session:
        yield session


@pytest.fixture(name='override_get_session')
def override_get_session_fixture(engine):
    # Função para sobrescrever a dependência do FastAPI
    def _override():
        with Session(engine) as session:
            yield session

    return _override
