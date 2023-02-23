import typing
from aiohttp import ClientSession, TCPConnector

from app.base.base_accessor import BaseAccessor
from app.store.telegram_api.dataclasses import UpdateObject, Message
from app.store.telegram_api.poller import Poller

if typing.TYPE_CHECKING:
    from app.web.app import Application

URL = f'https://api.telegram.org/bot'


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

    async def send_message(self, message: Message):
        async with self.session.post(self.api_path + "/sendMessage", data={
            "chat_id": message.chat_id,
            "text": message.text,
        }) as response:
            res = await response.json()
            return res

    async def poll(self) -> list[UpdateObject] | None:
        async with self.session.get(self.api_path + "/getUpdates",
                                    data={"timeout": 5,
                                          "offset": self.last_update + 1}) as response:
            raw_response = await response.json()
            if raw_response["result"]:
                updates = [
                    UpdateObject(update_id=update["update_id"], message=Message(
                        message_id=update["message"]["message_id"],
                        chat_id=update["message"]["chat"]["id"],
                        username=update["message"]["chat"]["username"],
                        is_bot=update["message"]["from"]["is_bot"],
                        date=update["message"]["date"],
                        text=update["message"]["text"],
                    )) for update in raw_response["result"]]

                self.last_update = updates[-1].update_id
                return updates
