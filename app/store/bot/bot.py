import json
import typing
from pprint import pprint

from app.store.telegram_api.dataclasses import UpdateObject, Message

if typing.TYPE_CHECKING:
    from app.web.app import Application


class Bot:
    def __init__(self, app: "Application"):
        self.app = app
        self.update: UpdateObject | None = None

    async def command_handler(self):
        match self.update.message.text:
            case "/start":
                await self.start()
            case "/start_game":
                await self.start_game()
            case "/stop_game":
                await self.stop_game()
            case "/info_game":
                await self.info_game()
            case "/show":
                await self.show_keyboard()

    async def message_handler(self):
        await self.app.store.tg_api.send_message(
            Message(
                chat_id=self.update.message.chat_id,
                text="Это просто сообщение"
            )
        )

    async def callback_query_handler(self):
        if self.update.callback_query:
            match self.update.callback_query.data:
                case "q11":
                    await self.app.store.tg_api.send_message(
                        Message(chat_id=self.update.message.chat_id,
                                text=f"{self.update.message.text} за {self.update.callback_query.data}", )
                    )
                    await self.app.store.tg_api.delete_message(
                        message=self.update.message)
                case "q12":
                    await self.app.store.tg_api.send_message(
                        Message(chat_id=self.update.message.chat_id,
                                text=f"{self.update.message.text} за {self.update.callback_query.data}", )
                    )
                    await self.app.store.tg_api.delete_message(
                        message=self.update.message)
                case "q13":
                    await self.app.store.tg_api.send_message(
                        Message(chat_id=self.update.message.chat_id,
                                text=f"{self.update.message.text} за {self.update.callback_query.data}", )
                    )
                    await self.app.store.tg_api.delete_message(
                        message=self.update.message)
                case "q14":
                    await self.app.store.tg_api.send_message(
                        Message(chat_id=self.update.message.chat_id,
                                text=f"{self.update.message.text} за {self.update.callback_query.data}", )
                    )
                    await self.app.store.tg_api.delete_message(
                        message=self.update.message)
                case "q15":
                    await self.app.store.tg_api.send_message(
                        Message(chat_id=self.update.message.chat_id,
                                text=f"{self.update.message.text} за {self.update.callback_query.data}", )
                    )
                    await self.app.store.tg_api.delete_message(
                        message=self.update.message)

    async def start(self):
        await self.app.store.tg_api.send_message(
            Message(
                chat_id=self.update.message.chat_id,
                text="Для начала игры создайте группу и добавьте бота туда,"
                     "После чего введите команду /start_game",
            )
        )

    async def start_game(self):
        await self.app.store.tg_api.send_message(
            Message(
                chat_id=self.update.message.chat_id,
                text="Ура вы начали игру",
            )
        )

    async def stop_game(self):
        await self.app.store.tg_api.send_message(
            Message(
                chat_id=self.update.message.chat_id,
                text="Вы закончили игру!",
            )
        )

    async def info_game(self):
        await self.app.store.tg_api.send_message(
            Message(
                chat_id=self.update.message.chat_id,
                text="Информация об игре:",
            )
        )

    def create_markup(self, themes, questions):
        markup = {}
        inline_keyboard = []
        for theme_idx, theme in enumerate(themes):
            _theme = [{"text": theme, "callback_data": "Dummy"}]
            inline_keyboard.append(_theme)

            _questions = [
                {"text": q, "callback_data": f"q{theme_idx + 1}{i + 1}"} for i, q in
                enumerate(questions)
            ]
            inline_keyboard.append(_questions)

        markup["inline_keyboard"] = inline_keyboard
        return markup

    async def show_keyboard(self):

        themes = ["Космос", "Наука", "Музыка", "Водопады"]
        questions = ["100", "200", "300", "400", "500"]

        await self.app.store.tg_api.send_message(
            message=Message(
                chat_id=self.update.message.chat_id,
                text=f"Игрок выберете вопрос!",
            ),
            reply_markup=json.dumps(self.create_markup(themes, questions))
        )
