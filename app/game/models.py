from dataclasses import dataclass

from sqlalchemy import Integer, Column, String, ForeignKey, Boolean

from sqlalchemy.orm import relationship

from app.store.database.sqlalchemy_base import db


class GameModel(db):
    __tablename__ = "games"
    id = Column(Integer, primary_key=True)


class PlayerModel(db):
    __tablename__ = "players"
    id = Column(Integer, primary_key=True)


class RoundModel(db):
    __tablename__ = "rounds"
    id = Column(Integer, primary_key=True)
