from dataclasses import dataclass


@dataclass
class User:
    id: int
    is_bot: bool
    first_name: str
    last_name: str | None = None
    username: str | None = None


@dataclass
class ChatMember(User):
    status: str = "member"


@dataclass
class PollOption:
    text: str
    voter_count: int


@dataclass
class PollAnswer:
    poll_id: int
    user: User
    option_ids: list[int]


@dataclass
class Poll:
    id: int
    question: str
    options: list[PollOption]
    total_voter_count: int
    is_closed: bool
    is_anonymous: bool
    type: bool
    allows_multiple_answers: bool


@dataclass
class Chat:
    id: int
    type: str
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None


@dataclass
class MessageEntity:
    type: str
    offset: int
    length: int


@dataclass
class Message:
    message_id: int
    date: int
    chat: Chat
    from_: User | None = None
    text: str | None = None
    entities: list[MessageEntity] | None = None
    poll: Poll | None = None
    new_chat_member: User = None
    left_chat_member: User = None


@dataclass
class CallbackQuery:
    id: int
    from_: User
    message: Message
    inline_message_id: str | None = None
    chat_instance: str | None = None
    data: str | None = None


@dataclass
class Update:
    update_id: int
    message: Message | None = None
    poll: Poll | None = None
    poll_answer: PollAnswer | None = None
    callback_query: CallbackQuery | None = None


@dataclass
class ChatMemberAdministrator:
    status: str
    user: User
