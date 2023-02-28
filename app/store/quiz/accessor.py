from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.base_accessor import BaseAccessor
from app.quiz.models import (
    Answer,
    Question,
    Theme,
    ThemeModel,
    AnswerModel,
    QuestionModel,
)


class QuizAccessor(BaseAccessor):
    async def create_theme(self, title: str) -> Theme:
        theme = ThemeModel(title=title)
        async with self.app.database.session() as session:
            session: AsyncSession
            session.add(theme)
            await session.commit()
            await session.refresh(theme)

        return Theme(theme.id, theme.title)

    async def _get_theme(self, statement):
        async with self.app.database.session() as session:
            session: AsyncSession
            result = await session.execute(statement)
            rows = result.first()
            if not rows:
                return None
        return Theme(rows[0].id, rows[0].title)

    async def get_theme_by_title(self, title: str) -> Optional[Theme]:
        stmt = select(ThemeModel).where(ThemeModel.title == title)
        return await self._get_theme(stmt)

    async def get_theme_by_id(self, id_: int) -> Optional[Theme]:
        stmt = select(ThemeModel).where(ThemeModel.id == id_)
        return await self._get_theme(stmt)

    async def list_themes(self) -> list[Theme]:
        stmt = select(ThemeModel)
        async with self.app.database.session() as session:
            session: AsyncSession
            result = await session.scalars(stmt)

        return [Theme(id=row.id, title=row.title) for row in result]

    async def create_answers(
        self, question_id: int, answers: list[Answer]
    ) -> list[Answer]:
        answer_models = [
            AnswerModel(
                is_correct=answer.is_correct,
                title=answer.title,
                question_id=question_id,
            )
            for answer in answers
        ]

        async with self.app.database.session() as session:
            session: AsyncSession
            session.add_all(answer_models)
            await session.commit()
            for answer in answer_models:
                await session.refresh(answer)
        return [
            Answer(title=model.title, is_correct=model.is_correct)
            for model in answer_models
        ]

    async def create_question(
        self, title: str, theme_id: int, answers: list[Answer] = None
    ) -> Question:
        # if theme_id is None:
        #     raise IntegrityError(statement="123", params=None, orig=None)
        question = QuestionModel(title=title, theme_id=theme_id)
        async with self.app.database.session() as session:
            session: AsyncSession
            session.add(question)
            await session.commit()
            await session.refresh(question)
        answers_ = await self.create_answers(question_id=question.id, answers=answers)
        return Question(
            id=question.id, title=question.title, theme_id=theme_id, answers=answers_
        )

    async def get_question_by_title(self, title: str) -> Optional[Question]:
        async with self.app.database.session() as session:
            session: AsyncSession
            row = await session.execute(
                select(QuestionModel)
                .where(QuestionModel.title == title)
                .options(selectinload(QuestionModel.answers))
            )
            row = row.scalars().first()
            if not row:
                return None

            answers = [
                Answer(title=answer.title, is_correct=answer.is_correct)
                for answer in row.answers
            ]
        return Question(
            title=row.title, id=row.id, answers=answers, theme_id=row.theme_id
        )

    async def get_question_by_id(self, id: int):
        async with self.app.database.session() as session:
            session: AsyncSession
            result = await session.execute(
                select(QuestionModel)
                .where(QuestionModel.id == id)
                .options(selectinload(QuestionModel.answers))
            )
            row = result.scalars().first()
            if not row:
                return None

            answers = [
                Answer(title=answer.title, is_correct=answer.is_correct)
                for answer in row.answers
            ]
            return Question(
                title=row.title, id=row.id, answers=answers, theme_id=row.theme_id
            )

    async def list_questions(
        self, theme_id: Optional[int] = None
    ) -> Optional[list[Question]]:
        async with self.app.database.session() as session:
            session: AsyncSession
            if theme_id:
                query = await session.execute(
                    select(QuestionModel)
                    .where(QuestionModel.theme_id == theme_id)
                    .options(selectinload(QuestionModel.answers))
                )
            else:
                query = await session.execute(
                    select(QuestionModel).options(selectinload(QuestionModel.answers))
                )
            rows = query.scalars().all()
            if not rows:
                return None

            result = []
            for row in rows:
                answers = [
                    Answer(title=answer.title, is_correct=answer.is_correct)
                    for answer in row.answers
                ]
                result.append(
                    Question(
                        title=row.title,
                        id=row.id,
                        answers=answers,
                        theme_id=row.theme_id,
                    )
                )

            return result

    async def get_answer_by_title(self, title: str) -> Answer | None:
        async with self.app.database.session() as session:
            session: AsyncSession

            query = select(AnswerModel).where(AnswerModel.title == title)

            result = await session.execute(query)
            result = result.scalars().first()

            if not result:
                return None
            return Answer(is_correct=result.is_correct, title=result.title)
