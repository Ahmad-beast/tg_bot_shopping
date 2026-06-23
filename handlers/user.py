from contextlib import suppress

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest
from subscription import is_subscribed, join_keyboard, join_text
from config import CHANNEL_ID  # add to existing config import



import database as db
import keyboards as kb
from config import ADMIN_IDS, DIVIDER, BINANCE_PAY_ID, SUPPORT_USERNAME, MIN_TOPUP, is_admin
from states import TopUp
from utils import send_temp

router = Router()


def home_text(name):
    return (
        f"<b>🛍 DIGITAL STORE</b>\n{DIVIDER}\n\n"
        f"👋 Welcome, <b>{name}</b>!\n\n"
        f"🔥 <b>Premium Digital Services</b>\n\n"
        f"⚡ Instant Delivery\n🔒 Secure Service\n💎 Premium Quality\n\n"
        f"{DIVIDER}\n👇 <i>Select an option below</i>"
    )


@router.message(CommandStart())
async def start(message: Message):
    await db.add_user(message.from_user.id, message.from_user.first_name)
    if not await is_subscribed(message.bot, message.from_user.id):
        return await message.answer(join_text(), reply_markup=join_keyboard())
    await message.answer(
        home_text(message.from_user.first_name),
        reply_markup=kb.main_menu(is_admin(message.from_user.id)),
    )

@router.callback_query(F.data == "check_join")
async def check_join(cb: CallbackQuery):
    if await is_subscribed(cb.bot, cb.from_user.id):
        await cb.message.edit_text(
            home_text(cb.from_user.first_name),
            reply_markup=kb.main_menu(is_admin(cb.from_user.id)),
        )
        await cb.answer("✅ Welcome!")
    else:
        await cb.answer("❌ You haven't joined yet. Please join first.", show_alert=True)




