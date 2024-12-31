"""add_enum

Revision ID: b9d83e1f03d1
Revises: 56286d60c53f
Create Date: 2024-12-21 02:01:27.585869

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b9d83e1f03d1'
down_revision: Union[str, None] = '56286d60c53f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    priority_enum = sa.Enum('LOW', 'MEDIUM', 'HIGH', 'CRITICAL', name='requestpriorityenum')
    priority_enum.create(op.get_bind())

    op.add_column('request_stats', sa.Column('r_priority', priority_enum, nullable=False))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('request_stats', 'r_priority')
    sa.Enum( name='requestpriorityenum').drop(op.get_bind())
    # ### end Alembic commands ###
