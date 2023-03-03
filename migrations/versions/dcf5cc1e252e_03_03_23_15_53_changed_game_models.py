"""03.03.23 15:53 CHANGED Game Models

Revision ID: dcf5cc1e252e
Revises: 
Create Date: 2023-03-03 15:57:20.408862

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'dcf5cc1e252e'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('game_players',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('game_id', sa.Integer(), nullable=True),
    sa.Column('player_id', sa.Integer(), nullable=True),
    sa.Column('score', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['game_id'], ['games.id'], ),
    sa.ForeignKeyConstraint(['player_id'], ['players.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.drop_table('answered_players')
    op.drop_table('rounds')
    op.add_column('games', sa.Column('answering_player', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'games', 'players', ['answering_player'], ['id'])
    op.add_column('players', sa.Column('tg_id', sa.Integer(), nullable=True))
    op.create_unique_constraint(None, 'players', ['tg_id'])
    op.drop_constraint('players_game_id_fkey', 'players', type_='foreignkey')
    op.drop_column('players', 'score')
    op.drop_column('players', 'game_id')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('players', sa.Column('game_id', sa.INTEGER(), autoincrement=False, nullable=True))
    op.add_column('players', sa.Column('score', sa.INTEGER(), autoincrement=False, nullable=True))
    op.create_foreign_key('players_game_id_fkey', 'players', 'games', ['game_id'], ['id'], ondelete='CASCADE')
    op.drop_constraint(None, 'players', type_='unique')
    op.drop_column('players', 'tg_id')
    op.drop_constraint(None, 'games', type_='foreignkey')
    op.drop_column('games', 'answering_player')
    op.create_table('rounds',
    sa.Column('id', sa.INTEGER(), server_default=sa.text("nextval('rounds_id_seq'::regclass)"), autoincrement=True, nullable=False),
    sa.Column('count', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('current_question', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('is_button_pressed', sa.BOOLEAN(), autoincrement=False, nullable=True),
    sa.Column('game_id', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('answering_player', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('winner_player', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.ForeignKeyConstraint(['answering_player'], ['players.id'], name='rounds_answering_player_fkey'),
    sa.ForeignKeyConstraint(['current_question'], ['game_questions.question_id'], name='rounds_current_question_fkey', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['game_id'], ['games.id'], name='rounds_game_id_fkey', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['winner_player'], ['players.id'], name='rounds_winner_player_fkey'),
    sa.PrimaryKeyConstraint('id', name='rounds_pkey'),
    postgresql_ignore_search_path=False
    )
    op.create_table('answered_players',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('player_id', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('round_id', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.ForeignKeyConstraint(['player_id'], ['players.id'], name='answered_players_player_id_fkey', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['round_id'], ['rounds.id'], name='answered_players_round_id_fkey', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name='answered_players_pkey')
    )
    op.drop_table('game_players')
    # ### end Alembic commands ###