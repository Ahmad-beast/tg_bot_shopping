import re
from contextlib import suppress
from datetime import datetime, timedelta, timezone

from aiogram import Router, F
from aiogram.types import Message, ChatPermissions
from aiogram.enums import ChatType
from aiogram.exceptions import TelegramBadRequest

from config import LINK_MUTE_SECONDS, is_admin

router = Router()

group_filter = F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP})

# Real links only: http(s), www., t.me/, or domain.tld (NOT @usernames or /commands)
LINK_RE = re.compile(
    r"(https?://\S+"
    r"|www\.\S+"
    r"|t\.me/\S+|telegram\.me/\S+"
    r"|\b[a-z0-9][a-z0-9-]*\.(com|net|org|io|me|xyz|co|online|info|link|shop|store|app|site|ru|pk)\b)",
    re.IGNORECASE,
)


def has_link(message: Message) -> bool:
    text = message.text or message.caption or ""

    # Ignore bot commands like /about@shopflixd_bot
    if text.strip().startswith("/"):
        return False

    if LINK_RE.search(text):
        return True

    # Telegram-parsed link entities (real URLs only, not mentions/commands)
    for ent in (message.entities or []) + (message.caption_entities or []):
        if ent.type in ("url", "text_link"):
            return True
    return False


@router.message(group_filter, F.from_user)
async def group_handler(message: Message):
    # store admins exempt
    if is_admin(message.from_user.id):
        return await _maybe_reply(message)

    # group admins exempt
    with suppress(Exception):
        member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
        if member.status in ("administrator", "creator"):
            return await _maybe_reply(message)

    if has_link(message):
        with suppress(TelegramBadRequest):
            await message.delete()

        until = datetime.now(timezone.utc) + timedelta(seconds=LINK_MUTE_SECONDS)
        muted = False
        with suppress(TelegramBadRequest):
            await message.bot.restrict_chat_member(
                chat_id=message.chat.id,
                user_id=message.from_user.id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=until,
            )
            muted = True

        if muted:
            await message.answer(
                f"🔇 <a href='tg://user?id={message.from_user.id}'>"
                f"{message.from_user.first_name}</a> was muted for "
                f"{LINK_MUTE_SECONDS // 60} minute for sending links. 🚫🔗"
            )
        else:
            await message.answer("⚠️ Links are not allowed. (I need admin rights to mute.)")
        return

    await _maybe_reply(message)


async def _maybe_reply(message: Message):
    text = (message.text or "").lower()

    # Help / FAQ replies
    if any(w in text for w in ("help", "madad", "kaise", "how")):
        return await message.reply(
            "💬 <b>How to use:</b>\n"
            "1️⃣ Open the bot privately: /start\n"
            "2️⃣ Tap 🛒 Browse Products\n"
            "3️⃣ Top up balance & buy — instant delivery!\n\n"
            "Need a human? Use 💬 Support inside the bot."
        )
    if "price" in text or "rate" in text:
        return await message.reply(
            "🛍 See live prices in the bot: /start → 🛒 Browse Products."
        )
    if any(w in text for w in ("buy", "order", "purchase")):
        return await message.reply("🛒 Buy here: open /start in private chat with me.")

    # Reply when mentioned or replied to
    bot_user = await message.bot.me()
    mentioned = bot_user.username and f"@{bot_user.username.lower()}" in text
    replied_to_bot = (
        message.reply_to_message
        and message.reply_to_message.from_user
        and message.reply_to_message.from_user.id == bot_user.id
    )
    if mentioned or replied_to_bot:
        await message.reply(
            "👋 Hi! I'm the store bot.\n"
            "Open me privately and tap /start to browse and buy products. 🛍"
        )
