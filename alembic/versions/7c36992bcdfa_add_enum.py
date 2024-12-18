"""add_enum

Revision ID: 7c36992bcdfa
Revises: 56286d60c53f
Create Date: 2024-12-19 01:07:53.325392

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7c36992bcdfa'
down_revision: Union[str, None] = '56286d60c53f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
