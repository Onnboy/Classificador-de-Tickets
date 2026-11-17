from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool
from sqlmodel import SQLModel

# Importa os modelos para registrar as tabelas em SQLModel.metadata.
from app.models.ticket import Ticket  # noqa: F401
from app.models.user import User  # noqa: F401

config = context.config

# disable_existing_loggers=False: sem isso, rodar as migrações dentro do
# pytest desligaria os loggers já configurados pela aplicação e pelos testes.
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = SQLModel.metadata

# render_as_batch: o SQLite não altera colunas nem constraints com ALTER
# TABLE; em modo batch o Alembic recria a tabela. No PostgreSQL o modo batch
# continua usando ALTER TABLE normal.
OPCOES = {'target_metadata': target_metadata, 'render_as_batch': True}


def _database_url() -> str:
    # Import tardio: Settings exige todas as variáveis do .env, e quem passa
    # a conexão pronta (o teste de migração) não precisa delas.
    from app.config import settings  # noqa: PLC0415

    return settings.DATABASE_URL


def run_migrations_offline() -> None:
    """Gera o SQL das migrações sem conectar ao banco (alembic --sql)."""
    context.configure(
        url=_database_url(),
        literal_binds=True,
        dialect_opts={'paramstyle': 'named'},
        **OPCOES,
    )
    with context.begin_transaction():
        context.run_migrations()


def _rodar_com_conexao(connection) -> None:
    context.configure(connection=connection, **OPCOES)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Aplica as migrações conectado ao banco.

    Se quem chamou passou uma conexão em config.attributes['connection'],
    usa essa conexão; senão, cria o engine pela settings.DATABASE_URL.
    """
    connection = config.attributes.get('connection')
    if connection is not None:
        _rodar_com_conexao(connection)
        return

    engine = create_engine(_database_url(), poolclass=pool.NullPool)
    with engine.connect() as connection:
        _rodar_com_conexao(connection)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
