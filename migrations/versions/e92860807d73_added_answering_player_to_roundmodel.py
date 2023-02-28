"""added answering_player to RoundModel

Revision ID: e92860807d73
Revises: a7a470b6f586
Create Date: 2023-02-24 20:08:35.668621

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e92860807d73'
down_revision = 'a7a470b6f586'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('rounds', sa.Column('answering_player', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'rounds', 'players', ['answering_player'], ['id'])
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'rounds', type_='foreignkey')
    op.drop_column('rounds', 'answering_player')
    # ### end Alembic commands ###