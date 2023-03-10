from sqlalchemy import select, delete, update, func, join
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.base.base_accessor import BaseAccessor
from icecream import ic

# from app.game.models import (
#     GameModel,
#     PlayerModel,
#     RoundModel,
#     AnsweredPlayerModel,
#     Game,
#     Player,
#     Round,
#     AnsweredPlayer,
#     GamePoll,
#     GameQuestionsModel,
#     GameQuestion,
# )

from app.game.models import (
    GameModel,
    Game,
    PlayerModel,
    Player,
    GamePlayer,
    GameQuestionsModel,
)
from app.quiz.models import ThemeModel, QuestionModel, Question


class GameAccessor(BaseAccessor):
    async def create_game(self, chat_id: int) -> Game:
        """Создает новую игру с помощью chat_id"""
        async with self.app.database.session() as session:
            game = GameModel(chat_id=chat_id)
            session: AsyncSession
            session.add(game)
            await session.commit()
            return Game(
                id=game.id,
                created_at=game.created_at,
                is_finished=game.is_finished,
                chat_id=game.chat_id,
                answering_player=game.answering_player,
            )

    async def delete_game(self, chat_id: int):
        """Удаляет запись об игре по chat_id"""
        async with self.app.database.session() as session:
            session: AsyncSession
            stmt = delete(GameModel).where(GameModel.chat_id == chat_id)
            await session.execute(stmt)
            await session.commit()

    async def update_game_finished_status(self, chat_id: int,
                                          is_finished: bool = True):
        """Изменяет статус игры (поле is_finished) по chat_id"""
        async with self.app.database.session() as session:
            session: AsyncSession
            stmt = (
                update(GameModel)
                .where(GameModel.chat_id == chat_id)
                .values(is_finished=is_finished)
            )

            await session.execute(stmt)
            await session.commit()

    async def update_game_answering_player(self, chat_id: int,
                                           user_id: int | None):
        """
        Устанавливает поле answering_player в соответствии с user_id
        Если нужно очистить поле user_id то следует передать None
        Это нужно для того чтобы не было флага отвечающего игрока, и остальные
        игроки могли нажать на кнопку ответить
        """
        async with self.app.database.session() as session:
            session: AsyncSession
            stmt = (
                update(GameModel)
                .where(GameModel.chat_id == chat_id)
                .values(answering_player=user_id)
            )
            await session.execute(stmt)
            await session.commit()

    async def get_game(self, chat_id: int) -> Game | None:
        """Возвращает объект игры по chat_id"""
        async with self.app.database.session() as session:
            session: AsyncSession
            stmt = select(GameModel).where(GameModel.chat_id == chat_id)

            result = await session.execute(stmt)
            result = result.first()
            if not result:
                return None

            game = result[0]
            return Game(
                id=game.id,
                created_at=game.created_at,
                is_finished=game.is_finished,
                chat_id=game.chat_id,
                answering_player=game.answering_player,
            )

    async def create_player(self, nickname: str, tg_id: int) -> Player:
        """
        Создает нового игрока
        """
        async with self.app.database.session() as session:
            player = PlayerModel(
                nickname=nickname,
                tg_id=tg_id,
            )
            session: AsyncSession
            session.add(player)
            await session.commit()
            return player

    async def get_player(self, tg_id: int) -> Player | None:
        """Возвращает объект Player"""
        async with self.app.database.session() as session:
            stmt = select(PlayerModel).where(PlayerModel.tg_id == tg_id)
            result = await session.execute(stmt)

            if not result:
                return None

            result = result.first()[0]
            return Player(
                id=result.id,
                nickname=result.nickname,
                tg_id=result.tg_id,
            )

    async def get_game_players(self, chat_id: int) -> list[Player]:
        """Возвращает список игроков в текущей игре"""
        async with self.app.database.session() as session:
            session: AsyncSession
            stmt = (
                select(PlayerModel)
                .join(GamePlayer)
                .join(GameModel)
                .where(
                    GameModel.chat_id == chat_id,
                )
            )
            result = await session.execute(stmt)
            players = [
                Player(id=player.id, nickname=player.nickname,
                       tg_id=player.tg_id)
                for player in result.scalars()
            ]
            return players

    async def create_game_player(self, game: Game, player: Player):
        """Создает новую запись об игроке связанного с конкретной игрой"""
        async with self.app.database.session() as session:
            session: AsyncSession
            game_player = GamePlayer(game_id=game.id, player_id=player.id)
            session.add(game_player)
            await session.commit()

    async def update_game_player_score(self, game: Game, player_id: int,
                                       score: int):
        """Изменяет количество очков пользователя в игре"""
        async with self.app.database.session() as session:
            session: AsyncSession
            stmt = (
                update(GamePlayer)
                .values(score=GamePlayer.score + score)
                .where(GamePlayer.game_id == game.id,
                       GamePlayer.player_id == player_id)
            )

            await session.execute(stmt)
            await session.commit()

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
                    .limit(5)
                )
                result = await session.execute(stmt)
                for q in result.scalars():
                    questions.append(q)

            game = await self.get_game(chat_id)
            game_questions = [
                GameQuestionsModel(
                    game_id=game.id,
                    question_id=q.id,
                    is_answered=False,
                )
                for q in questions
            ]
            session.add_all(game_questions)
            await session.commit()

    async def get_game_player_scores(self, chat_id: int) -> list:
        async with self.app.database.session() as session:
            session: AsyncSession
            stmt = (
                select([PlayerModel.nickname, GamePlayer.score])
                .select_from(
                    join(
                        GamePlayer, PlayerModel,
                        PlayerModel.id == GamePlayer.player_id
                    )
                    .join(
                        GameModel,
                        GameModel.id == GamePlayer.game_id
                    )
                )
                .where(GameModel.chat_id == chat_id)
            )

            result = await session.execute(stmt)

            return [row for row in result]

    async def get_game_questions(self, chat_id: int) -> dict:
        """
        Возвращает вопросы связанные с конкретной игрой, в виде словаря
        ключами которого являются темы, а вопросы представлены ценой и id
        """
        async with self.app.database.session() as session:
            session: AsyncSession

            stmt = (
                select([GameQuestionsModel.question_id, QuestionModel.cost,
                        ThemeModel.title])
                .select_from(
                    join(
                        GameQuestionsModel, QuestionModel,
                        GameQuestionsModel.question_id == QuestionModel.id
                    )
                    .join(
                        ThemeModel,
                        QuestionModel.theme_id == ThemeModel.id)
                    .join(
                        GameModel,
                        GameQuestionsModel.game_id == GameModel.id
                    )
                )
                .where(
                    GameQuestionsModel.is_answered == False,
                    GameModel.chat_id == chat_id
                )
                .order_by(ThemeModel.id, QuestionModel.cost)
            )

            result = await session.execute(stmt)

            res = {}

            for row in result.fetchall():
                question_id = row[0]
                cost = row[1]
                theme = row[2]

                if theme not in res:
                    res[theme] = [{"question_id": question_id, "cost": cost}]
                else:
                    res[theme].append(
                        {"question_id": question_id, "cost": cost})

            return res

    async def update_game_question_state(self, question_id: int,
                                         chat_id: int,
                                         **kwargs):
        """
        Метод для установки статуса текущего вопроса в игре
        kwargs могут быть is_answered или is_current типа bool
        """
        async with self.app.database.session() as session:
            session: AsyncSession
            game = await self.get_game(chat_id)
            stmt = (
                update(GameQuestionsModel)
                .values(**kwargs)
                .where(GameQuestionsModel.question_id == question_id,
                       GameQuestionsModel.game_id == game.id)
            )

            await session.execute(stmt)
            await session.commit()

    async def get_current_game_question(self, chat_id: int) -> Question:
        """Метод для получения текущего вопроса в игре"""
        async with self.app.database.session() as session:
            session: AsyncSession
            stmt = (
                select(QuestionModel)
                .join(GameQuestionsModel)
                .join(GameModel)
                .where(GameModel.chat_id == chat_id,
                       GameQuestionsModel.is_current == True)
            )

            result = await session.execute(stmt)
            result = result.scalars().first()
            return Question(
                id=result.id,
                title=result.title,
                theme_id=result.theme_id,
                answer=result.answer,
                cost=result.cost,
            )

    async def get_player_winner(self, chat_id: int) -> list[tuple[str, str]]:
        """
        Метод для получения победителя в игре.
        Возвращает список со строками - никнейм + счет
        Список сделан для того, чтобы обработать ситуацию когда у игроков равный
        счет.
        """
        async with self.app.database.session() as session:
            session: AsyncSession

            subquery = select([func.max(GamePlayer.score)]).where(
                GamePlayer.game_id == GamePlayer.game_id).as_scalar()

            stmt = (
                select([PlayerModel.nickname,
                        GamePlayer.score])
                .select_from(join(PlayerModel, GamePlayer,
                                  PlayerModel.id == GamePlayer.player_id).join(
                    GameModel, GamePlayer.game_id == GameModel.id))
                .where(GameModel.chat_id == chat_id)
                .where(GamePlayer.score == subquery)
            )

            res = await session.execute(stmt)

            nickname_with_score = [player for player in res.fetchall()]
            return nickname_with_score
