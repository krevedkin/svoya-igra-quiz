from dataclasses import dataclass
from typing import Optional

from sqlalchemy import Integer, Column, String, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from app.store.database.sqlalchemy_base import db


@dataclass
class Theme:
    id: Optional[int]
    title: str


@dataclass
class Question:
    id: Optional[int]
    title: str
    theme_id: int
    answers: list["Answer"]


@dataclass
class Answer:
    title: str
    is_correct: bool


class ThemeModel(db):
    __tablename__ = "themes"
    id = Column(Integer, primary_key=True)
    title = Column(String, unique=True)

    def __repr__(self):
        return f"(ThemeModel id={self.id}, title={self.title})"


class QuestionModel(db):
    __tablename__ = "questions"
    id = Column(Integer, primary_key=True)
    title = Column(String, unique=True)
    theme_id = Column(
        Integer, ForeignKey("themes.id", ondelete="CASCADE"), nullable=False
    )
    answers = relationship("AnswerModel", backref="questionmodel")

    def __repr__(self):
        return f"(QuestionModel id={self.id}, title={self.title}, theme_id={self.theme_id})"


class AnswerModel(db):
    __tablename__ = "answers"
    id = Column(Integer, primary_key=True)
    title = Column(String)
    is_correct = Column(Boolean)
    question_id = Column(Integer, ForeignKey("questions.id", ondelete="CASCADE"))
