from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import (
    Integer,
    Column,
    String,
    ForeignKey,
    Boolean,
    TIMESTAMP,
    BigInteger,
    UniqueConstraint,
)

from app.store.database.sqlalchemy_base import db


@dataclass
class Game:
    id: int
    created_at: datetime
    is_finished: bool
    chat_id: int


@dataclass
class Player:
    id: int
    nickname: str
    tg_id: int


@dataclass
class GPlayer(Player):
    score: int
    is_answering: bool
    is_question_chooser: bool


@dataclass
class GameQuestion:
    is_answered: bool
    question_id: int
    theme: str
    cost: str


class GameModel(db):
    __tablename__ = "games"
    id = Column(Integer, primary_key=True)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    is_finished = Column(Boolean, default=False)
    chat_id = Column(BigInteger, unique=True)


class PlayerModel(db):
    __tablename__ = "players"
    id = Column(Integer, primary_key=True)
    nickname = Column(String(50), nullable=False, unique=True)
    tg_id = Column(Integer, unique=True)


class GamePlayer(db):
    __tablename__ = "game_players"
    id = Column(Integer, primary_key=True)
    game_id = Column(ForeignKey("games.id", ondelete="CASCADE"))
    player_id = Column(ForeignKey("players.id", ondelete="CASCADE"))
    score = Column(Integer, default=0)
    is_answering = Column(Boolean, default=False)
    is_question_chooser = Column(Boolean, default=False)
    __table_args__ = (
        UniqueConstraint(
            "game_id",
            "player_id",
            name="uq_game_player",
        ),
    )


class GameQuestionsModel(db):
    __tablename__ = "game_questions"
    id = Column(Integer, primary_key=True)
    game_id = Column(ForeignKey(GameModel.id, ondelete="CASCADE"))
    question_id = Column(ForeignKey("questions.id", ondelete="CASCADE"),
                         unique=True)
    is_answered = Column(Boolean, default=False)
    is_current = Column(Boolean, default=False)

    def __repr__(self):
        return (
            f"GameQuestionsModel(id={self.id} "
            f"game_id={self.game_id} "
            f"question_id={self.question_id} "
            f"is_answered={self.is_answered} "
        )
