from contextlib import suppress
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import CHANNEL_ID, CHANNEL_USERNAME


import logging

async def is_subscribed(bot, user_id) -> bool:
    # 1. Try checking with CHANNEL_ID
    if CHANNEL_ID:
        try:
            cid = CHANNEL_ID
            with suppress(ValueError):
                cid = int(str(CHANNEL_ID).strip())
            member = await bot.get_chat_member(cid, user_id)
            return member.status in ("member", "administrator", "creator")
        except Exception as e:
            logging.warning(f"Subscription check failed for ID {CHANNEL_ID}: {e}")

    # 2. Fallback to checking with CHANNEL_USERNAME
    if CHANNEL_USERNAME:
        username = str(CHANNEL_USERNAME).strip().lstrip("@")
        try:
            member = await bot.get_chat_member(f"@{username}", user_id)
            return member.status in ("member", "administrator", "creator")
        except Exception as e:
            logging.error(f"Subscription check failed for Username @{username}: {e}")

    # If no channel configuration is present, default to True
    if not CHANNEL_ID and not CHANNEL_USERNAME:
        return True

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
