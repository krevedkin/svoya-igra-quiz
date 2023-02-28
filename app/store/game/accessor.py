from sqlalchemy import select, delete, join, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.base_accessor import BaseAccessor

from app.game.models import (
    GameModel,
    PlayerModel,
    RoundModel,
    AnsweredPlayerModel,
    Game,
    Player,
    Round,
    AnsweredPlayer,
    GamePoll,
    GameQuestionsModel,
    GameQuestion,
)
from app.quiz.models import QuestionModel, ThemeModel


class GameAccessor(BaseAccessor):
    async def create_game(self, chat_id: int) -> Game:
        game = GameModel(chat_id=chat_id)
        async with self.app.database.session() as session:
            session: AsyncSession
            session.add(game)
            await session.commit()

        return Game(
            id=game.id,
            created_at=game.created_at,
            is_finished=game.is_finished,
            chat_id=game.chat_id,
        )

    async def _get_game(self, statement):
        async with self.app.database.session() as session:
            session: AsyncSession
            response = await session.execute(statement)
            rows = response.first()
            if not rows:
                return None
            return Game(
                id=rows[0].id,
                created_at=rows[0].created_at,
                is_finished=rows[0].is_finished,
                chat_id=rows[0].chat_id,
            )

    async def get_game_by_id(self, id_: int) -> Game | None:
        stmt = select(GameModel).where(GameModel.id == id_)
        return await self._get_game(stmt)

    async def get_game_by_chat_id(self, chat_id: int) -> Game | None:
        stmt = select(GameModel).where(GameModel.chat_id == chat_id)
        return await self._get_game(stmt)

    async def delete_game(self, chat_id: int):
        async with self.app.database.session() as session:
            session: AsyncSession
            stmt = delete(GameModel).where(GameModel.chat_id == chat_id)
            response = await session.execute(stmt)
            await session.commit()

    async def create_player(self, nickname: str, game_id: int) -> Player:
        player = PlayerModel(nickname=nickname, game_id=game_id)
        async with self.app.database.session() as session:
            session.add(player)
            await session.commit()

            return Player(
                id=player.id,
                score=player.score,
                nickname=player.nickname,
                game_id=player.game_id,
            )

    async def get_player_by_nickname(self, nickname: str) -> Player | None:
        async with self.app.database.session() as session:
            session: AsyncSession
            stmt = select(PlayerModel).where(PlayerModel.nickname == nickname)
            response = await session.execute(stmt)
            rows = response.first()
            if not rows:
                return None
            return Player(
                id=rows[0].id,
                nickname=rows[0].nickname,
                score=rows[0].score,
                game_id=rows[0].game_id,
            )

    async def get_players_by_game_chat_id(self, chat_id) -> list[Player]:
        async with self.app.database.session() as session:
            session: AsyncSession
            stmt = (
                select(PlayerModel).join(GameModel).where(GameModel.chat_id == chat_id)
            )
            result = await session.execute(stmt)
            result = result.scalars()
            return [
                Player(
                    id=player.id,
                    score=player.score,
                    nickname=player.nickname,
                    game_id=player.game_id,
                )
                for player in result
            ]

    async def create_round(
        self,
        count: int,
        game_id: int,
        current_question: int,
    ) -> Round:
        round_ = RoundModel(
            count=count,
            game_id=game_id,
            current_question=current_question,
        )
        async with self.app.database.session() as session:
            session.add(round_)
            await session.commit()

            return Round(
                id=round_.id,
                count=round_.count,
                game_id=round_.game_id,
                current_question=round_.current_question,
            )

    async def update_round_answering_player(
        self, id: str, answering_player: str
    ) -> None:
        async with self.app.database.session() as session:
            session: AsyncSession

            stmt = (
                update(RoundModel)
                .where(RoundModel.id == id)
                .values(answering_player=answering_player)
            )
            await session.execute(stmt)
            await session.commit()

    async def get_round_by_id(self, id_: int) -> Round | None:
        async with self.app.database.session() as session:
            session: AsyncSession
            stmt = select(RoundModel).where(PlayerModel.id == id_)
            response = await session.execute(stmt)
            rows = response.first()
            if not rows:
                return None

            return Round(
                id=rows[0].id,
                count=rows[0].count,
                game_id=rows[0].game_id,
                answering_player=rows[0].answering_player,
                current_question=rows[0].current_question,
            )

    async def get_game_last_round_by_chat_id(self, chat_id: int) -> Round | None:
        async with self.app.database.session() as session:
            session: AsyncSession
            stmt = (
                select(RoundModel)
                .join(GameModel)
                .where(GameModel.chat_id == chat_id)
                .order_by(RoundModel.count.desc())
            )
            res = await session.execute(stmt)
            result = res.scalars().first()
            if not result:
                return None
            return Round(
                id=result.id,
                count=result.count,
                game_id=result.game_id,
                current_question=result.current_question,
                answering_player=result.answering_player,
            )

    async def create_answered_player(self, player_id, round_id) -> AnsweredPlayer:
        answered_player = AnsweredPlayerModel(
            player_id=player_id,
            round_id=round_id,
        )
        async with self.app.database.session() as session:
            session.add(answered_player)
            await session.commit()

            return AnsweredPlayer(
                id=answered_player.id,
                player_id=answered_player.player_id,
                round_id=answered_player.round_id,
            )

    async def get_answered_player_by_round_id(
        self, round_id: int
    ) -> AnsweredPlayer | None:
        async with self.app.database.session() as session:
            session: AsyncSession
            stmt = select(AnsweredPlayerModel).where(
                AnsweredPlayerModel.round_id == round_id
            )
            response = await session.execute(stmt)
            rows = response.first()
            if not rows:
                return None

            return AnsweredPlayer(
                id=rows[0].id,
                round_id=rows[0].round_id,
                player_id=rows[0].player_id,
            )

    async def create_game_poll(self, game_id: int, poll_id: str) -> GamePoll:
        poll = GamePollsModel(game_id=game_id, poll_id=poll_id)

        async with self.app.database.session() as session:
            session: AsyncSession
            session.add(poll)
            await session.commit()

        return GamePoll(id=poll.id, game_id=poll.game_id, poll_id=poll.poll_id)

    async def _get_game_poll(self, statement) -> GamePoll | None:
        async with self.app.database.session() as session:
            session: AsyncSession
            response = await session.execute(statement)
            rows = response.first()
            if not rows:
                return None
            return GamePoll(
                id=rows[0].id,
                poll_id=rows[0].poll_id,
                game_id=rows[0].game_id,
            )

    async def get_game_poll_by_poll_id(self, poll_id: str) -> GamePoll | None:
        stmt = select(GamePollsModel).where(GamePollsModel.poll_id == poll_id)
        return await self._get_game_poll(stmt)

    async def get_game_poll_by_game_id(self, game_id: int) -> GamePoll | None:
        stmt = select(GamePollsModel).where(GamePollsModel.game_id == game_id)
        return await self._get_game_poll(stmt)

    async def get_game_questions_by_chat_id(self, chat_id) -> list[GameQuestion]:
        async with self.app.database.session() as session:
            session: AsyncSession
            stmt = (
                select(
                    GameQuestionsModel.is_answered,
                    GameQuestionsModel.cost,
                    QuestionModel.id.label("question_id"),
                    ThemeModel.title.label("theme"),
                )
                .join(GameModel)
                .join(QuestionModel)
                .join(ThemeModel)
                .where(GameModel.chat_id == chat_id)
                .order_by(GameQuestionsModel.cost)
            )

            result = await session.execute(stmt)

            return [
                GameQuestion(
                    is_answered=item.is_answered,
                    cost=item.cost,
                    theme=item.theme,
                    question=item.question_id,
                )
                for item in result
            ]

    async def generate_game_questions(self, chat_id: int):
        async with self.app.database.session() as session:
            session: AsyncSession

            stmt = select(ThemeModel.title).order_by(func.random()).limit(1)

            result = await session.execute(stmt)
            random_themes = [i for i in result.scalars()]

            questions = []
            for theme in random_themes:
                stmt = (
                    select(QuestionModel)
                    .join(ThemeModel)
                    .filter(ThemeModel.title == theme)
                    .order_by(func.random())
                    .limit(3)
                )
                result = await session.execute(stmt)
                for q in result.scalars():
                    questions.append(q)

            game = await self.get_game_by_chat_id(chat_id)
            game_questions = [
                GameQuestionsModel(
                    game_id=game.id,
                    question_id=q.id,
                    is_answered=False,
                    cost=100,
                )
                for q in questions
            ]
            session.add_all(game_questions)
            await session.commit()
