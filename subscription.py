from contextlib import suppress
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import CHANNEL_ID, CHANNEL_USERNAME


async def is_subscribed(bot, user_id) -> bool:
    if not CHANNEL_ID:
        return True  # force-join disabled if no channel set
    with suppress(Exception):
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ("member", "administrator", "creator")
    return False


def join_keyboard():
    url = f"https://t.me/{CHANNEL_USERNAME}" if CHANNEL_USERNAME else None
    rows = []
    if url:
        rows.append([InlineKeyboardButton(text="📢 Join Channel", url=url)])
    rows.append([InlineKeyboardButton(text="✅ I Joined", callback_data="check_join")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def join_text():
    return (
        "🔒 <b>Almost there!</b>\n\n"
        "To use this bot, please join our channel first 👇\n\n"
        "After joining, tap <b>✅ I Joined</b>."
    )
