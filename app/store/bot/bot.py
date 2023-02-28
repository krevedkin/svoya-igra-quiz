import asyncio
import json
import typing
import random
from logging import getLogger
from typing import Sequence

from sqlalchemy.exc import IntegrityError

from app.game.models import Player, GameQuestion
from app.store.telegram_api.dataclasses import Update

if typing.TYPE_CHECKING:
    from app.web.app import Application


class Bot:
    def __init__(self, app: "Application"):
        self.app = app
        self.update: Update | None = None
        self.logger = getLogger("Bot")

    def parse_command(self) -> str:
        for entity in self.update.message.entities:
            if entity.type == "bot_command":
                command = self.update.message.text[
                          entity.offset: entity.offset + entity.length]
                return command

    async def command_handler(self):
        command = self.parse_command()
        match command:
            case "/start":
                await self.start()
            case "/start_game":
                await self.start_game()
            case "/stop_game":
                await self.stop_game()
            case "/stop_game":
                await self.stop_game()
            # case "/show":
            #     await self.show_keyboard()
            case "/menu":
                await self.show_game_menu()
            case "/test":
                await self.app.store.game.generate_game_questions(-879727519)
            case _:
                print("команды не было")

    async def message_handler(self):
        await self.app.store.tg_api.send_message(
            chat_id=self.update.message.chat.id,
            text="Это просто сообщение"
        )

    async def callback_query_handler(self):
        if self.update.callback_query:
            data = self.update.callback_query.data
            match data:
                # начало игры после команды /start_game
                case "confirm_game_start":
                    await self.app.store.tg_api.delete_message(
                        self.update.callback_query.message
                    )
                    await self.app.store.tg_api.send_message(
                        chat_id=self.update.callback_query.message.chat.id,
                        text="Игра началась"
                    )
                    await self.round_handler()

                # отмена игры
                case "cancel_game_start":
                    await self.stop_game()
                    await self.app.store.tg_api.delete_message(
                        self.update.callback_query.message
                    )
                    await self.app.store.tg_api.send_message(
                        chat_id=self.update.callback_query.message.chat.id,
                        text="Игра была отменена! Напишите "
                             "/start_game чтобы начать заново!"
                    )
                # В остальных случаях переходим в обработчика логики игры
                case _:
                    await self.round_handler()

    async def show_game_menu(self):
        """Показать меню игры с inline кнопками"""
        await self.app.store.tg_api.send_message(
            chat_id=self.update.message.chat.id,
            text="Выберите действие",
            reply_markup=self.create_markup(
                (
                    ("Показать счет", "show_score"),
                    ("Закончить игру", "cancel_game_start"),
                ),
            )
        )

    async def start(self):
        """Показывает сообщение при вводе команды /start"""
        await self.app.store.tg_api.send_message(
            chat_id=self.update.message.chat.id,
            text="Для начала игры создайте группу и добавьте бота туда,"
                 "После чего введите команду /start_game",
        )

    async def start_game(self) -> None:
        """
        Создает новую игру, если она уже была создана, игра не создается.
        Создает список игроков состоящих и администраторов чата.
        Отправляет список зарегистрированных игроков с inline кнопками
        для подтверждения запуска игры или отмены
        """
        try:
            game = await self.app.store.game.create_game(
                self.update.message.chat.id)
            await self.app.store.tg_api.send_message(
                chat_id=self.update.message.chat.id,
                text="Ура вы начали игру!!!",
            )
            players = await self.app.store.tg_api.get_chat_admins(
                self.update.message.chat.id)
            players_string = ''
            for player in players:
                if player.user.username:
                    username = player.user.username
                    players_string += f"{username}\n"
                else:
                    username = f"{player.user.first_name}_{player.user.id}"
                    players_string += f"{username}\n"
                await self.app.store.game.create_player(
                    nickname=username,
                    game_id=game.id
                )

            await self.app.store.tg_api.send_message(
                chat_id=self.update.message.chat.id,
                text=f"Зарегистрированы игроки:"
                     f"\n{players_string}\n\nЕсли вы хотите играть в "
                     f"этом составе, нажмите начать или отмена если не хотите.",
                reply_markup=self.create_markup(
                    (
                        ("Начать", "confirm_game_start"),
                        ("Отмена", "cancel_game_start")
                    )
                )
            )

        except IntegrityError as e:
            self.app.logger.info(e)
            self.app.logger.info("Game with this chat id already exists")
            await self.app.store.tg_api.send_message(
                chat_id=self.update.message.chat.id,
                text="Игра уже запущена, нельзя начать новую, не завершив ее",
            )

    async def get_players(self) -> list[Player]:
        """Вспомогательный метод для получения текущего списка игроков
        в игре
        """

        return await self.app.store.game.get_players_by_game_chat_id(
            self._get_chat_id()
        )

    async def get_player(self) -> Player:
        """
        Метод для получения игрока в текущей игре
        Так как у пользователя в telegram параметр username
        может отсутствовать, проверяет на его наличие.
        В этом случае значение username из модели Players
        берется по параметру first_name
        """
        players = await self.get_players()
        if self.update.callback_query.from_.username:
            p = [
                player for player in players
                if
                player.nickname == self.update.callback_query.from_.username
            ]
            return p[0]
        else:
            p = [
                player for player in players
                if
                player.nickname.startswith(
                    self.update.callback_query.from_.first_name)
            ]
            return p[0]

    async def show_score(self):
        """
        Метод для отправки сообщения содержащего текущее состояние игры
        """
        players = await self.get_players()
        result = ''
        for player in players:
            score = f"Игрок: {player.nickname} | Счет: {player.score}\n"
            result += score
        await self.app.store.tg_api.send_message(
            chat_id=self.update.callback_query.message.chat.id, text=result
        )

    async def stop_game(self) -> None:
        """
        Метод для остановки игры, удаляет текущую игру из БД
        """
        chat_id = self._get_chat_id()
        game = await self.app.store.game.get_game_by_chat_id(
            chat_id=chat_id,
        )
        if game:
            await self.app.store.game.delete_game(
                chat_id=chat_id,
            )
            await self.app.store.tg_api.send_message(
                chat_id=chat_id,
                text="Игра остановлена",
            )

    @staticmethod
    def create_markup(
            data: Sequence[list[str, str] | tuple[str, str]]
    ) -> str:
        """
        Вспомогательный метод для создания inline_keyboard_markup
        """
        inline_markup = [
            [{"text": array[0], "callback_data": array[1]}]
            for array in data
        ]
        r = json.dumps({"inline_keyboard": inline_markup})
        return r

    async def create_game_keyboard(self):
        """
        Метод для создания игровой клавиатуры.
        Клавиатура представляет собой сообщение содержащее inline кнопки,
        примерно такого вида:
        [тема1]
        [стоимость_вопроса_1, стоимость вопроса_2, ... стоимость_вопроса_N]
        [тема2]
        [стоимость_вопроса_1, стоимость вопроса_2, ... стоимость_вопроса_N]
        ...
        [темаN]
        [стоимость_вопроса_1, стоимость вопроса_2, ... стоимость_вопроса_N]

        Кнопка отвечающая за тему не должна выполнять никаких задач, и служит
        только для того, чтобы отображать тему, для этого ее callback_data
        является 'None'.

        Кнопки отображающие стоимости вопросов, проассоциированы с темой под
        которой они находятся. Для того чтобы идентифицировать вопрос при
        нажатии на кнопку стоимости вопроса, callback_data таких кнопок это
        id записи вопроса в БД.
        """
        game_questions = await self.app.store.game.get_game_questions_by_chat_id(
            self._get_chat_id()
        )
        themes = set([q.theme for q in game_questions])
        questions = [filter(lambda x: x.theme == theme, game_questions)
                     for theme in themes]
        result = []
        for item in questions:
            costs = []
            for i in item:
                theme_button = [{"text": i.theme, "callback_data": "None"}]
                if theme_button not in result:
                    result.append(theme_button)
                costs.append({
                    "text": str(i.cost), "callback_data": str(i.question),
                })
            result.append(costs)

        return result

    async def show_keyboard(self, player: Player):
        """
        Метод отправки сообщения содержащего inline клавиатуру с текущими
        темами и вопросами игрового раунда.
        """
        inline_keyboard = {
            "inline_keyboard": await self.create_game_keyboard()
        }

        await self.app.store.tg_api.send_message(
            chat_id=self._get_chat_id(),
            text=f"Игрок {player.nickname} выберете вопрос!",
            reply_markup=json.dumps(inline_keyboard)
        )

    async def choose_first_player(self) -> Player:
        """
        Метод для случайного определения первого игрока в начале игры.
        """
        players = await self.get_players()
        first_player = random.choice(players)
        await self.app.store.tg_api.send_message(
            text=f"Право первого хода предоставляется игроку "
                 f"{first_player.nickname}, выбранному случайно!",
            chat_id=self._get_chat_id()
        )
        return first_player

    async def send_question(self, question_id: int) -> GameQuestion:
        """
        Метод для отправки сообщения содержащего вопрос.
        Также показывает варианты ответов для игроков,
        чтобы они успели подумать, прежде чем кнопки содержащие ответы появятся.
        """
        question = await self.app.store.quizzes.get_question_by_id(question_id)
        await self.app.store.tg_api.send_message(
            chat_id=self._get_chat_id(),
            text=question.title
        )
        answers = "".join([answer.title + "\n" for answer in question.answers])
        await self.app.store.tg_api.send_message(
            chat_id=self._get_chat_id(),
            text=f"Варианты ответа:\n"
                 f"{answers}",
        )
        return question

    async def send_ready_button(self, delay: int = 0):
        """
        Метод для отправки сообщения содержащего кнопку "Ответить".
        При нажатии на нее будет выбран игрок, который отвечает на вопрос в
        текущем раунде. Пока игроки читают вопрос, создается задержка отправки
        этого сообщения. Обязательно использовать этот метод
        с asyncio.create_task()
        :param delay: Время в секундах для установления задержки
        отправки кнопки.
        """
        try:
            chat_id = self.update.callback_query.message.chat.id
            await asyncio.sleep(delay)
            await self.app.store.tg_api.send_message(
                chat_id=chat_id,
                text="Нажмите на кнопку если вы готовы ответить",
                reply_markup=self.create_markup(
                    (
                        ("Ответить!", "ready_to_answer"),
                    )
                )
            )
        except Exception as e:
            self.logger.exception(e)

    async def round_handler(self):
        """Логика игры"""
        data = self.update.callback_query.data
        # Для того чтобы определить, является ли callback_data вопросом
        # пробуем привести его к int
        try:
            data = int(data)
        except ValueError:
            ...
        match data:
            # В случае если callback_data удается привести к int
            # задаем пользователю вопрос
            case int():
                game = await self.app.store.game.get_game_by_chat_id(
                    self._get_chat_id())
                last_round = await self.app.store.game.get_game_last_round_by_chat_id(
                    self._get_chat_id()
                )
                # в случае того, что это первый раунд игры,
                # создаем новый раунд
                if not last_round:
                    await self.app.store.game.create_round(
                        count=1,
                        game_id=game.id,
                        current_question=data,
                    )
                await self.send_question(data)
                # Отправка кнопки "Ответить" с задержкой
                asyncio.create_task(self.send_ready_button(1))

            case "ready_to_answer":
                player_ = await self.get_player()
                round_ = await self.app.store.game.get_game_last_round_by_chat_id(
                    self._get_chat_id()
                )
                await self.app.store.game.update_round_answering_player(
                    id=round_.id,
                    answering_player=player_.nickname,
                )
                question = await self.app.store.quizzes.get_question_by_id(
                    round_.id)
                answers = [
                    [answer.title, str(answer.is_correct).lower() + "_answer"]
                    for answer in question.answers]
                await self.app.store.tg_api.send_message(
                    chat_id=self.update.callback_query.message.chat.id,
                    text=f"Игрок {player_.nickname} выберите вариант ответа",
                    reply_markup=self.create_markup(
                        answers
                    )
                )
            case "true_answer":
                await self.app.store.tg_api.send_message(
                    self._get_chat_id(),
                    text="Вы ответили правильно!!!"
                )

            case "false_answer":
                await self.app.store.tg_api.answer_callback_query(
                    callback_query_id=self.update.callback_query.id,
                    text="Вы уже отвечали в этом раунде, поэтому больше"
                         "не можете, дождитесь следующего раунда",
                )
                await self.app.store.tg_api.send_message(
                    self._get_chat_id(),
                    text="К сожалению ответ неверный! "
                         "Вы больше не участвуете в этом раунде"
                )
                await self.app.store.tg_api.send_message(
                    self._get_chat_id(),
                    text="Остальные игроки приготовьтесь отвечать..."
                )
                asyncio.create_task(self.send_ready_button(2))

            case _:
                chat_id = self._get_chat_id()
                last_round = await self.app.store.game.get_game_last_round_by_chat_id(
                    chat_id
                )
                if not last_round:
                    await self.app.store.game.generate_game_questions(chat_id)
                    player = await self.choose_first_player()
                    await self.show_keyboard(player)

    def _get_chat_id(self) -> int:
        """
        Вспомогательная функция для получения chat_id текущего события
        """
        if self.update.callback_query:
            return self.update.callback_query.message.chat.id
        elif self.update.message:
            return self.update.message.chat.id

    async def _check_is_player_answered(self, player):
        ...
