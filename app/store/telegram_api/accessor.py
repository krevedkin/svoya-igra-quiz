import typing
from pprint import pprint

from aiohttp import ClientSession, TCPConnector

from app.base.base_accessor import BaseAccessor
from app.store.telegram_api.dataclasses import UpdateObject, Message
from app.store.telegram_api.poller import Poller

if typing.TYPE_CHECKING:
    from app.web.app import Application

URL = f"https://api.telegram.org/bot"


class TelegramApiAccessor(BaseAccessor):
    def __init__(self, app: "Application", *args, **kwargs):
        super().__init__(app, *args, **kwargs)
        self.session: ClientSession | None = None
        self.poller: Poller | None = None
        self.last_update: int = 0
        self.api_path = URL + self.app.config.bot.token

    async def connect(self, app: "Application"):
        self.session = ClientSession(connector=TCPConnector(ssl=False))
        self.poller = Poller(app.store)
        self.logger.info("start polling")
        await self.poller.start()

    async def disconnect(self, app: "Application"):
        self.logger.info("stop polling")
        await self.session.close()

    async def send_message(self, message: Message):
        async with self.session.post(
            self.api_path + "/sendMessage",
            data={
                "chat_id": message.chat_id,
                "text": message.text,
            },
        ) as response:
            res = await response.json()
            return res

    @staticmethod
    async def _create_update_object(updates: dict) -> UpdateObject:
        message = Message(
            message_id=updates["message"]["message_id"],
            chat_id=updates["message"]["chat"]["id"],
            username=updates["message"]["from"]["username"],
            is_bot=updates["message"]["from"]["username"],
            date=updates["message"]["date"],
        )

        if "entities" in updates["message"]:
            message.type_ = updates["message"]["entities"][0]["type"]
        if "text" in updates["message"]:
            message.text = updates["message"]["text"]
        return UpdateObject(update_id=updates["update_id"], message=message)

    async def poll(self) -> list[UpdateObject]:
        async with self.session.get(
            self.api_path + "/getUpdates",
            data={
                "timeout": 5,
                "offset": self.last_update + 1,
            },
        ) as response:
            raw_response = await response.json()
            updates = []

            if raw_response["result"]:
                for update in raw_response["result"]:
                    if "message" in update:
                        update_object = await self._create_update_object(update)
                        updates.append(update_object)
                    else:
                        self.last_update = update["update_id"]

                self.last_update = updates[-1].update_id

            return updates
