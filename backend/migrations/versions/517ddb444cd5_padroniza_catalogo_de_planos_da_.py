"""padroniza catalogo de planos da plataforma

Revision ID: 517ddb444cd5
Revises: 7830e4378920
Create Date: 2026-08-27 14:35:12.848674

"""
import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '517ddb444cd5'
down_revision: Union[str, None] = '7830e4378920'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PLAN_KINDS = ('avulso', 'mensal', 'trimestral')


def upgrade() -> None:
    connection = op.get_bind()

    # 1) coluna nova, nullable por enquanto (backfill vem antes do NOT NULL).
    op.add_column('plans', sa.Column('enabled', sa.Boolean(), nullable=True))

    # 2) linhas que ja existiam eram planos ativamente oferecidos - considera habilitadas.
    connection.execute(sa.text('UPDATE plans SET enabled = true WHERE enabled IS NULL'))

    # 3) valores viravam constante de codigo (services/plan_catalog.py) - nunca mais coluna.
    # Precisa vir antes do backfill de linhas novas abaixo, senao elas violam o NOT NULL
    # que essas colunas antigas ainda tem.
    op.drop_column('plans', 'name')
    op.drop_column('plans', 'price')
    op.drop_column('plans', 'discount_pct')
    op.drop_column('plans', 'free_kwh_allowance')
    op.drop_column('plans', 'priority')

    # 4) garante uma linha por nivel do catalogo (services/plan_catalog.PLAN_CATALOG) em
    # todo estabelecimento - a maioria ainda nao tinha nenhuma linha de Plan nesta fase do
    # projeto. Espelha `provision_plans_for_establishment`: avulso habilitado por padrao,
    # mensal/trimestral desabilitados ate o proprietario optar.
    establishments = connection.execute(sa.text('SELECT id FROM establishments')).fetchall()
    for (establishment_id,) in establishments:
        existing_kinds = {
            row[0]
            for row in connection.execute(
                sa.text('SELECT kind FROM plans WHERE establishment_id = :eid'),
                {'eid': establishment_id},
            ).fetchall()
        }
        for kind in PLAN_KINDS:
            if kind in existing_kinds:
                continue
            connection.execute(
                sa.text(
                    'INSERT INTO plans (id, establishment_id, kind, enabled) '
                    'VALUES (:id, :eid, CAST(:kind AS plan_kind), :enabled)'
                ),
                {
                    'id': str(uuid.uuid4()),
                    'eid': establishment_id,
                    'kind': kind,
                    'enabled': kind == 'avulso',
                },
            )

    op.alter_column('plans', 'enabled', nullable=False)
    op.create_unique_constraint('uq_plans_establishment_kind', 'plans', ['establishment_id', 'kind'])


def downgrade() -> None:
    op.drop_constraint('uq_plans_establishment_kind', 'plans', type_='unique')
    op.add_column('plans', sa.Column('priority', sa.INTEGER(), autoincrement=False, nullable=False, server_default='0'))
    op.add_column('plans', sa.Column('free_kwh_allowance', sa.NUMERIC(precision=12, scale=3), autoincrement=False, nullable=True))
    op.add_column('plans', sa.Column('discount_pct', sa.NUMERIC(precision=5, scale=2), autoincrement=False, nullable=True))
    op.add_column('plans', sa.Column('price', sa.NUMERIC(precision=12, scale=4), autoincrement=False, nullable=True))
    op.add_column('plans', sa.Column('name', sa.VARCHAR(length=100), autoincrement=False, nullable=False, server_default=''))
    op.drop_column('plans', 'enabled')
