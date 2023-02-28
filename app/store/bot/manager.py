import typing
from logging import getLogger
from pprint import pformat

from app.store.bot.bot import Bot
from app.store.telegram_api.dataclasses import Update, Message

if typing.TYPE_CHECKING:
    from app.web.app import Application


class BotManager:
    def __init__(self, app: "Application"):
        self.app = app
        self.bot = Bot(app)
        self.logger = getLogger("handler")

    async def handle_updates(self, updates: list[Update]):
        for update in updates:
            self.logger.info(pformat(update))
            self.logger.info("---------------------------------------")
            self.bot.update = update
            if update.callback_query:
                await self.bot.callback_query_handler()
            elif update.message and update.message.entities:
                await self.bot.command_handler()
