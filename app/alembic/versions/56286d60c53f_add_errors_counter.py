"""add_errors_counter

Revision ID: 56286d60c53f
Revises: 41a7c267a812
Create Date: 2024-12-11 00:08:28.692395

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '56286d60c53f'
down_revision: Union[str, None] = '41a7c267a812'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('request_stats', sa.Column('errors', sa.Integer(), nullable=False))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('request_stats', 'errors')
    # ### end Alembic commands ###