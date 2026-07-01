import asyncio
import logging
from contextlib import suppress

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from handlers import user, admin, group

from config import BOT_TOKEN, CHANNEL_ID, DIVIDER, SUPPORT_USERNAME
import database as db
import keyboards as kb
from middlewares import AntiSpamMiddleware, BanMiddleware

logging.basicConfig(level=logging.INFO)


async def channel_daily_digest(bot: Bot):
    """Periodically posts store status updates to the channel every 12 hours."""
    # Wait a few seconds on startup
    await asyncio.sleep(15)
    
    while True:
        if CHANNEL_ID:
            with suppress(Exception):
                # Fetch all products
                products = await db.get_products()
                if products:
                    lines = []
                    for p in products:
                        pid, emoji, name, price, desc, _ = p
                        cnt = await db.stock_count(pid)
                        if cnt > 0:
                            stock_str = f"🟢 <b>In Stock</b> ({cnt})"
                        else:
                            stock_str = "🔴 <b>Out of Stock</b>"
                        
                        price_str = "Free 🎁" if price == 0 else f"${price:.2f}"
                        lines.append(f"{emoji} <b>{name}</b> • {price_str} ({stock_str})")
                    
                    body = "\n".join(lines)
                    msg = (
                        f"🏪 <b>CURRENT STORE STATUS</b>\n"
                        f"{DIVIDER}\n\n"
                        f"Here is our active inventory availability:\n\n"
                        f"{body}\n\n"
                        f"{DIVIDER}\n"
                        f"💬 <b>Support:</b> @{SUPPORT_USERNAME}\n"
                        f"🛒 <b>Shop directly via the bot!</b>"
                    )
                    
                    await bot.send_message(CHANNEL_ID, msg, reply_markup=kb.buy_now_kb())
        # Sleep for 12 hours (12 * 3600 seconds)
        await asyncio.sleep(12 * 3600)


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

    # Start automated background channel posts
    asyncio.create_task(channel_daily_digest(bot))

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
