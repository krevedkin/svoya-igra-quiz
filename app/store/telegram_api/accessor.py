import json
import typing
from pprint import pprint

from aiohttp import ClientSession, TCPConnector

from app.base.base_accessor import BaseAccessor

from app.store.telegram_api.dataclasses import (
    Update,
    ChatMemberAdministrator,
    Message,
    User,
)
from app.store.telegram_api.poller import Poller
from app.store.telegram_api.update_parser import RequestResponseParser

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
        self.parser = RequestResponseParser()

    async def connect(self, app: "Application"):
        self.session = ClientSession(connector=TCPConnector(ssl=False))
        self.poller = Poller(app.store)
        self.logger.info("start polling")
        await self.poller.start()

    async def disconnect(self, app: "Application"):
        self.logger.info("stop polling")
        await self.session.close()

    async def send_message(self, chat_id: int, text: str, **kwargs):
        """Метод отправки сообщения"""
        data = {
            "chat_id": chat_id,
            "text": text,
        }
        if kwargs:
            data.update(kwargs)
        async with self.session.post(
            self.api_path + "/sendMessage", data=data
        ) as response:
            res = await response.json()
            return res

    async def delete_message(self, message: Message):
        """Метод удаления сообщения"""
        data = {
            "chat_id": message.chat.id,
            "message_id": message.message_id,
        }
        async with self.session.post(
            self.api_path + "/deleteMessage", data=data
        ) as response:
            res = await response.json()
            return res

    async def get_chat_admins(self, chat_id: int) -> list[ChatMemberAdministrator]:
        """
        Метод получения списка администраторов чата, по id чата.
        """
        data = {"chat_id": chat_id}
        async with self.session.get(
            self.api_path + "/getChatAdministrators", data=data
        ) as response:
            res = await response.json()

            return [
                self.parser.parse_chat_administrator(admin)
                for admin in res["result"]
                if not admin["user"]["is_bot"]
            ]

    async def answer_callback_query(
        self, callback_query_id: str, text: str, show_alert: bool = False
    ):
        """Метод обработки callback_query для показа уведомлений в чате"""
        data = {
            "callback_query_id": callback_query_id,
            "text": text,
            "show_alert": show_alert,
        }
        async with self.session.post(
            self.api_path + "/answerCallbackQuery", data=data
        ) as response:
            res = await response.json()
            return res

    async def get_me(self) -> User:
        async with self.session.get(self.api_path + "/getMe") as response:
            result = await response.json()
            user = self.parser.parse_get_me(result["result"])
            return user

    async def get_chat_member(
        self,
        chat_id: int,
        user_id: int,
    ):
        data = {"chat_id": chat_id, "user_id": user_id}
        async with self.session.post(
            self.api_path + "/getChatMember", data=data
        ) as response:
            res = await response.json()
            chat_member = self.parser.parse_chat_member(res["result"])
            return chat_member

    async def promote_or_demote_chat_member(
        self, chat_id: str, user_id: str, is_promote: bool
    ):
        """
        Метод для повышения или понижения прав пользователя чата
        """
        permissions = {
            "can_send_messages": is_promote,
            "can_send_audios": is_promote,
            "can_send_documents": is_promote,
            "can_send_photos": is_promote,
            "can_send_video_notes": is_promote,
            "can_send_voice_notes": is_promote,
            "can_send_polls": is_promote,
            "can_send_other_messages": is_promote,
            "can_add_web_page_previews": is_promote,
            "can_change_info": is_promote,
            "can_invite_users": is_promote,
            "can_pin_messages": is_promote,
            "can_manage_topics": is_promote,
        }
        data: dict = {"chat_id": chat_id, "user_id": user_id}
        data.update(permissions)
        async with self.session.post(
            self.api_path + "/restrictChatMember", data=data
        ) as response:
            res = await response.json()

            return res

    async def poll(self) -> list[Update]:
        """Метод получения обновлений из telegram."""
        async with self.session.get(
            self.api_path + "/getUpdates",
            data={
                "timeout": 5,
                "offset": self.last_update + 1,
                "allowed_updates": json.dumps(
                    [
                        "message",
                        "callback_query",
                        "poll",
                        "poll_answer",
                        "chat_member",
                        "my_chat_member",
                    ]
                ),
            },
        ) as response:
            raw_response = await response.json()
            updates = [
                self.parser.parse_update(update) for update in raw_response["result"]
            ]
            if updates:
                self.last_update = updates[-1].update_id
            return updates
