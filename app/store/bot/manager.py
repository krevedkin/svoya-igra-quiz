import typing
from logging import getLogger

from app.store.telegram_api.dataclasses import UpdateObject, Message

if typing.TYPE_CHECKING:
    from app.web.app import Application


class BotManager:
    def __init__(self, app: "Application"):
        self.app = app
        self.bot = None
        self.logger = getLogger("handler")

    async def handle_updates(self, updates: list[UpdateObject]):
        if updates:
            for update in updates:
                await self.app.store.tg_api.send_message(
                    Message(
                        chat_id=update.message.chat_id,
                        text="Привет!",
                    )
                )
