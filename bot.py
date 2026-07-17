import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from handlers import user, admin, group

from config import BOT_TOKEN, CHANNEL_ID, DIVIDER, SUPPORT_USERNAME
import database as db
from middlewares import AntiSpamMiddleware, BanMiddleware

logging.basicConfig(level=logging.INFO)


async def main():
    await db.init_db()

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    # middlewares (ban check first, then anti-spam)
    dp.update.middleware(BanMiddleware())
    dp.update.middleware(AntiSpamMiddleware())

    dp.include_router(admin.router)
    dp.include_router(group.router) 
    dp.include_router(user.router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

