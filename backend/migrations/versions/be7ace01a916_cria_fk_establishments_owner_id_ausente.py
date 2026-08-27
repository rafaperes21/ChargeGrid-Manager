"""cria fk establishments_owner_id ausente

Revision ID: be7ace01a916
Revises: fd107b73830a
Create Date: 2026-08-27 01:34:57.596483

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'be7ace01a916'
down_revision: Union[str, None] = 'fd107b73830a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # A migration inicial (6a550df89efb) declara este ForeignKeyConstraint com
    # use_alter=True dentro do proprio create_table (necessario para quebrar o ciclo
    # users -> establishments -> ... -> users), mas use_alter exige um op.create_foreign_key
    # separado para o Postgres de fato receber o ALTER TABLE - isso nunca foi feito.
    # Confirmado com inspect(engine).get_foreign_keys('establishments') no banco real:
    # a constraint nao existe. Sem dado orfao em owner_id (checado antes de escrever isto).
    op.create_foreign_key(
        "fk_establishments_owner_id",
        "establishments",
        "users",
        ["owner_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_establishments_owner_id", "establishments", type_="foreignkey")
