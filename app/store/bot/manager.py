import typing
from logging import getLogger
from pprint import pformat
from icecream import ic
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
            # self.logger.info(pformat(update))
            # self.logger.info("---------------------------------------")
            ic(update)
            self.bot.update = update
            if update.callback_query:
                # await self.bot.callback_query_handler()
                await self.bot.handle_callback_query()

            elif update.message and update.message.entities:
                # await self.bot.command_handler()
                await self.bot.handle_command()

            # elif update.message and update.message.new_chat_member:
            #     await self.bot.new_chat_user_handler()
            #
            # elif update.message and update.message.left_chat_member:
            #     await self.bot.left_chat_user_handler()

            elif update.message:
                await self.bot.handle_answer_message()
                # game = await self.app.store.game.get_game_by_chat_id(
                #     update.message.chat.id
                # )
                # if game:
                #     await self.bot.answer_message_handler()
