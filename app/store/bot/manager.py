import typing
from logging import getLogger
from app.store.bot.bot import Bot
from app.store.telegram_api.dataclasses import Update

if typing.TYPE_CHECKING:
    from app.web.app import Application


class BotManager:
    def __init__(self, app: "Application"):
        self.app = app
        self.bot = Bot(app)
        self.logger = getLogger("handler")

    async def handle_updates(self, updates: list[Update]):
        for update in updates:
            self.bot.update = update
            if update.callback_query:
                await self.bot.handle_callback_query()

            elif update.message and update.message.entities:
                await self.bot.handle_command()

            elif update.message:
                await self.bot.handle_answer_message()
