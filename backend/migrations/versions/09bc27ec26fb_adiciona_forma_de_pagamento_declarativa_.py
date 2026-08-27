"""adiciona forma de pagamento declarativa na sessao

Revision ID: 09bc27ec26fb
Revises: c18be676ce47
Create Date: 2026-08-27 14:47:22.747291

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '09bc27ec26fb'
down_revision: Union[str, None] = 'c18be676ce47'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


payment_method_enum = sa.Enum(
    'pix', 'cartao_credito', 'cartao_debito', 'carteira_do_app', name='payment_method'
)


def upgrade() -> None:
    payment_method_enum.create(op.get_bind())
    op.add_column('charging_sessions', sa.Column('payment_method', payment_method_enum, nullable=True))


def downgrade() -> None:
    op.drop_column('charging_sessions', 'payment_method')
    payment_method_enum.drop(op.get_bind())
