from enum import Enum
from app.store.telegram_api.dataclasses import (
    User,
    PollOption,
    PollAnswer,
    Poll,
    Chat,
    MessageEntity,
    Message,
    Update,
    CallbackQuery,
    ChatMemberAdministrator,
    ChatMember,
)


class TgTypes(Enum):
    MESSAGE = "message"
    CALLBACK_QUERY = "callback_query"
    POLL = "poll"
    POLL_ANSWER = "poll_answer"
    USERNAME = "username"
    FIRST_NAME = "first_name"
    LAST_NAME = "last_name"
    FROM = "from"
    TEXT = "text"
    ENTITIES = "entities"
    NEW_CHAT_MEMBER = "new_chat_member"
    LEFT_CHAT_MEMBER = "left_chat_member"
    INLINE_MESSAGE_ID = "inline_message_id"
    CHAT_INSTANCE = "chat_instance"
    DATA = "data"


class RequestResponseParser:
    """
    Класс для парсинга данных из telegram.
    Создает объекты для удобного взаимодействия с ними в дальнейшем.
    """

    def parse_update(self, update: dict) -> Update:
        _update = Update(update_id=update["update_id"])

        if "message" in update:
            message = self.parse_message(update["message"])
            _update.message = message

        if "callback_query" in update:
            callback_query = self.parse_callback_query(update["callback_query"])
            _update.callback_query = callback_query

        if "poll" in update:
            poll = self.parse_poll(update["poll"])
            _update.poll = poll

        if "poll_answer" in update:
            poll_answer = self.parse_poll_answer(update["poll_answer"])
            _update.poll = poll_answer

        return _update

    @staticmethod
    def parse_user(user: dict) -> User:
        _user = User(
            id=user["id"], is_bot=user["is_bot"], first_name=user["first_name"]
        )
        if "last_name" in user:
            _user.last_name = user["last_name"]
        if "username" in user:
            _user.username = user["username"]

        return _user

    def parse_chat_member(self, chat_member: dict) -> ChatMember:
        user = self.parse_user(chat_member["user"])
        return ChatMember(
            status=chat_member["status"],
            id=user.id,
            is_bot=user.is_bot,
            first_name=user.first_name,
            last_name=user.last_name,
            username=user.username,
        )

    @staticmethod
    def parse_poll_option(poll_option: dict) -> PollOption:
        _poll_option = PollOption(
            text=poll_option["text"], voter_count=poll_option["voter_count"]
        )

        return _poll_option

    def parse_poll_answer(self, poll_answer: dict):
        _poll_answer = PollAnswer(
            poll_id=poll_answer["poll_id"],
            user=self.parse_user(poll_answer["user"]),
            option_ids=poll_answer["option_ids"],
        )
        return poll_answer

    def parse_poll(self, poll: dict) -> Poll:
        options = [self.parse_poll_option(option) for option in poll["options"]]
        _poll = Poll(
            id=poll["id"],
            question=poll["question"],
            options=options,
            total_voter_count=poll["total_voter_count"],
            is_closed=poll["is_closed"],
            type=poll["type"],
            allows_multiple_answers=poll["type"],
            is_anonymous=poll["is_anonymous"],
        )

        return _poll

    @staticmethod
    def parse_chat(chat: dict) -> Chat:
        _chat = Chat(id=chat["id"], type=chat["type"])

        if "username" in chat:
            _chat.username = chat["username"]

        if "first_name" in chat:
            _chat.first_name = chat["first_name"]

        if "last_name" in chat:
            _chat.last_name = chat["last_name"]

        return _chat

    @staticmethod
    def parse_message_entity(message_entity: dict) -> MessageEntity:
        _message_entity = MessageEntity(
            type=message_entity["type"],
            offset=message_entity["offset"],
            length=message_entity["length"],
        )
        return _message_entity

    def parse_message(self, message: dict) -> Message:
        _message = Message(
            message_id=message["message_id"],
            date=message["date"],
            chat=self.parse_chat(message["chat"]),
        )

        if "from" in message:
            _message.from_ = self.parse_user(message["from"])

        if "text" in message:
            _message.text = message["text"]

        if "entities" in message:
            _message.entities = [
                self.parse_message_entity(entinity) for entinity in
                message["entities"]
            ]

        if "poll" in message:
            _message.poll = self.parse_poll(message["poll"])

        if "new_chat_member" in message:
            _message.new_chat_member = self.parse_user(
                message["new_chat_member"])

        if "left_chat_member" in message:
            _message.left_chat_member = self.parse_user(
                message["left_chat_member"])

        return _message

    def parse_callback_query(self, callback_query: dict) -> CallbackQuery:
        _callback_query = CallbackQuery(
            id=callback_query["id"],
            from_=self.parse_user(callback_query["from"]),
            message=self.parse_message(callback_query["message"]),
        )

        if "inline_message_id" in callback_query:
            _callback_query.inline_message_id = callback_query[
                "inline_message_id"]

        if "chat_instance" in callback_query:
            _callback_query.chat_instance = callback_query["chat_instance"]

        if "data" in callback_query:
            _callback_query.data = callback_query["data"]

        return _callback_query

    def parse_chat_administrator(self, admin: dict):
        return ChatMemberAdministrator(
            status=admin["status"], user=self.parse_user(admin["user"])
        )

    @staticmethod
    def parse_get_me(get_me: dict):
        return User(
            id=get_me["id"],
            is_bot=get_me["is_bot"],
            first_name=get_me["first_name"],
            username=get_me["username"],
        )
