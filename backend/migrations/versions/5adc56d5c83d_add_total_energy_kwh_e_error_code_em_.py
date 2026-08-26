"""add total_energy_kwh e error_code em charger_readings

Revision ID: 5adc56d5c83d
Revises: 6a550df89efb
Create Date: 2026-08-25 20:14:40.484702

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5adc56d5c83d'
down_revision: Union[str, None] = '6a550df89efb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "charger_readings",
        sa.Column(
            "total_energy_kwh",
            sa.Numeric(precision=12, scale=3),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "charger_readings",
        sa.Column("error_code", sa.String(length=50), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("charger_readings", "error_code")
    op.drop_column("charger_readings", "total_energy_kwh")
