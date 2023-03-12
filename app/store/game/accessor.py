from sqlalchemy import select, delete, update, func, join
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.base_accessor import BaseAccessor

from app.game.models import (
    GameModel,
    Game,
    PlayerModel,
    Player,
    GamePlayer,
    GameQuestionsModel,
    GPlayer,
    FinishedGame,
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
            )

    async def delete_game(self, chat_id: int):
        """Удаляет запись об игре по chat_id"""
        async with self.app.database.session() as session:
            session: AsyncSession
            stmt = delete(GameModel).where(GameModel.chat_id == chat_id)
            await session.execute(stmt)
            await session.commit()

    async def delete_finished_game_by_id(self, id_: int) -> Game | None:
        """
        Удаляет законченную игру по ее id
        """
        async with self.app.database.session() as session:
            session: AsyncSession
            stmt = (
                delete(GameModel)
                .where(GameModel.id == id_, GameModel.is_finished == True)
                .returning(GameModel)
            )

            res = await session.execute(stmt)
            await session.commit()

            deleted_game = res.fetchone()
            if deleted_game:
                return Game(
                    id=deleted_game.id,
                    created_at=deleted_game.created_at,
                    is_finished=True,
                    chat_id=None,
                )

    async def delete_game_chat_id(self, chat_id: int):
        """Удаляет запись chat_id из игры"""
        async with self.app.database.session() as session:
            stmt = (
                update(GameModel)
                .values(chat_id=None)
                .where(GameModel.chat_id == chat_id)
            )
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

    async def update_player_answering_or_chooser(
            self,
            chat_id: int,
            player_tg_id: int,
            is_answering: bool | None = None,
            is_chooser: bool | None = None
    ):
        """
        Устанавливает поля is_question_chooser или is_answering модели
        GamePlayers
        """
        async with self.app.database.session() as session:
            session: AsyncSession
            query = (
                select(GamePlayer)
                .join(GameModel)
                .join(PlayerModel)
                .where(
                    GameModel.chat_id == chat_id,
                    PlayerModel.tg_id == player_tg_id
                )
            )
            results = await session.execute(query)
            for result in results.scalars():
                if is_answering is not None:
                    result.is_answering = is_answering
                if is_chooser is not None:
                    result.is_question_chooser = is_chooser
            await session.commit()

    async def get_game(self, chat_id: int) -> Game | None:
        """Возвращает объект игры по chat_id"""
        async with self.app.database.session() as session:
            session: AsyncSession
            stmt = select(GameModel).where(GameModel.chat_id == chat_id,
                                           GameModel.is_finished == False)

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
            )

    async def get_finished_games(self) -> list[FinishedGame]:
        """Возвращает список законченных игр"""
        async with self.app.database.session() as session:
            query = (
                select(
                    GameModel.id, GameModel.created_at,
                    func.array_agg(PlayerModel.nickname).label('nicknames'),
                    func.array_agg(GamePlayer.score).label('scores')
                )
                .select_from(
                    join(
                        GamePlayer, PlayerModel,
                        GamePlayer.player_id == PlayerModel.id
                    )
                )
                .where(GameModel.is_finished == True)
                .group_by(GameModel.id)

            )
            res = await session.execute(query)
            result = res.fetchall()

            games = [
                FinishedGame(
                    id=row.id,
                    created_at=row.created_at,
                    players_and_scores=dict(zip(row.nicknames, row.scores))
                )
                for row in result
            ]

            return games

    async def create_player(self, nickname: str, tg_id: int) -> Player:
        """
        Создает нового игрока в таблице Players
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
        async with self.app.database.session() as session:
            stmt = select(PlayerModel).where(PlayerModel.tg_id == tg_id)
            result = await session.execute(stmt)
            result = result.first()
            if not result:
                return None

            result = result[0]

            return Player(tg_id=result.tg_id, nickname=result.nickname,
                          id=result.id)

    async def get_game_player(self, chat_id: int, tg_id: int) -> GPlayer | None:
        """Возвращает объект GPlayer связанного с текущей игрой"""
        async with self.app.database.session() as session:
            stmt = (
                select(
                    GamePlayer.score,
                    GamePlayer.is_answering,
                    GamePlayer.is_question_chooser,
                    PlayerModel.tg_id,
                    PlayerModel.nickname,
                    PlayerModel.id
                )
                .join(PlayerModel)
                .join(GameModel)
                .where(PlayerModel.tg_id == tg_id,
                       GameModel.chat_id == chat_id))
            result = await session.execute(stmt)

            if not result:
                return None

            result = result.first()
            return GPlayer(
                id=result.id,
                nickname=result.nickname,
                tg_id=result.tg_id,
                score=result.score,
                is_question_chooser=result.is_question_chooser,
                is_answering=result.is_answering
            )

    async def get_game_players(self, chat_id: int) -> list[GPlayer]:
        """Возвращает список игроков в текущей игре"""
        async with self.app.database.session() as session:
            session: AsyncSession
            stmt = (
                select(
                    GamePlayer.score,
                    GamePlayer.is_answering,
                    GamePlayer.is_question_chooser,
                    PlayerModel.tg_id,
                    PlayerModel.nickname,
                    PlayerModel.id
                )
                .join(PlayerModel)
                .join(GameModel)
                .where(
                    GameModel.chat_id == chat_id,
                )
            )
            result = await session.execute(stmt)

            players = [
                GPlayer(id=player.id,
                        nickname=player.nickname,
                        tg_id=player.tg_id,
                        score=player.score,
                        is_answering=player.is_answering,
                        is_question_chooser=player.is_question_chooser)
                for player in result.fetchall()
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

    async def get_answering_player(self, chat_id: int) -> GPlayer | None:
        """Возвращает Gplayer объект игрока, который в данный момент является
        отвечающим, если такого нет вернет None
        """
        async with self.app.database.session() as session:
            session: AsyncSession
            stmt = (
                select(
                    GamePlayer.score,
                    GamePlayer.is_answering,
                    GamePlayer.is_question_chooser,
                    PlayerModel.tg_id,
                    PlayerModel.nickname,
                    PlayerModel.id
                )
                .join(GameModel)
                .join(PlayerModel)
                .where(GameModel.chat_id == chat_id,
                       GamePlayer.is_answering == True)
            )
            result = await session.execute(stmt)
            result = result.first()
            if not result:
                return None

            return GPlayer(
                id=result.id,
                nickname=result.nickname,
                tg_id=result.tg_id,
                score=result.score,
                is_question_chooser=result.is_question_chooser,
                is_answering=result.is_answering
            )

    async def get_question_chooser_player(self, chat_id: int) -> GPlayer | None:
        """Возвращает Gplayer объект игрока, который в данный момент является
        отвечающим, если такого нет вернет None
        """
        async with self.app.database.session() as session:
            session: AsyncSession
            stmt = (
                select(
                    GamePlayer.score,
                    GamePlayer.is_answering,
                    GamePlayer.is_question_chooser,
                    PlayerModel.tg_id,
                    PlayerModel.nickname,
                    PlayerModel.id
                )
                .join(GameModel)
                .join(PlayerModel)
                .where(GameModel.chat_id == chat_id,
                       GamePlayer.is_question_chooser == True)
            )
            result = await session.execute(stmt)
            result = result.first()
            if not result:
                return None

            return GPlayer(
                id=result.id,
                nickname=result.nickname,
                tg_id=result.tg_id,
                score=result.score,
                is_question_chooser=result.is_question_chooser,
                is_answering=result.is_answering
            )

    async def get_available_themes(self) -> list[str]:
        """
        Метод для получения списка тем, которые могут появиться в игре.
        Возвращает только те темы, у которых есть по крайней мере 5 вопросов
        стоимости которых формируют группу 100,200,300,400,500
        """
        async with self.app.database.session() as session:
            session: AsyncSession

            stmt = (
                select(ThemeModel.title)
                .join(QuestionModel)
                .group_by(ThemeModel.id)
                .having(func.count(QuestionModel.cost.distinct()) >= 5)
                .order_by(ThemeModel.id)
            )
            result = await session.execute(stmt)
            return [theme for theme in result.scalars()]

    async def generate_game_questions(self, chat_id: int):
        """
            Метод для генерирования вопросов игры.
            Первое выражение выбирает 5 случайных тем из базы данных,
        у которых есть по крайней мере 5 вопросов с уникальной стоимостью,
        такие как 100,200, 300, 400, 500.
        Если не будет хотя бы одного из вопросов с такой стоимостью, они не
        попадут в выборку, это нужно для того чтобы не было ситуации когда
        игра генерирует клавиатуру, а там не хватает вопросов в какой-то из
        тем.
            Далее в цикле для каждой темы делается выборка вопросов так,
        чтобы в нее попали только вопросы с уникальными ценами.

        В результирующем наборе будут вопрос за 100 за 200 за 300 за 400 за 500.
        После чего эти вопросы будут записаны в таблицу game_questions.
        """
        async with self.app.database.session() as session:
            session: AsyncSession

            stmt = (
                select(ThemeModel.title)
                .join(QuestionModel)
                .group_by(ThemeModel.id)
                .having(func.count(QuestionModel.cost.distinct()) >= 5)
                .order_by(func.random())
                .limit(5)
            )
            result = await session.execute(stmt)
            random_themes = [i for i in result.scalars()]

            questions = []
            for theme in random_themes:
                subquery = (
                    select(QuestionModel)
                    .join(ThemeModel)
                    .filter(ThemeModel.title == theme)
                    .distinct(QuestionModel.cost)
                    .subquery()
                )

                stmt = (
                    select(subquery)
                    .order_by(func.random())
                    .limit(5)
                )
                result = await session.execute(stmt)
                for q in result.fetchall():
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
