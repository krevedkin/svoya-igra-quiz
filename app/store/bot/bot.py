import json
import typing

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
        await self.app.store.tg_api.send_message(
            Message(
                chat_id=self.update.message.chat_id,
                text="Вы нажали на кнопку!!!"
            )
        )
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

    async def show_keyboard(self):
        markup = json.dumps(
            {
                "inline_keyboard": [
                    [
                        {"text": "100", "callback_data": "100"},
                        {"text": "200", "callback_data": "200"},
                        {"text": "300", "callback_data": "300"},
                        {"text": "400", "callback_data": "400"},
                        {"text": "500", "callback_data": "500"},
                    ]
                ]
            },
        ),
        themes = ["Животные", "Музыка", "Люди", "Красота", "Живопись"]
        await self.app.store.tg_api.send_message(
            message=Message(
                chat_id=self.update.message.chat_id,
                text=f"Игрок выберите тему!",
            ),
        )
        for theme in themes:
            await self.app.store.tg_api.send_message(
                message=Message(
                    chat_id=self.update.message.chat_id,
                    text=f"Тема: {theme}",
                ),
                reply_markup=markup

            )
