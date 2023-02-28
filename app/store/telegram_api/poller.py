import asyncio
from asyncio import Task
from logging import getLogger
from pprint import pformat
from typing import Optional

from app.store import Store


class Poller:
    def __init__(self, store: Store):
        self.store = store
        self.is_running = False
        self.poll_task: Optional[Task] = None
        self.logger = getLogger("Poller")

    async def start(self):
        self.is_running = True
        self.poll_task = asyncio.create_task(self.poll())

    async def stop(self):
        self.is_running = False
        await self.poll_task

    async def poll(self):
        while self.is_running:
            try:
                updates = await self.store.tg_api.poll()
                await self.store.bots_manager.handle_updates(updates)
            except Exception as e:
                self.logger.exception(e)
                self.logger.error(pformat(updates))
