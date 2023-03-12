"""restored

Revision ID: 90cefcb60a64
Revises: ec472ac871e5
Create Date: 2023-03-10 05:19:48.799900

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '90cefcb60a64'
down_revision = 'ec472ac871e5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('game_players', 'fake_field')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('game_players', sa.Column('fake_field', sa.INTEGER(), autoincrement=False, nullable=True))
    # ### end Alembic commands ###