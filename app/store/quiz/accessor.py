from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.base_accessor import BaseAccessor
from app.quiz.models import (
    Question,
    Theme,
    ThemeModel,
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

    async def create_question(
            self,
            title: str,
            theme_id: int,
            answer: str,
            cost: int,
    ) -> Question:
        question = QuestionModel(
            title=title, theme_id=theme_id, answer=answer, cost=cost
        )
        async with self.app.database.session() as session:
            session: AsyncSession
            session.add(question)
            await session.commit()
            await session.refresh(question)
        return Question(
            id=question.id,
            title=question.title,
            theme_id=theme_id,
            answer=question.answer,
            cost=question.cost,
        )

    async def get_question_by_title(self, title: str) -> Optional[Question]:
        async with self.app.database.session() as session:
            session: AsyncSession
            row = await session.execute(
                select(QuestionModel)
                .where(QuestionModel.title == title)
            )
            row = row.scalars().first()
            if not row:
                return None

        return Question(
            title=row.title,
            id=row.id,
            answer=row.answer,
            theme_id=row.theme_id,
            cost=row.cost,
        )

    async def get_question_by_id(self, id: int):
        async with self.app.database.session() as session:
            session: AsyncSession
            result = await session.execute(
                select(QuestionModel).where(QuestionModel.id == id)
            )
            row = result.scalars().first()
            if not row:
                return None

            return Question(
                title=row.title,
                id=row.id,
                answer=row.answer,
                theme_id=row.theme_id,
                cost=row.cost,
            )

    async def edit_question_by_id(self, id_: int, **kwargs) -> Question | None:
        async with self.app.database.session() as session:
            session: AsyncSession
            stmt = (
                update(QuestionModel)
                .values(**kwargs)
                .where(QuestionModel.id == id_)
                .returning(QuestionModel)
            )

            res = await session.execute(stmt)
            await session.commit()
            question = res.fetchone()
            if question:
                return Question(
                    id=question.id,
                    title=question.title,
                    theme_id=question.theme_id,
                    answer=question.answer,
                    cost=question.cost,
                )

    async def list_questions(
            self, theme_id: Optional[int] = None
    ) -> Optional[list[Question]]:
        async with self.app.database.session() as session:
            session: AsyncSession
            if theme_id:
                query = await session.execute(
                    select(QuestionModel).where(
                        QuestionModel.theme_id == theme_id)
                )
            else:
                query = await session.execute(select(QuestionModel))
            rows = query.scalars().all()
            if not rows:
                return None

            result = []
            for row in rows:
                result.append(
                    Question(
                        title=row.title,
                        id=row.id,
                        answer=row.answer,
                        theme_id=row.theme_id,
                        cost=row.cost,
                    )
                )

            return result
