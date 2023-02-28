from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Integer, Column, String, ForeignKey, Boolean, TIMESTAMP

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
    score: int
    game_id: int


@dataclass
class Round:
    id: int
    count: int
    game_id: int
    current_question: int
    answering_player: int | None = None


@dataclass
class AnsweredPlayer:
    id: int
    player_id: int
    round_id: int


@dataclass
class GamePoll:
    id: int
    game_id: int
    poll_id: str


@dataclass
class GameQuestion:
    cost: int
    is_answered: bool
    question: str
    theme: str


class GameModel(db):
    __tablename__ = "games"
    id = Column(Integer, primary_key=True)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    is_finished = Column(Boolean, default=False)
    chat_id = Column(Integer, unique=True)

    def __repr__(self):
        return (
            f"GameModel(id={self.id}, created_at{self.created_at}, "
            f"is_finished={self.is_finished})"
        )


class PlayerModel(db):
    __tablename__ = "players"
    id = Column(Integer, primary_key=True)
    nickname = Column(String(50), nullable=False)
    score = Column(Integer, default=0)
    game_id = Column(ForeignKey("games.id", ondelete="CASCADE"))


class RoundModel(db):
    __tablename__ = "rounds"
    id = Column(Integer, primary_key=True)
    count = Column(Integer, default=1, nullable=False)
    current_question = Column(
        ForeignKey("game_questions.question_id", ondelete="CASCADE")
    )

    game_id = Column(ForeignKey("games.id", ondelete="CASCADE"))
    answering_player = Column(String(50), nullable=True)


class AnsweredPlayerModel(db):
    __tablename__ = "answered_players"
    id = Column(Integer, primary_key=True)
    player_id = Column(ForeignKey(PlayerModel.id, ondelete="CASCADE"))
    round_id = Column(ForeignKey(RoundModel.id, ondelete="CASCADE"))


class GameQuestionsModel(db):
    __tablename__ = "game_questions"
    id = Column(Integer, primary_key=True)
    game_id = Column(ForeignKey(GameModel.id, ondelete="CASCADE"))
    question_id = Column(ForeignKey("questions.id", ondelete="CASCADE"), unique=True)
    is_answered = Column(Boolean, default=False)
    cost = Column(Integer, default=100)

    def __repr__(self):
        return (
            f"GameQuestionsModel(id={self.id} "
            f"game_id={self.game_id} "
            f"question_id={self.question_id} "
            f"is_answered={self.is_answered} "
            f"cost={self.cost})"
        )
