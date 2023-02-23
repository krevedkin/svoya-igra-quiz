from dataclasses import dataclass
from datetime import datetime


@dataclass
class Message:
    message_id: int | None = None
    chat_id: int | None = None
    username: str | None = None
    is_bot: bool | None = None
    date: datetime | int | None = None
    text: str | None = None
    type_: str = "text"

    def __post_init__(self):
        if self.date:
            self.date = datetime.fromtimestamp(self.date)


@dataclass
class UpdateObject:
    update_id: int
    message: Message
