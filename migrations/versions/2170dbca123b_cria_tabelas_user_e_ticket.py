"""Cria as tabelas user e ticket.

Migração inicial: reproduz o schema que o SQLModel.metadata.create_all
criava antes do Alembic. Gerada por autogenerate e revisada à mão contra
app/models/user.py e app/models/ticket.py.

Revision ID: 2170dbca123b
Revises:
Create Date: 2026-11-16 20:02:35.587134

"""

from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = '2170dbca123b'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

Texto = sqlmodel.sql.sqltypes.AutoString


def upgrade() -> None:
    op.create_table(
        'user',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', Texto(), nullable=False),
        sa.Column('email', Texto(), nullable=False),
        sa.Column('hashed_password', Texto(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('criado_em', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
    )
    op.create_index(
        op.f('ix_user_username'), 'user', ['username'], unique=True
    )

    op.create_table(
        'ticket',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('titulo', Texto(), nullable=False),
        sa.Column('descricao', Texto(), nullable=False),
        sa.Column('categoria', Texto(), nullable=False),
        sa.Column('prioridade', Texto(), nullable=False),
        sa.Column('criado_em', sa.DateTime(), nullable=False),
        sa.Column('usuario_id', sa.Integer(), nullable=False),
        sa.Column('atribuido_a_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['usuario_id'], ['user.id']),
        sa.ForeignKeyConstraint(['atribuido_a_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    # Ordem inversa: ticket depende de user pelas chaves estrangeiras.
    op.drop_table('ticket')
    op.drop_index(op.f('ix_user_username'), table_name='user')
    op.drop_table('user')
