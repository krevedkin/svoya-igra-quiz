import typing
from logging import getLogger
from pprint import pprint

from app.store.bot.bot import Bot
from app.store.telegram_api.dataclasses import UpdateObject, Message

if typing.TYPE_CHECKING:
    from app.web.app import Application


class BotManager:
    def __init__(self, app: "Application"):
        self.app = app
        self.bot = Bot(app)
        self.logger = getLogger("handler")

    async def handle_updates(self, updates: list[UpdateObject]):
        if updates:
            for update in updates:
                self.bot.update = update
                match update.message.type_:
                    case 'bot_command':
                        await self.bot.command_handler()
                    case 'text':
                        await self.bot.message_handler()
                    case 'callback':
                        await self.bot.callback_query_handler()
