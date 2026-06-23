import time
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update

import database as db
from config import ANTISPAM_RATE, is_admin


class AntiSpamMiddleware(BaseMiddleware):
    def __init__(self):
        self.last_action = {}

    async def __call__(self, handler, event: TelegramObject, data):
        user = data.get("event_from_user")
        if user and not is_admin(user.id):
            now = time.time()
            last = self.last_action.get(user.id, 0)
            if now - last < ANTISPAM_RATE:
                # silently drop spammy updates
                return
            self.last_action[user.id] = now
        return await handler(event, data)


class BanMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: TelegramObject, data):
        user = data.get("event_from_user")
        if user and not is_admin(user.id):
            if await db.is_banned(user.id):
                return  # ignore banned users
        return await handler(event, data)
