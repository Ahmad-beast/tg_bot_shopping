import asyncio
from contextlib import suppress
from aiogram.exceptions import TelegramBadRequest
from config import SENSITIVE_DELETE_AFTER


async def send_temp(message_obj, text, reply_markup=None, delay=SENSITIVE_DELETE_AFTER):
    msg = await message_obj.answer(text, reply_markup=reply_markup)
    asyncio.create_task(_delete_later(msg, delay))
    return msg


async def _delete_later(msg, delay):
    await asyncio.sleep(delay)
    with suppress(TelegramBadRequest):
        await msg.delete()
