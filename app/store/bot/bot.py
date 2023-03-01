import asyncio
import json
import typing
import random
from asyncio import Task
from logging import getLogger
from pprint import pprint
from typing import Sequence

from sqlalchemy.exc import IntegrityError

from app.game.models import Player, GameQuestion, Game, Round
from app.store.telegram_api.dataclasses import Update

if typing.TYPE_CHECKING:
    from app.web.app import Application


class Bot:
    def __init__(self, app: "Application"):
        self.app = app
        self.update: Update | None = None
        self.logger = getLogger("Bot")
        self.timer_task: Task | None = None

    def parse_command(self) -> str:
        for entity in self.update.message.entities:
            if entity.type == "bot_command":
                command = self.update.message.text[
                    entity.offset : entity.offset + entity.length
                ]
                return command

    async def command_handler(self):
        command = self.parse_command()
        match command:
            case "/start":
                await self.start()
            case "/start_game":
                if not await self.is_bot_admin_of_group():
                    await self.app.store.tg_api.send_message(
                        chat_id=self._get_chat_id(),
                        text="Для начала игры нужно создать группу, добавить туда бота и сделать администратором группы",
                    )
                else:
                    game = await self.start_game()
                    if game:
                        await self.send_register_button()

            case "/stop_game":
                await self.stop_game()
            case "/menu":
                await self.show_game_menu()
            case _:
                print("команды не было")

    async def new_chat_user_handler(self):
        await self.app.store.tg_api.send_message(
            chat_id=self._get_chat_id(),
            text=f"Привет {self.update.message.new_chat_member.username}",
        )
        await self.app.store.tg_api.promote_or_demote_chat_member(
            chat_id=self.update.message.chat.id,
            user_id=self.update.message.new_chat_member.id,
            is_promote=False,
        )

    async def left_chat_user_handler(self):
        await self.app.store.tg_api.send_message(
            chat_id=self._get_chat_id(),
            text=f"Пока {self.update.message.left_chat_member.username}",
        )

    async def answer_message_handler(self):
        player = await self.get_player()
        round_ = await self.app.store.game.get_game_last_round_by_chat_id(
            chat_id=self._get_chat_id()
        )

        if round_.is_button_pressed:
            answer = self.update.message.text
            is_correct = await self.check_answer(round_, answer)

            if is_correct:
                await self.app.store.tg_api.send_message(
                    chat_id=self._get_chat_id(), text="Вы ответили правильно!"
                )
                await self.app.store.game.create_answered_player(
                    round_id=round_.id, player_id=player.id
                )
                await self.app.store.game.update_round_button_pressed_by_toggle(
                    id=round_.id, is_pressed=False
                )

                await self.app.store.game.update_game_question_as_answered(
                    game_id=round_.game_id, question_id=round_.current_question
                )

                await self.change_player_score(True)
                await self.app.store.game.update_round_winner_by_id(
                    round_id=round_.id,
                    player_id=player.id,
                )
                await self.show_keyboard(player=player)

            else:
                await self.app.store.game.create_answered_player(
                    round_id=round_.id, player_id=player.id
                )
                await self.app.store.tg_api.send_message(
                    chat_id=self._get_chat_id(),
                    text="Вы ответили неправильно! Снижаем ваши деньги",
                )
                await self.app.store.tg_api.send_message(
                    chat_id=self._get_chat_id(),
                    text="Остальные игроки приготовьтесь отвечать",
                )

                await self.app.store.game.update_round_button_pressed_by_toggle(
                    id=round_.id, is_pressed=False
                )
                await self.change_player_score(False)
                asyncio.create_task(self.send_ready_button(1))

    async def send_register_button(self):
        """
        Метод для отправки кнопки получения игроков.
        """
        await self.app.store.tg_api.send_message(
            chat_id=self._get_chat_id(),
            text="Нажмите на кнопку для того чтобы зарегистрироваться как игрок",
            reply_markup=self.create_markup(
                (
                    (
                        "Зарегистрироваться",
                        "register",
                    ),
                )
            ),
        )

    async def register_players(self):
        """
        Метод для получения игроков которые будут играть в игру.
        """
        game = await self.app.store.game.get_game_by_chat_id(
            chat_id=self._get_chat_id()
        )

        if self.update.callback_query.from_.username:
            username = self.update.callback_query.from_.username
        else:
            username = self.update.callback_query.from_.first_name + str(
                self.update.callback_query.from_.id
            )
        try:
            await self.app.store.game.create_player(
                game_id=game.id,
                nickname=username,
            )
            await self.app.store.tg_api.answer_callback_query(
                callback_query_id=self.update.callback_query.id,
                show_alert=False,
                text="Вы зарегистрировались как игрок",
            )
            players = await self.get_players()
            players = "".join([player.nickname + "\n" for player in players])

            await self.app.store.tg_api.send_message(
                chat_id=self._get_chat_id(),
                text=f"Зарегистрированы игроки:\n"
                f"{players} \n"
                f"Если готовы начать игру нажмите на кнопку",
                reply_markup=self.create_markup(
                    (
                        ("Начать игру", "confirm_game_start"),
                        ("Отменить игру", "cancel_game_start"),
                    )
                ),
            )
        except IntegrityError:
            self.logger.info("Player with this nickname already exists")
            await self.app.store.tg_api.answer_callback_query(
                callback_query_id=self.update.callback_query.id,
                show_alert=True,
                text="Вы уже зарегистрированы как игрок, ожидайте начала игры",
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
                        text="Игра началась",
                    )
                    first_player = await self.choose_first_player()
                    await self.app.store.game.generate_game_questions(
                        chat_id=self._get_chat_id()
                    )
                    await self.show_keyboard(first_player)
                    await self.round_handler()

                # отмена игры
                case "cancel_game_start":
                    await self.stop_game()
                    await self.app.store.tg_api.send_message(
                        chat_id=self.update.callback_query.message.chat.id,
                        text="Игра была отменена! Напишите "
                        "/start_game чтобы начать заново!",
                    )
                # регистрация участников игры
                case "register":
                    await self.register_players()
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
            ),
        )

    async def start(self):
        """Показывает сообщение при вводе команды /start"""
        await self.app.store.tg_api.send_message(
            chat_id=self.update.message.chat.id,
            text="Для начала игры создайте группу и добавьте бота туда.\n"
            "Установите для бота права администратора. "
            "После этого приглашайте в группу других пользователей, "
            "и тогда "
            "Бот начнет регистрировать их как участников игры "
            "После чего введите команду /start_game когда будете "
            "готовы играть.",
        )

    async def start_game(self) -> bool:
        """
        Создает новую игру, если она уже была создана, игра не создается.
        Создает список игроков состоящих и администраторов чата.
        Отправляет список зарегистрированных игроков с inline кнопками
        для подтверждения запуска игры или отмены
        """

        try:
            await self.app.store.game.create_game(self.update.message.chat.id)
            await self.app.store.tg_api.send_message(
                chat_id=self.update.message.chat.id,
                text="Ура вы начали игру!!!",
            )
            return True

        except IntegrityError as e:
            self.app.logger.info(e)
            self.app.logger.info("Game with this chat id already exists")
            await self.app.store.tg_api.send_message(
                chat_id=self.update.message.chat.id,
                text="Игра уже запущена, нельзя начать новую, не завершив ее",
            )
            return False

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

        for player in players:
            if player.nickname.startswith(self.get_username_of_first_name()):
                return player

    def get_username_of_first_name(self) -> str:
        if self.update.callback_query:
            if self.update.callback_query.from_.username:
                return self.update.callback_query.from_.username
            else:
                return self.update.callback_query.from_.first_name

        elif self.update.message:
            if self.update.message.from_.username:
                return self.update.message.from_.username
            else:
                return self.update.message.from_.first_name

    async def show_score(self):
        """
        Метод для отправки сообщения содержащего текущее состояние игры
        """
        players = await self.get_players()
        result = ""
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
    def create_markup(data: Sequence[list[str, str] | tuple[str, str]]) -> str:
        """
        Вспомогательный метод для создания inline_keyboard_markup
        """
        inline_markup = [
            [{"text": array[0], "callback_data": array[1]}] for array in data
        ]
        r = json.dumps({"inline_keyboard": inline_markup})
        return r

    async def create_game_keyboard(self) -> list[list[dict]]:
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
        questions = [
            list(filter(lambda x: x.theme == theme, game_questions)) for theme in themes
        ]
        result = []
        costs = []
        for questions_list in questions:
            for question in questions_list:
                if question.theme not in result:
                    result.append(question.theme)

                costs.append(
                    {
                        "text": str(question.cost),
                        "callback_data": str(question.question_id),
                    }
                )
            result.append(costs[:])
            costs.clear()

        for i, item in enumerate(result):
            if isinstance(item, str):
                result[i] = [
                    {
                        "text": item,
                        "callback_data": "None",
                    }
                ]

        return result

    async def show_keyboard(self, player: Player):
        """
        Метод отправки сообщения содержащего inline клавиатуру с текущими
        темами и вопросами игрового раунда.
        """
        inline_keyboard = {"inline_keyboard": await self.create_game_keyboard()}

        await self.app.store.tg_api.send_message(
            chat_id=self._get_chat_id(),
            text=f"Игрок {player.nickname} выберете вопрос!",
            reply_markup=json.dumps(inline_keyboard),
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
            chat_id=self._get_chat_id(),
        )
        return first_player

    async def send_question(self, question_id: int) -> GameQuestion:
        """
        Метод для отправки сообщения содержащего вопрос.
        """
        question = await self.app.store.quizzes.get_question_by_id(question_id)
        await self.app.store.tg_api.send_message(
            chat_id=self._get_chat_id(), text=question.title
        )

        await self.app.store.tg_api.send_message(
            chat_id=self._get_chat_id(), text="У вас 10 секунд на размышление!"
        )
        asyncio.create_task(self.send_ready_button(1))
        self.timer_task = asyncio.create_task(self.create_timer(5))

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
            await asyncio.sleep(delay)
            await self.app.store.tg_api.send_message(
                chat_id=self._get_chat_id(),
                text="Нажмите на кнопку если вы готовы ответить",
                reply_markup=self.create_markup((("Ответить!", "ready_to_answer"),)),
            )
        except Exception as e:
            self.logger.exception(e)

    async def create_new_round(self, question_id: int) -> Round:
        last_round = await self.app.store.game.get_game_last_round_by_chat_id(
            chat_id=self._get_chat_id()
        )
        game = await self.app.store.game.get_game_by_chat_id(
            chat_id=self._get_chat_id()
        )
        if not last_round:
            round_ = await self.app.store.game.create_round(
                count=1, game_id=game.id, current_question=question_id
            )

        else:
            round_ = await self.app.store.game.create_round(
                count=last_round.count + 1,
                game_id=game.id,
                current_question=question_id,
            )
        return round_

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
                await self.app.store.tg_api.delete_message(
                    self.update.callback_query.message
                )
                await self.send_question(data)
                await self.create_new_round(data)

            case "ready_to_answer":
                player_ = await self.get_player()
                round_ = await self.app.store.game.get_game_last_round_by_chat_id(
                    self._get_chat_id()
                )
                await self.app.store.game.update_round_button_pressed_by_toggle(
                    id=round_.id, is_pressed=True
                )
                is_answered = await self.check_is_player_answered(player_, round_)
                if not is_answered:
                    await self.app.store.game.update_round_answering_player(
                        id=round_.id,
                        answering_player=player_.id,
                    )

                    await self.app.store.tg_api.send_message(
                        chat_id=self._get_chat_id(),
                        text=f"Игрок {player_.nickname} напишите свой ответ",
                    )
                else:
                    await self.app.store.tg_api.answer_callback_query(
                        callback_query_id=self.update.callback_query.id,
                        text="Вы уже отвечали в этом раунде, дождитесь следующего",
                        show_alert=True,
                    )

    def _get_chat_id(self) -> int:
        """
        Вспомогательная функция для получения chat_id текущего события
        """
        if self.update.callback_query:
            return self.update.callback_query.message.chat.id
        elif self.update.message:
            return self.update.message.chat.id

    async def check_answer(self, round: Round, answer: str) -> bool:
        question = await self.app.store.quizzes.get_question_by_id(
            round.current_question
        )
        return question.answer.lower() == answer.lower()

    async def is_bot_admin_of_group(self) -> bool:
        """
        Метод для проверки является ли бот администратором чата
        """
        chat_id = self._get_chat_id()
        bot = await self.app.store.tg_api.get_me()

        user_member = await self.app.store.tg_api.get_chat_member(
            chat_id=chat_id,
            user_id=bot.id,
        )

        return user_member.status == "administrator"

    async def check_is_player_answered(self, player: Player, round_: Round) -> bool:
        answered_player = await self.app.store.game.get_answered_player_by_round_id(
            round_.id
        )
        if not answered_player:
            return False

        return answered_player.player_id == player.id

    async def change_player_score(self, is_correct: bool):
        round_ = await self.app.store.game.get_game_last_round_by_chat_id(
            chat_id=self._get_chat_id()
        )
        question = await self.app.store.quizzes.get_question_by_id(
            id=round_.current_question
        )

        if is_correct:
            score = int(question.cost)
        else:
            score = -int(question.cost)
        await self.app.store.game.update_player_score_by_id(
            id=round_.answering_player, score=score
        )

    async def create_timer(self, delay: int):
        chat_id = self._get_chat_id()
        await asyncio.sleep(delay)
        round_ = await self.app.store.game.get_game_last_round_by_chat_id(
            chat_id=chat_id
        )
        if not round_.answering_player:
            await self.app.store.tg_api.send_message(
                chat_id=chat_id,
                text="Никто не ответил на вопрос переходим к следующему",
            )
            await self.app.store.game.update_game_question_as_answered(
                game_id=round_.game_id, question_id=round_.current_question
            )

            player = await self.app.store.game.get_last_round_winner(chat_id=chat_id)
            await self.show_keyboard(player=player)
