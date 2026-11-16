"""Garante que as migrações do Alembic e os modelos SQLModel batem.

Se alguém alterar um modelo sem criar a migração correspondente, o teste
test_upgrade_head_bate_com_os_modelos falha e a CI acusa.

Limitação: roda em SQLite. Diferenças específicas do PostgreSQL (tipos,
server defaults) não aparecem aqui.
"""

from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect
from sqlmodel import SQLModel

# Importa os modelos para registrar as tabelas em SQLModel.metadata.
from app.models.ticket import Ticket  # noqa: F401
from app.models.user import User  # noqa: F401

RAIZ = Path(__file__).resolve().parent.parent


@pytest.fixture(name='conexao')
def conexao_fixture():
    engine = create_engine('sqlite://')
    with engine.begin() as conexao:
        yield conexao
    engine.dispose()


def _config(conexao) -> Config:
    config = Config(str(RAIZ / 'alembic.ini'))
    config.attributes['connection'] = conexao
    return config


def _diferencas(conexao) -> list:
    contexto = MigrationContext.configure(conexao)
    return compare_metadata(contexto, SQLModel.metadata)


def test_migracoes_tem_uma_unica_head():
    script = ScriptDirectory.from_config(Config(str(RAIZ / 'alembic.ini')))

    assert len(script.get_heads()) == 1


def test_upgrade_head_bate_com_os_modelos(conexao):
    command.upgrade(_config(conexao), 'head')

    assert _diferencas(conexao) == []


def test_downgrade_base_remove_tudo_e_upgrade_recria(conexao):
    config = _config(conexao)
    command.upgrade(config, 'head')

    command.downgrade(config, 'base')

    assert inspect(conexao).get_table_names() == ['alembic_version']

    command.upgrade(config, 'head')

    assert _diferencas(conexao) == []
