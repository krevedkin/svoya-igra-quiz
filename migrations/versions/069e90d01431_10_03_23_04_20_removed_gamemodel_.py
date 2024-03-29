"""10/03/23 04:20 removed gameModel foreign key, added fields to GamePlayer

Revision ID: 069e90d01431
Revises: b27d3f7776ab
Create Date: 2023-03-10 04:21:03.646569

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '069e90d01431'
down_revision = 'b27d3f7776ab'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('game_players', sa.Column('is_answering', sa.Boolean(), nullable=True))
    op.add_column('game_players', sa.Column('is_question_chooser', sa.Boolean(), nullable=True))
    op.drop_constraint('games_answering_player_fkey', 'games', type_='foreignkey')
    op.drop_column('games', 'answering_player')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('games', sa.Column('answering_player', sa.INTEGER(), autoincrement=False, nullable=True))
    op.create_foreign_key('games_answering_player_fkey', 'games', 'players', ['answering_player'], ['id'])
    op.drop_column('game_players', 'is_question_chooser')
    op.drop_column('game_players', 'is_answering')
    # ### end Alembic commands ###
