import asyncio
import json
import random
import typing
from enum import Enum
from logging import getLogger
from typing import Sequence

from sqlalchemy.exc import IntegrityError

from app.store.telegram_api.dataclasses import (
    Update,
    User,
    ChatMemberAdministrator
)

if typing.TYPE_CHECKING:
    from app.web.app import Application


class Emoji(Enum):
    QUESTION = "\U00002753"
    RED_CROSS = "\U0000274C"
    CHECK_MARK = "\U00002705"


class Commands(Enum):
    START = "/start", "/start@SvoyaIgraQuiz_bot"
    START_GAME = "/start_game", "/start_game@SvoyaIgraQuiz_bot"
    STOP_GAME = "/stop_game", "/stop_game@SvoyaIgraQuiz_bot"
    INFO = "/info", "/info@SvoyaIgraQuiz_bot"
    THEMES = "/themes", "/themes@SvoyaIgraQuiz_bot"


class CallbackQueryDatas(Enum):
    CONFIRM_GAME_START = "confirm_game_start"
    REGISTER_NEW_PLAYER = "register_new_player"
    READY_TO_ANSWER = "ready_to_answer"
    NULL = "null"


class Bot:

    def __init__(self, app: "Application"):
        self.app = app
        self.update: Update | None = None
        self.logger = getLogger("Bot")

    def _get_chat_id(self) -> int:
        """Вспомогательный метод для получения chat_id текущего события"""
        if self.update.callback_query:
            return self.update.callback_query.message.chat.id
        elif self.update.message:
            return self.update.message.chat.id

    def _parse_command(self) -> str:
        """
        Вспомогательный метод для распознавания команды для бота из
        сообщения
        """
        for entity in self.update.message.entities:
            if entity.type == "bot_command":
                command = self.update.message.text[
                          entity.offset: entity.offset + entity.length
                          ]
                return command

    async def _get_group_creator(self) -> ChatMemberAdministrator:
        """
        Метод для нахождения создателя группы, нужен для того, чтобы только
        создатель группы мог нажать на кнопку "Начать игру".
        """
        admins = await self.app.store.tg_api.get_chat_admins(
            chat_id=self._get_chat_id()
        )
        for admin in admins:
            if admin.status == "creator":
                return admin

    def _check_is_message_from_group(self) -> bool:
        """
        Метод для определения пришло ли сообщение из группы или нет.
        Нужно для того, чтобы начать игру можно было только в группах.
        """
        type_ = self.update.message.chat.type
        return type_ == 'supergroup' or type_ == 'group'

    async def send_message(self, text: str, markup: str | None = None):
        """
        Вспомогательный метод для отправки сообщения
        markup - параметр для отправки inline кнопок вместе с сообщением.
        """
        kwargs = {
            "chat_id": self._get_chat_id(),
            "text": text,
        }
        if markup:
            kwargs["reply_markup"] = markup
        # sleep это костыль, чтобы немножко снизить количество сообщений
        # в секунду и не блокироваться телегой
        await asyncio.sleep(0.1)
        await self.app.store.tg_api.send_message(**kwargs)

    async def show_alert(self, text: str):
        """Вспомогательная функция для показа alert"""
        await self.app.store.tg_api.answer_callback_query(
            callback_query_id=self.update.callback_query.id, text=text,
            show_alert=True
        )

    @staticmethod
    def create_markup(data: Sequence[list[str, str] | tuple[str, str]]) -> str:
        """
        Вспомогательный метод для создания inline_keyboard_markup
        """
        inline_markup = [
            [{"text": array[0], "callback_data": array[1]}] for array in data
        ]
        return json.dumps({"inline_keyboard": inline_markup})

    async def choose_winner(self):
        """
        Метод для определения победителя в конце игры
        В случае наличия более одного победителя объявляет ничью между ними
        """
        winners = await self.app.store.game.get_player_winner(
            chat_id=self._get_chat_id()
        )

        if len(winners) == 1:
            winner, score = winners[0]
            await self.send_message(
                f"Победил(а) @{winner} со счетом {score}"
            )
        else:
            winners_str = ''
            for winner in winners:
                winners_str += f"@{winner[0]} "
            await self.send_message(
                f"У нас возникла ничья между игроками:\n {winners_str}\n"
                f"набравших {winners[0][1]} очков!"
                f"Победила дружба, купите друг другу "
                f"бутылочку пивка чтобы отметить :)"
            )

    async def finish_game(self):
        """
        Метод для окончания игры.
        Объявляет победителя и удаляет сыгранную игру.
        """
        await self.send_message(
            text="Вопросов больше не осталось! Подводим итоги игры")

        await self.choose_winner()
        chat_id = self._get_chat_id()

        await self.app.store.game.update_game_finished_status(
            chat_id=chat_id,
            is_finished=True
        )
        await self.app.store.game.delete_game_chat_id(
            chat_id=self._get_chat_id()
        )

    async def stop_game(self):
        """
        Метод для досрочной остановки игры.
        Остановить игру может только владелец группы.
        """
        game = await self.app.store.game.get_game(
            chat_id=self._get_chat_id()
        )
        group_owner = await self._get_group_creator()
        from_id = self.update.message.from_.id
        if game and group_owner.user.id == from_id:
            await self.send_message("Игра была досрочно остановлена")
            scores = await self.get_scores()
            await self.send_message(f"Результаты игры:\n"
                                    f"{scores}")
            await self.app.store.game.delete_game(
                chat_id=self._get_chat_id()
            )
        elif game and group_owner.user.id != from_id:
            nickname = group_owner.user.username if \
                group_owner.user.username else \
                group_owner.user.first_name
            await self.send_message(
                f"Досрочно остановить игру может только создатель "
                f"группы @{nickname}"
            )
        else:
            await self.send_message(
                "Игра не была создана, нечего останавливать")

    async def send_question_keyboard(self):
        """
        Метод отправки игровой клавиатуры содержащей темы и стоимости вопросов
        для выбора.
        """
        chat_id = self._get_chat_id()
        questions = await self.app.store.game.get_game_questions(
            chat_id=chat_id
        )
        if not questions:
            await self.finish_game()
        else:
            inline_markup = []
            for theme in questions:
                inline_markup.append([{"text": theme, "callback_data": "null"}])

                costs = [{"text": d["cost"], "callback_data": d["question_id"]}
                         for d in questions[theme]]

                inline_markup.append(costs)

            markup = json.dumps({"inline_keyboard": inline_markup})
            question_chooser_player = \
                await self.app.store.game.get_question_chooser_player(chat_id)

            await self.send_message(
                text=f"Вопрос выбирает игрок "
                     f"@{question_chooser_player.nickname}",
                markup=markup
            )

    async def send_ready_button(self):
        """Метод для отправки кнопки Ответить"""
        await self.send_message(
            "Нажмите на кнопку если готовы отвечать",
            markup=self.create_markup(
                (
                    ("Ответить", "ready_to_answer"),
                )
            )
        )

    async def send_question(self, question_id: int):
        """
        Метод отправляет вопрос в чат после нажатия на кнопку содержащую
        стоимость вопроса.
        Удаляет сообщение со списком вопросов
        """
        chat_id = self._get_chat_id()
        user = self.get_user_data()
        player = await self.app.store.game.get_game_player(
            chat_id=chat_id,
            tg_id=user.id
        )
        if player.is_question_chooser:
            await self.app.store.tg_api.delete_message(
                message=self.update.callback_query.message
            )
            question = await self.app.store.quizzes.get_question_by_id(
                question_id
            )
            theme = await self.app.store.quizzes.get_theme_by_id(
                question.theme_id)
            await self.app.store.game.update_game_question_state(
                question_id=question_id,
                chat_id=chat_id,
                is_current=True,
            )
            await self.send_message(
                text=f"Тема: {theme.title}\nСтоимость: {question.cost}\n"
                     f"{Emoji.QUESTION.value}{question.title}"
            )

            await self.send_ready_button()
        else:
            await self.show_alert(
                "Сейчас не ваша очередь выбирать вопрос"
            )

    def get_user_data(self) -> User:
        """Возвращает User в зависимости от типа update"""
        user = None
        if self.update.callback_query:
            user = self.update.callback_query.from_
        elif self.update.message:
            user = self.update.message.from_

        if user.username is None:
            user.username = f"{user.first_name}_{user.id}"

        return user

    async def create_player(self):
        """Создает нового игрока, связанного с текущей игрой"""
        game = await self.app.store.game.get_game(
            chat_id=self._get_chat_id(),
        )

        if game:
            user = self.get_user_data()
            try:
                player = await self.app.store.game.create_player(
                    tg_id=user.id,
                    nickname=user.username,
                )

            except IntegrityError:
                player = await self.app.store.game.get_player(user.id)

            try:
                await self.app.store.game.create_game_player(
                    game=game,
                    player=player,
                )
                await self.show_alert("Вы успешно зарегистрировались "
                                      "дождитесь начала игры")

                await self.send_message(
                    f"Зарегистрирован игрок @{player.nickname}")
            except IntegrityError:
                await self.show_alert(
                    text="Вы уже зарегистрированы, дождитесь начала игры"
                )

        else:
            await self.show_alert(
                "Игра не была создана, создайте игру командой /start_game"
            )

    async def start_game(self):
        """
        Метод для начала игры после ввода команды "/start_game"
        Создает игру в БД.
        """
        try:
            await self.app.store.game.create_game(chat_id=self._get_chat_id())
            await self.send_message(
                text="Игра создана, для участия в качестве "
                     "игрока нажмите кнопку зарегистрироваться. "
                     "Когда все игроки зарегистрированы владелец группы "
                     "должен нажать кнопку Начать игру"
            )
            await self.send_message(
                text="Нажмите для регистрации",
                markup=self.create_markup(
                    (
                        ("Зарегистрироваться", "register_new_player"),
                        ("Начать игру", "confirm_game_start"),
                    )
                ),
            )

        except IntegrityError:
            await self.send_message(
                text="Игра уже создана нельзя начать новую не завершив "
                     "эту игру.",
            )

    async def confirm_game_start(self):
        """
            Метод который непосредственно запускает игру после
        нажатия кнопки "Начать игру".
            Если на кнопку жмет не владелец группы, игра не запустится, а ему
        будет показано всплывающее окно.
            Также выбирает случайного игрока, который будет первым выбирать
        вопрос.
        """
        group_owner = await self._get_group_creator()
        registered_players = await self.app.store.game.get_game_players(
            chat_id=self._get_chat_id()
        )
        if self.update.callback_query.from_.id == group_owner.user.id and \
                len(registered_players) != 0:
            chat_id = self._get_chat_id()
            await self.app.store.tg_api.delete_message(
                message=self.update.callback_query.message
            )

            await self.send_message(text="Игра началась!")
            players = await self.app.store.game.get_game_players(
                chat_id=chat_id
            )

            text = "Зарегистрированы игроки:\n"
            for player in players:
                text += f"@{player.nickname}\n"
            await self.send_message(text)
            await self.app.store.game.generate_game_questions(
                chat_id=chat_id
            )

            random_player = random.choice(players)
            await self.app.store.game.update_player_answering_or_chooser(
                chat_id=chat_id,
                player_tg_id=random_player.tg_id,
                is_chooser=True
            )
            await self.send_question_keyboard()
        elif self.update.callback_query.from_.id == group_owner.user.id and \
                len(registered_players) == 0:
            await self.show_alert(
                f"Количество зарегистрированных игроков "
                f"{len(registered_players)} нужен хотя бы 1 игрок для начала."
            )
        else:
            nickname = group_owner.user.username if group_owner.user.username \
                else group_owner.user.first_name

            await self.show_alert(
                f"Начать игру может только создатель группы - @{nickname}"
            )

    async def ask_for_answer(self):
        """
            Метод для отправки сообщения в чат, позволяющее пользователю
        который нажал на кнопку "ответить" самым первым написать ответ
        на вопрос.
            В то же время запрещает другим пользователям отвечать на вопрос,
        если сейчас не их очередь.
            Удаляет из чата кнопку Ответить.
        """
        user = self.get_user_data()
        chat_id = self._get_chat_id()
        await self.app.store.tg_api.delete_message(
            message=self.update.callback_query.message
        )
        answering_player = await self.app.store.game.get_answering_player(
            chat_id=chat_id
        )
        if not answering_player:
            await self.app.store.game.update_player_answering_or_chooser(
                chat_id=chat_id,
                player_tg_id=user.id,
                is_answering=True
            )
            player = await self.app.store.game.get_game_player(
                chat_id=chat_id,
                tg_id=user.id
            )
            await self.send_message(text=f"Отвечает @{player.nickname}!\n"
                                         f"Напишите свой ответ в чат")
        else:
            await self.show_alert(text="Вы не можете ответить "
                                       "во время ответа другого игрока")

    async def get_scores(self) -> str:
        """
        Метод для создания текста сообщения, показывающего никнейм
        и очки игроков.
        """
        players = await self.app.store.game.get_game_players(
            chat_id=self._get_chat_id()
        )
        scores_str = "Статистика:\n"
        for player in players:
            scores_str += f"Игрок: @{player.nickname} Счет: {player.score}\n"
        return scores_str

    async def handle_user_answer_message(self, user_answer: str):
        """
            Метод для проверки правильности ответа пользователя
        user_answer это строка с ответом пользователя из чата.

            В случае правильного ответа увеличивает очки пользователя,
        устанавливает статус вопроса как отвеченный, пользователя как
        выбирающего следующий вопрос, и присылает клавиатуру с вопросами

            В случае неправильного ответа снижает очки пользователя и присылает
        кнопку "Ответить", чтобы игроки тоже могли попытаться дать ответ
        """
        chat_id = self._get_chat_id()
        current_question = await self.app.store.game.get_current_game_question(
            chat_id=chat_id
        )
        game = await self.app.store.game.get_game(chat_id=chat_id)
        is_correct = (
                         current_question.answer
                         .lower()
                         .strip()
                     ) == user_answer.lower().strip()
        answering_player = await self.app.store.game.get_answering_player(
            chat_id=chat_id
        )
        previous_question_chooser = \
            await self.app.store.game.get_question_chooser_player(chat_id)

        if answering_player.tg_id == self.update.message.from_.id:
            if is_correct:
                await self.app.store.game.update_game_question_state(
                    chat_id=chat_id,
                    is_current=False,
                    is_answered=True,
                    question_id=current_question.id,
                )

                await self.app.store.game.update_game_player_score(
                    game=game, player_id=answering_player.id,
                    score=current_question.cost
                )

                await self.app.store.game.update_player_answering_or_chooser(
                    chat_id=chat_id,
                    player_tg_id=previous_question_chooser.tg_id,
                    is_answering=False,
                    is_chooser=False,
                )
                await self.app.store.game.update_player_answering_or_chooser(
                    chat_id=chat_id,
                    player_tg_id=answering_player.tg_id,
                    is_answering=False,
                    is_chooser=True,
                )
                scores = await self.get_scores()
                await self.send_message(
                    f"{Emoji.CHECK_MARK.value} Вы ответили правильно! и "
                    f"заработали {current_question.cost} очков\n"
                    f"{scores}")

                if not game.is_finished:
                    await self.send_question_keyboard()

            else:
                await self.app.store.game.update_game_player_score(
                    game=game, player_id=answering_player.id,
                    score=-current_question.cost
                )

                await self.app.store.game.update_player_answering_or_chooser(
                    chat_id=chat_id,
                    player_tg_id=answering_player.tg_id,
                    is_answering=False,
                )
                await self.send_message(
                    f"{Emoji.RED_CROSS.value} К сожалению вы ответили неверно! "
                    f"Вы потеряли {current_question.cost} Очков")

                await self.send_ready_button()

    async def handle_answer_message(self):
        """
        Метод-обертка над обработкой ответа пользователя, проверяет существует
        ли "отвечающий игрок" прежде чем приступить к обработке.
        Нужен для использования в BotManager.
        """
        answering_player = await self.app.store.game.get_answering_player(
            chat_id=self._get_chat_id()
        )
        if answering_player:
            await self.handle_user_answer_message(
                user_answer=self.update.message.text)

    async def send_info_message(self):
        """
        Вспомогательный метод для отправки информации о боте при команде /info
        """
        text = 'Это бот для игры в аналог ТВ-передачи "Своя игра" ' \
               'Игроки соревнуются друг с другом, отвечая на вопросы ' \
               'разных тем, победителем является тот игрок, который ' \
               'набрал наибольшее кол-во очков.\n\n' \
               'Подготовка к игре\n' \
               '1. Создайте группу в которой будет проходить игра;\n' \
               '2. Добавьте участников в нее, а также бота;\n' \
               '3. Сделайте бота администратором группы - ' \
               'это необходимо, чтобы бот имел доступ к сообщениям ' \
               'пользователей, которые будут писать свои ответы ' \
               'на вопросы;\n' \
               '4. Когда вы готовы начинать, введите команду ' \
               '/start_game - это создаст новую игру;\n' \
               '5. Бот отправит сообщение с предложением ' \
               'зарегистрироваться в игре, каждый игрок должен ' \
               'нажать на эту кнопку, чтобы принять участие в игре;\n' \
               '6. Когда все игроки зарегистрированы, владелец ' \
               'группы должен нажать кнопку "Начать игру" - это ' \
               'запустит игровой процесс\n\n' \
               'Игровой процесс и правила:\n' \
               '1. В начале игры будет выбран случайный игрок, ' \
               'который будет выбирать вопрос из предложенных тем.\n' \
               '2. Каждая кнопка с текстом представляет собой тему,' \
               ' каждая кнопка с цифрой под ней, представляет собой' \
               ' вопрос, цифра означает количество очков, которое' \
               ' игрок получит в случае правильного ответа, либо ' \
               'они будут списаны с его счета в случае ' \
               'неправильного;\n' \
               '3. Когда выбирающий игрок нажимает на вопрос, ' \
               'бот отправит текст вопроса, а также кнопку ' \
               '"Ответить"\n' \
               '4. Для того чтобы ответить на вопрос, нужно нажать' \
               ' эту кнопку, тот игрок который первым нажал на кнопку ' \
               'и будет отвечать.\n' \
               '5. Ответ нужно писать в чат текстом, ответы не ' \
               'зависят от регистра или пробелов. ' \
               'Ответ всегда является одним словом.\n' \
               '6. В случае правильного ответа игрок получает право ' \
               'выбрать следующий вопрос.\n' \
               '7. Игра продолжается до тех пор, пока не останется' \
               ' ни одного вопроса\n' \
               '8. Победителем игры будет игрок, набравший самое ' \
               'большое число очков, либо в случае если у двух и' \
               ' более игроков одинаковое количество очков, ' \
               'будет объявлена ничья.'

        await self.send_message(text)

    async def handle_command(self):
        """
        Метод для использования в BotManager
        Парсит команду из сообщения, и решает что делать с каждой из них
        """
        command = self._parse_command()

        if command in Commands.START.value:
            await self.send_message(
                text="Для начала игры добавьте бота в группу, после чего\n"
                     "Обязательно сделайте его администратором группы.\n"
                     "Это нужно чтобы он мог видеть сообщения с ответами\n"
                     "Пользователей.\n"
                     "Далее введите команду /start_game или выберете эту\n"
                     "команду в меню бота, чтобы начать игру"
            )
        elif command in Commands.START_GAME.value:
            if self._check_is_message_from_group():
                await self.start_game()
            else:
                await self.send_message(
                    "Для того чтобы играть, добавьте бота в группу"
                    " и сделайте админом."
                )

        elif command in Commands.STOP_GAME.value:
            if self._check_is_message_from_group():
                await self.stop_game()

        elif command in Commands.INFO.value:
            await self.send_info_message()

        elif command in Commands.THEMES.value:
            theme_titles = await self.app.store.game.get_available_themes()

            msg = 'Список доступных тем:\n\n'
            for title in theme_titles:
                msg += title + "\n"

            await self.send_message(
                text=msg
            )

    async def handle_callback_query(self):
        """
        Метод для работы с событиями нажатия на inline кнопки.
        Нужен для использования в BotManager.
        """
        data = self.update.callback_query.data
        game = await self.app.store.game.get_game(
            chat_id=self._get_chat_id()
        )
        if not game:
            await self.show_alert(
                "Эта игра уже закончилась и больше не доступна"
            )
            return

        try:
            # это нужно для того, чтобы понять что callback_data, является id
            # вопроса и в таком случае отправить в чат вопрос
            data = int(data)
        except ValueError:
            ...
        try:
            match data:
                case int():
                    await self.send_question(data)
                case "confirm_game_start":
                    await self.confirm_game_start()
                case "register_new_player":
                    await self.create_player()
                case "ready_to_answer":
                    await self.ask_for_answer()

                case "null":
                    # null сделан для того, чтобы если пользователь нажмет на
                    # кнопку которая представляет тему, ему было понятно что на
                    # нее жать не надо :)
                    await self.show_alert(
                        "Для того чтобы выбрать вопрос нажмите "
                        "на цифру под темой")
        except Exception as e:
            await self.show_alert(
                "Эта игра уже закончилась и больше не доступна"
            )
            self.logger.exception(e)