@router.callback_query(F.data == "home")
async def home(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.message.edit_text(
        home_text(cb.from_user.first_name),
        reply_markup=kb.main_menu(is_admin(cb.from_user.id)),
    )
    await cb.answer()


@router.callback_query(F.data == "products")
async def products(cb: CallbackQuery):
    items = await db.get_products()
    if not items:
        await cb.message.edit_text(
            f"<b>🛒 PRODUCT CATALOG</b>\n{DIVIDER}\n\n🚫 No products available yet.",
            reply_markup=kb.back_menu())
        return await cb.answer()
    stocks = {p[0]: await db.stock_count(p[0]) for p in items}
    await cb.message.edit_text(
        f"<b>🛒 PRODUCT CATALOG</b>\n{DIVIDER}\n\nChoose a product to view details 👇",
        reply_markup=kb.products_menu(items, stocks))
    await cb.answer()


@router.callback_query(F.data.startswith("view:"))
async def view_product(cb: CallbackQuery):
    pid = int(cb.data.split(":")[1])
    p = await db.get_product(pid)
    if not p:
        return await cb.answer("Product not found!", show_alert=True)
    cnt = await db.stock_count(pid)
    stock_line = f"📦 <b>In stock:</b> {cnt}" if cnt > 0 else "❌ <b>Out of stock</b>"
    text = (
        f"<b>{p[1]} {p[2].upper()}</b>\n{DIVIDER}\n\n"
        f"{p[4]}\n\n"
        f"💰 <b>Price:</b> ${p[3]:.2f}\n{stock_line}\n\n{DIVIDER}"
    )
    await cb.message.edit_text(text, reply_markup=kb.product_detail_menu(pid, cnt > 0))
    await cb.answer()


@router.callback_query(F.data.startswith("buy:"))
async def buy(cb: CallbackQuery):
    pid = int(cb.data.split(":")[1])
    p = await db.get_product(pid)
    if not p:
        return await cb.answer("Product not found!", show_alert=True)

    cnt = await db.stock_count(pid)
    if cnt <= 0:
        return await cb.answer("❌ Out of stock!", show_alert=True)

    price = p[3]
    bal = await db.get_balance(cb.from_user.id)
    if bal < price:
        return await cb.answer(
            f"❌ Insufficient balance!\nNeed ${price:.2f}, you have ${bal:.2f}.",
            show_alert=True)

    # take one item (the user's unique ID/account)
    content = await db.take_one_stock(pid)
    if content is None:
        return await cb.answer("❌ Out of stock!", show_alert=True)

    await db.update_balance(cb.from_user.id, -price)
    await db.add_order(cb.from_user.id, p[2], content, price)

    delivered = (
        f"<b>✅ PURCHASE SUCCESSFUL</b>\n{DIVIDER}\n\n"
        f"{p[1]} <b>{p[2]}</b>\n\n"
        f"🔐 <b>Your account / ID</b> (auto-deletes soon):\n"
        f"<code>{content}</code>\n\n"
        f"💰 New balance: ${(bal - price):.2f}\n\n"
        f"<i>Saved in My Orders.</i>"
    )
    await send_temp(cb.message, delivered)
    await cb.answer("✅ Purchased! Check the message below.", show_alert=True)

    for admin in ADMIN_IDS:
        if CHANNEL_ID:
            with suppress(Exception):
                await cb.bot.send_message(
                CHANNEL_ID,
                f"🎉 <b>NEW SALE!</b>\n{DIVIDER}\n\n"
                f"{p[1]} <b>{p[2]}</b> just got purchased! ✅\n\n"
                f"🛒 Get yours now in our store bot!"
            )

@router.callback_query(F.data == "balance")
async def balance(cb: CallbackQuery):
    bal = await db.get_balance(cb.from_user.id)
    await cb.message.edit_text(
        f"<b>💰 YOUR BALANCE</b>\n{DIVIDER}\n\n"
        f"💵 Current balance: <b>${bal:.2f}</b>\n\n"
        f"Top up via Binance Pay 👇\n\n{DIVIDER}",
        reply_markup=kb.balance_menu())
    await cb.answer()


@router.callback_query(F.data == "topup")
async def topup(cb: CallbackQuery, state: FSMContext):
    await cb.message.edit_text(
        f"<b>💎 TOP UP — BINANCE PAY</b>\n{DIVIDER}\n\n"
        f"Send your payment to:\n\n"
        f"🆔 Binance Pay ID:\n<code>{BINANCE_PAY_ID}</code>\n\n"
        f"After paying, type the <b>amount</b> you sent (USD, min ${MIN_TOPUP:.0f}):",
        reply_markup=kb.back_menu())
    await state.set_state(TopUp.amount)
    await cb.answer()


@router.message(TopUp.amount)
async def topup_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text)
        if amount < MIN_TOPUP:
            raise ValueError
    except ValueError:
        return await message.answer(f"❌ Enter a valid amount (min ${MIN_TOPUP:.0f}).")
    await state.clear()
    tid = await db.create_topup(message.from_user.id, amount)
    await message.answer(
        "⏳ <b>Top-up request submitted.</b>\n"
        "Admin will verify your Binance payment and credit your balance shortly.",
        reply_markup=kb.back_menu())
    for admin in ADMIN_IDS:
        with suppress(Exception):
            await message.bot.send_message(
                admin,
                f"💳 <b>Top-up request #{tid}</b>\n"
                f"User: <code>{message.from_user.id}</code> ({message.from_user.first_name})\n"
                f"Amount: ${amount:.2f}\n\nVerify on Binance, then Approve/Reject:",
                reply_markup=kb.topup_review_menu(tid))


@router.callback_query(F.data == "orders")
async def orders(cb: CallbackQuery):
    rows = await db.get_user_orders(cb.from_user.id)
    if not rows:
        body = "🗂 No orders found.\n\n<i>Your purchases will appear here.</i>"
    else:
        lines = []
        for r in rows[:15]:
            lines.append(f"• <b>{r[0]}</b> — ${r[2]:.2f}\n   🔐 <code>{r[1]}</code>")
        body = "\n".join(lines)
    await cb.message.edit_text(
        f"<b>📦 MY ORDERS</b>\n{DIVIDER}\n\n{body}\n\n{DIVIDER}",
        reply_markup=kb.back_menu())
    await cb.answer()


@router.callback_query(F.data == "support")
async def support(cb: CallbackQuery):
    await cb.message.edit_text(
        f"<b>💬 SUPPORT</b>\n{DIVIDER}\n\n👤 @{SUPPORT_USERNAME}\n\n"
        f"⏱ Avg. response: 5–30 min\n\n{DIVIDER}",
        reply_markup=kb.back_menu())
    await cb.answer()


@router.callback_query(F.data == "about")
async def about(cb: CallbackQuery):
    await cb.message.edit_text(
        f"<b>ℹ️ ABOUT STORE</b>\n{DIVIDER}\n\n"
        f"🛍 Digital Services Store\n\n⚡ Fast Support\n🔒 Trusted Service\n💎 Premium Quality\n\n{DIVIDER}",
        reply_markup=kb.back_menu())
    await cb.answer()


@router.callback_query(F.data == "close")
async def close(cb: CallbackQuery):
    with suppress(TelegramBadRequest):
        await cb.message.delete()
    await cb.answer("Closed. Use /start to reopen.")
