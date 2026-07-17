from contextlib import suppress

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest

import database as db
import keyboards as kb
from config import (
    ADMIN_IDS, DIVIDER, BINANCE_PAY_ID, SUPPORT_USERNAME, 
    MIN_TOPUP, is_admin, REFERRAL_COMMISSION_PERCENT, DAILY_REWARD_AMOUNT
)
from states import TopUp, BuyProduct, SupportTicket, ProductReview, RedeemPromo
from subscription import is_subscribed, join_keyboard, join_text

router = Router()


async def home_text(user_id, name):
    user_info = await db.user_profile(user_id)
    ref_count, _ = await db.get_referral_stats(user_id)
    
    bal = user_info["balance"] if user_info else 0.0
    orders = user_info["orders"] if user_info else 0
    
    return (
        f"<b>⚡ Welcome to NOVA X Store</b>\n"
        f"<i>Premium Digital Licenses & Keys</i>\n"
        f"{DIVIDER}\n\n"
        f"👋 Welcome, <b>{name}</b>!\n\n"
        f"💳 <b>Wallet Balance :</b> <code>${bal:.2f}</code>\n"
        f"📦 <b>Total Orders    :</b> <code>{orders}</code>\n"
        f"👥 <b>Ref Invited    :</b> <code>{ref_count}</code>\n\n"
        f"✨ <i>Instant 24/7 delivery on all premium licenses, streaming accounts, and keys.</i>\n\n"
        f"{DIVIDER}\n"
        f"👇 Select an option from the menu below:"
    )


@router.message(CommandStart())
async def start(message: Message):
    await db.add_user(message.from_user.id, message.from_user.first_name)
    
    # Handle deep-linking
    args = message.text.split()
    prod_id = None
    if len(args) > 1:
        arg = args[1]
        if arg.startswith("ref_"):
            try:
                referrer_id = int(arg.split("_")[1])
                await db.set_referrer(message.from_user.id, referrer_id)
            except (ValueError, IndexError):
                pass
        elif arg.startswith("prod_"):
            try:
                prod_id = int(arg.split("_")[1])
            except (ValueError, IndexError):
                pass

    if not await is_subscribed(message.bot, message.from_user.id):
        return await message.answer(join_text(), reply_markup=join_keyboard())

    if prod_id:
        p = await db.get_product(prod_id)
        if p:
            cnt = await db.stock_count(prod_id)
            stock_line = f"📦 <b>Stock Status:</b> <code>In Stock ({cnt})</code>" if cnt > 0 else "❌ <b>Stock Status:</b> <code>Out of stock</code>"
            rating, count = await db.get_product_rating(prod_id)
            rating_line = f"⭐ <b>Rating:</b> <code>{rating:.1f}/5.0 ({count} reviews)</code>" if count > 0 else "⭐ <b>Rating:</b> <code>No reviews yet</code>"
            text = (
                f"<b>{p[1]} {p[2].upper()}</b>\n"
                f"<i>Premium License Key</i>\n"
                f"{DIVIDER}\n\n"
                f"{p[4]}\n\n"
                f"💰 <b>Price:</b> <code>${p[3]:.2f}</code>\n"
                f"{rating_line}\n"
                f"{stock_line}\n\n"
                f"{DIVIDER}"
            )
            return await message.answer(text, reply_markup=kb.product_detail_menu(prod_id, cnt > 0, category_id=p[5], is_free=(p[3] == 0)))

    await message.answer(
        await home_text(message.from_user.id, message.from_user.first_name),
        reply_markup=kb.main_menu(is_admin(message.from_user.id)),
    )


@router.callback_query(F.data == "check_join")
async def check_join(cb: CallbackQuery):
    if await is_subscribed(cb.bot, cb.from_user.id):
        await cb.message.edit_text(
            await home_text(cb.from_user.id, cb.from_user.first_name),
            reply_markup=kb.main_menu(is_admin(cb.from_user.id)),
        )
        await cb.answer("✅ Welcome!")
    else:
        await cb.answer("❌ You haven't joined yet. Please join first.", show_alert=True)


@router.callback_query(F.data == "home")
async def home(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.message.edit_text(
        await home_text(cb.from_user.id, cb.from_user.first_name),
        reply_markup=kb.main_menu(is_admin(cb.from_user.id)),
    )
    await cb.answer()


@router.callback_query(F.data == "products")
async def products(cb: CallbackQuery):
    categories = await db.get_categories()
    if not categories:
        return await show_all_products(cb)
    
    await cb.message.edit_text(
        f"<b>📂 PRODUCT CATEGORIES</b>\n"
        f"{DIVIDER}\n\n"
        f"Select a category to browse 👇",
        reply_markup=kb.categories_menu(categories)
    )
    await cb.answer()


@router.callback_query(F.data == "cat_all")
async def show_all_products(cb: CallbackQuery):
    items = await db.get_products()
    if not items:
        await cb.message.edit_text(
            f"<b>🛒 PRODUCT CATALOG</b>\n"
            f"{DIVIDER}\n\n"
            f"🚫 No products available yet.",
            reply_markup=kb.back_menu())
        return await cb.answer()
    stocks = {p[0]: await db.stock_count(p[0]) for p in items}
    await cb.message.edit_text(
        f"<b>🛒 ALL PRODUCTS</b>\n"
        f"{DIVIDER}\n\n"
        f"Choose a product to view details 👇",
        reply_markup=kb.products_menu(items, stocks, category_id="all"))
    await cb.answer()


@router.callback_query(F.data.startswith("cat:"))
async def view_category_products(cb: CallbackQuery):
    cid = int(cb.data.split(":")[1])
    cat = await db.get_category(cid)
    if not cat:
        return await cb.answer("Category not found!", show_alert=True)
    items = await db.get_products(category_id=cid)
    if not items:
        await cb.message.edit_text(
            f"<b>📁 {cat[2]}</b>\n"
            f"{DIVIDER}\n\n"
            f"🚫 No products available in this category yet.",
            reply_markup=kb.products_menu([], {}, category_id=cid))
        return await cb.answer()
    stocks = {p[0]: await db.stock_count(p[0]) for p in items}
    await cb.message.edit_text(
        f"<b>📁 {cat[2]}</b>\n"
        f"{DIVIDER}\n\n"
        f"Choose a product to view details 👇",
        reply_markup=kb.products_menu(items, stocks, category_id=cid))
    await cb.answer()


@router.callback_query(F.data.startswith("view:"))
async def view_product(cb: CallbackQuery):
    pid = int(cb.data.split(":")[1])
    p = await db.get_product(pid)
    if not p:
        return await cb.answer("Product not found!", show_alert=True)
    cnt = await db.stock_count(pid)
    stock_line = f"📦 <b>Stock Status:</b> <code>In Stock ({cnt})</code>" if cnt > 0 else "❌ <b>Stock Status:</b> <code>Out of stock</code>"
    
    rating, count = await db.get_product_rating(pid)
    rating_line = f"⭐ <b>Rating:</b> <code>{rating:.1f}/5.0 ({count} reviews)</code>" if count > 0 else "⭐ <b>Rating:</b> <code>No reviews yet</code>"

    text = (
        f"<b>{p[1]} {p[2].upper()}</b>\n"
        f"<i>Premium License Key</i>\n"
        f"{DIVIDER}\n\n"
        f"{p[4]}\n\n"
        f"💰 <b>Price:</b> <code>${p[3]:.2f}</code>\n"
        f"{rating_line}\n"
        f"{stock_line}\n\n"
        f"{DIVIDER}"
    )
    await cb.message.edit_text(text, reply_markup=kb.product_detail_menu(pid, cnt > 0, category_id=p[5], is_free=(p[3] == 0)))
    await cb.answer()


@router.callback_query(F.data.startswith("claim_free:"))
async def claim_free_product(cb: CallbackQuery):
    pid = int(cb.data.split(":")[1])
    p = await db.get_product(pid)
    if not p:
        return await cb.answer("Product not found!", show_alert=True)
        
    if p[3] != 0:
        return await cb.answer("❌ This is not a free product!", show_alert=True)
        
    cnt = await db.stock_count(pid)
    if cnt <= 0:
        return await cb.answer("❌ Out of stock!", show_alert=True)
        
    cooldown = await db.get_claim_cooldown(cb.from_user.id, pid)
    if cooldown > 0:
        hours = int(cooldown // 3600)
        minutes = int((cooldown % 3600) // 60)
        seconds = int(cooldown % 60)
        
        time_str = ""
        if hours > 0:
            time_str += f"{hours}h "
        if minutes > 0 or hours > 0:
            time_str += f"{minutes}m "
        time_str += f"{seconds}s"
        
        return await cb.answer(
            f"⚠️ You can only claim this once every 12 hours!\nTry again in {time_str}.",
            show_alert=True
        )
        
    items = await db.take_stock_items(pid, 1)
    if not items:
        return await cb.answer("❌ Out of stock!", show_alert=True)
        
    await db.add_free_claim(cb.from_user.id, pid)
    await db.add_order(cb.from_user.id, p[2], items[0], 0.0)
    
    delivered = (
        f"<b>🎁 CLAIM SUCCESSFUL</b>\n"
        f"<i>Free Reward Delivered!</i>\n"
        f"{DIVIDER}\n\n"
        f"📦 <b>Product:</b> {p[1]} <b>{p[2]}</b>\n\n"
        f"🔐 <b>Your Claimed Account / Key:</b>\n"
        f"<code>{items[0]}</code>\n\n"
        f"{DIVIDER}\n"
        f"<i>Please rate your claim below! ⭐</i>"
    )
    
    await cb.message.edit_text(delivered, reply_markup=kb.review_stars_menu(pid))
    await cb.answer("🎁 Claim successful!", show_alert=True)
    await check_and_alert_low_stock(cb.bot, pid)


@router.callback_query(F.data.startswith("buy_qty:"))
async def buy_quantity_select(cb: CallbackQuery):
    pid = int(cb.data.split(":")[1])
    p = await db.get_product(pid)
    if not p:
        return await cb.answer("Product not found!", show_alert=True)
    
    cnt = await db.stock_count(pid)
    if cnt <= 0:
        return await cb.answer("❌ Out of stock!", show_alert=True)
    
    await cb.message.edit_text(
        f"<b>🛒 BUY PRODUCT</b>\n"
        f"{DIVIDER}\n\n"
        f"📦 <b>Product:</b> {p[1]} {p[2]}\n"
        f"🔢 <b>Available:</b> <code>{cnt} items</code>\n\n"
        f"Select how many items you want to buy 👇",
        reply_markup=kb.quantity_menu(pid, cnt)
    )
    await cb.answer()


@router.callback_query(F.data.startswith("qsel:"))
async def quantity_selected(cb: CallbackQuery, state: FSMContext):
    parts = cb.data.split(":")
    pid = int(parts[1])
    qty_str = parts[2]
    
    p = await db.get_product(pid)
    if not p:
        return await cb.answer("Product not found!", show_alert=True)
    
    cnt = await db.stock_count(pid)
    if cnt <= 0:
        return await cb.answer("❌ Out of stock!", show_alert=True)
    
    if qty_str == "custom":
        await state.update_data(buy_pid=pid)
        await state.set_state(BuyProduct.quantity)
        await cb.message.edit_text(
            f"<b>✏️ CUSTOM QUANTITY</b>\n"
            f"{DIVIDER}\n\n"
            f"📦 <b>Product:</b> {p[1]} {p[2]}\n"
            f"🔢 <b>Available Stock:</b> <code>{cnt}</code>\n"
            f"💰 <b>Price per Unit:</b> <code>${p[3]:.2f}</code>\n\n"
            f"Please enter the exact quantity you wish to purchase:",
            reply_markup=kb.back_menu()
        )
        return await cb.answer()
    
    qty = int(qty_str)
    if qty > cnt:
        return await cb.answer(f"❌ Only {cnt} items left in stock!", show_alert=True)
    
    await show_checkout_confirmation(cb.message, state, p, qty)
    await cb.answer()


@router.message(BuyProduct.quantity)
async def custom_qty_input(message: Message, state: FSMContext):
    data = await state.get_data()
    pid = data.get("buy_pid")
    p = await db.get_product(pid)
    if not p:
        await state.clear()
        return await message.answer("Product not found.")
    
    try:
        qty = int(message.text)
        if qty <= 0:
            raise ValueError
    except ValueError:
        return await message.answer("❌ Please enter a valid positive integer.")
    
    cnt = await db.stock_count(pid)
    if qty > cnt:
        return await message.answer(f"❌ Only {cnt} items left in stock! Enter a smaller quantity:")
    
    await show_checkout_confirmation(message, state, p, qty)


async def show_checkout_confirmation(message_obj, state: FSMContext, product, quantity, promo_discount=0.0, promo_code=None):
    await state.update_data(buy_pid=product[0], buy_qty=quantity, promo_discount=promo_discount, promo_code=promo_code)
    
    total_price = (product[3] * quantity) - promo_discount
    if total_price < 0:
        total_price = 0.0
    
    discount_txt = f"\n🎟️ Promo discount: <b>-${promo_discount:.2f}</b>" if promo_discount > 0 else ""
    promo_code_txt = f"\n🔑 Code applied: <code>{promo_code}</code>" if promo_code else ""
    
    text = (
        f"<b>🛒 CHECKOUT CONFIRMATION</b>\n"
        f"{DIVIDER}\n\n"
        f"📦 <b>Product:</b> {product[1]} <b>{product[2]}</b>\n"
        f"🔢 <b>Quantity:</b> <code>{quantity}</code>\n"
        f"💵 <b>Price per Unit:</b> <code>${product[3]:.2f}</code>"
        f"{discount_txt}{promo_code_txt}\n\n"
        f"💰 <b>Total Cost:</b> <code>${total_price:.2f}</code>\n"
        f"{DIVIDER}\n"
        f"Please confirm your purchase below 👇"
    )
    
    reply_markup = kb.checkout_menu(product[0], quantity, has_promo=(promo_code is not None))
    
    if isinstance(message_obj, Message):
        await message_obj.answer(text, reply_markup=reply_markup)
    else:
        await message_obj.message.edit_text(text, reply_markup=reply_markup)


@router.callback_query(F.data.startswith("chk_promo:"))
async def checkout_apply_promo_start(cb: CallbackQuery, state: FSMContext):
    parts = cb.data.split(":")
    pid = int(parts[1])
    qty = int(parts[2])
    
    await state.update_data(buy_pid=pid, buy_qty=qty)
    await state.set_state(BuyProduct.promo_code)
    await cb.message.edit_text(
        "🎟️ <b>Enter your Promo Code:</b>",
        reply_markup=kb.back_menu()
    )
    await cb.answer()


@router.message(BuyProduct.promo_code)
async def checkout_apply_promo_save(message: Message, state: FSMContext):
    code = message.text.strip().upper()
    data = await state.get_data()
    pid = data.get("buy_pid")
    qty = data.get("buy_qty")
    
    p = await db.get_product(pid)
    if not p:
        await state.clear()
        return await message.answer("Product not found.")
    
    promo = await db.get_promo_code(code)
    if not promo:
        return await message.answer("❌ Invalid promo code! Try again or type /cancel to go back:")
    
    if promo[3] is not None and promo[4] >= promo[3]:
        return await message.answer("❌ This promo code has reached its maximum usage limit!")
    
    if await db.is_promo_used(code, message.from_user.id):
        return await message.answer("❌ You have already used this promo code!")
    
    promo_type = promo[1]
    val = promo[2]
    
    if promo_type == 'balance':
        return await message.answer("❌ This promo code is a Gift Card. Redeem it under 💰 Balance → Redeem Promo Code.")
    
    discount_amount = 0.0
    subtotal = p[3] * qty
    if promo_type == 'percentage':
        discount_amount = subtotal * (val / 100.0)
    elif promo_type == 'discount':
        discount_amount = val
    
    if discount_amount > subtotal:
        discount_amount = subtotal
        
    await show_checkout_confirmation(message, state, p, qty, promo_discount=discount_amount, promo_code=code)


@router.callback_query(F.data.startswith("chk_pay:"))
async def checkout_payment(cb: CallbackQuery, state: FSMContext):
    parts = cb.data.split(":")
    pid = int(parts[1])
    qty = int(parts[2])
    
    p = await db.get_product(pid)
    if not p:
        return await cb.answer("Product not found!", show_alert=True)
    
    data = await state.get_data()
    promo_discount = data.get("promo_discount", 0.0)
    promo_code = data.get("promo_code")
    
    cnt = await db.stock_count(pid)
    if cnt < qty:
        return await cb.answer("❌ Stock running low! Insufficient items left.", show_alert=True)
    
    price = (p[3] * qty) - promo_discount
    if price < 0:
        price = 0.0
        
    bal = await db.get_balance(cb.from_user.id)
    if bal < price:
        return await cb.answer(
            f"❌ Insufficient balance!\nNeed ${price:.2f}, you have ${bal:.2f}.",
            show_alert=True)
    
    items = await db.take_stock_items(pid, qty)
    if not items or len(items) < qty:
        return await cb.answer("❌ Purchase failed. Out of stock!", show_alert=True)
    
    if promo_code:
        await db.use_promo_code(promo_code, cb.from_user.id)
        
    await db.update_balance(cb.from_user.id, -price)
    
    content_delivered = "\n".join(items)
    for item in items:
        await db.add_order(cb.from_user.id, p[2], item, p[3])
        
    await state.clear()
    
    delivered = (
        f"<b>✅ PURCHASE SUCCESSFUL</b>\n"
        f"<i>Thank you for your order!</i>\n"
        f"{DIVIDER}\n\n"
        f"📦 <b>Product:</b> {p[1]} <b>{p[2]}</b> (x{qty})\n\n"
        f"🔐 <b>Your Account / ID List:</b>\n"
        f"<code>{content_delivered}</code>\n\n"
        f"💰 <b>Total Paid:</b> <code>${price:.2f}</code>\n"
        f"💵 <b>New Balance:</b> <code>${(bal - price):.2f}</code>\n\n"
        f"{DIVIDER}\n"
        f"<i>Please rate your purchase below! ⭐</i>"
    )
    
    await cb.message.edit_text(delivered, reply_markup=kb.review_stars_menu(pid))
    await cb.answer("✅ Purchase successful!", show_alert=True)
    await check_and_alert_low_stock(cb.bot, pid)


@router.callback_query(F.data.startswith("rate:"))
async def product_rating_receive(cb: CallbackQuery):
    parts = cb.data.split(":")
    pid = int(parts[1])
    rating = int(parts[2])
    
    await db.add_review(cb.from_user.id, pid, rating)
    await cb.message.edit_text(
        f"<b>Thank you for your rating! ⭐ {rating}/5</b>\n\n"
        f"Your feedback helps us maintain premium quality services.",
        reply_markup=kb.back_menu()
    )
    await cb.answer("Rating submitted!")


@router.callback_query(F.data == "skip_review")
async def product_rating_skip(cb: CallbackQuery):
    await cb.message.edit_text(
        await home_text(cb.from_user.id, cb.from_user.first_name),
        reply_markup=kb.main_menu(is_admin(cb.from_user.id))
    )
    await cb.answer()


@router.callback_query(F.data == "balance")
async def balance(cb: CallbackQuery):
    bal = await db.get_balance(cb.from_user.id)
    await cb.message.edit_text(
        f"<b>💰 WALLET BALANCE</b>\n"
        f"{DIVIDER}\n\n"
        f"💵 <b>Current Balance:</b> <code>${bal:.2f}</code>\n\n"
        f"You can top up your wallet via Binance Pay or redeem a promo gift card code below.\n\n"
        f"{DIVIDER}",
        reply_markup=kb.balance_menu())
    await cb.answer()


@router.callback_query(F.data == "topup")
async def topup(cb: CallbackQuery, state: FSMContext):
    await cb.message.edit_text(
        f"<b>💎 TOP UP — BINANCE PAY</b>\n"
        f"{DIVIDER}\n\n"
        f"Please send your payment to:\n"
        f"🆔 <b>Binance Pay ID:</b> <code>{BINANCE_PAY_ID}</code>\n\n"
        f"⚠️ <i>Minimum top-up is <b>${MIN_TOPUP:.0f} USD</b>. Any amount less than this will not be processed.</i>\n\n"
        f"After paying, enter the exact amount you sent (USD):",
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


@router.callback_query(F.data == "redeem_promo")
async def redeem_promo_start(cb: CallbackQuery, state: FSMContext):
    await state.set_state(RedeemPromo.code)
    await cb.message.edit_text(
        "🎟️ <b>REDEEM PROMO CODE</b>\n\n"
        "Please enter your promo code/gift card code to credit your balance:",
        reply_markup=kb.back_menu()
    )
    await cb.answer()


@router.message(RedeemPromo.code)
async def redeem_promo_save(message: Message, state: FSMContext):
    code = message.text.strip().upper()
    await state.clear()
    
    promo = await db.get_promo_code(code)
    if not promo:
        return await message.answer("❌ Invalid promo code!", reply_markup=kb.back_menu())
        
    if promo[3] is not None and promo[4] >= promo[3]:
        return await message.answer("❌ This promo code has reached its maximum usage limit!", reply_markup=kb.back_menu())
        
    if await db.is_promo_used(code, message.from_user.id):
        return await message.answer("❌ You have already redeemed this promo code!", reply_markup=kb.back_menu())
        
    if promo[1] != 'balance':
        return await message.answer("❌ This promo code is a discount coupon. Use it at checkout when purchasing a product.", reply_markup=kb.back_menu())
        
    success = await db.use_promo_code(code, message.from_user.id)
    if not success:
        return await message.answer("❌ Error redeeming code.", reply_markup=kb.back_menu())
        
    await db.update_balance(message.from_user.id, promo[2])
    
    await message.answer(
        f"<b>✅ PROMO CODE REDEEMED</b>\n"
        f"{DIVIDER}\n\n"
        f"🔑 <b>Promo Code:</b> <code>{code}</code>\n"
        f"💳 <b>Credited to Wallet:</b> <code>+${promo[2]:.2f}</code>\n\n"
        f"Enjoy shopping at NOVA X! 🛍️\n"
        f"{DIVIDER}",
        reply_markup=kb.back_menu()
    )


@router.callback_query(F.data == "referrals")
async def referrals_home(cb: CallbackQuery):
    count, earnings = await db.get_referral_stats(cb.from_user.id)
    from config import BOT_USERNAME
    ref_link = f"https://t.me/{BOT_USERNAME}?start=ref_{cb.from_user.id}"
    
    text = (
        f"<b>👥 REFERRAL PROGRAM</b>\n"
        f"{DIVIDER}\n\n"
        f"Invite your friends to NOVA X and earn <b>{REFERRAL_COMMISSION_PERCENT:.0f}% commission</b> on all their wallet top-ups!\n\n"
        f"🔗 <b>Your Referral Link:</b>\n<code>{ref_link}</code>\n\n"
        f"📊 <b>Your Statistics:</b>\n"
        f"• Total Invited: <code>{count} users</code>\n"
        f"• Commissions: <code>${earnings:.2f}</code>\n\n"
        f"<i>Commissions are credited instantly to your wallet balance.</i>\n"
        f"{DIVIDER}"
    )
    await cb.message.edit_text(text, reply_markup=kb.back_menu())
    await cb.answer()


@router.callback_query(F.data == "daily_claim")
async def daily_claim_handler(cb: CallbackQuery):
    can_claim = await db.can_claim_daily(cb.from_user.id)
    if not can_claim:
        return await cb.answer("❌ You have already claimed your daily reward today. Come back tomorrow!", show_alert=True)
    
    await db.claim_daily_reward(cb.from_user.id, DAILY_REWARD_AMOUNT)
    await cb.message.edit_text(
        f"<b>🎁 DAILY REWARD CLAIMED</b>\n"
        f"{DIVIDER}\n\n"
        f"Congratulations! You have received a free credit of <b>${DAILY_REWARD_AMOUNT:.2f}</b> to your balance.\n\n"
        f"Come back in 24 hours to claim another reward!\n"
        f"{DIVIDER}",
        reply_markup=kb.back_menu()
    )
    await cb.answer("Reward claimed!", show_alert=True)


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
        f"<b>📦 MY PURCHASES</b>\n"
        f"{DIVIDER}\n\n"
        f"{body}\n\n"
        f"{DIVIDER}",
        reply_markup=kb.back_menu())
    await cb.answer()


@router.callback_query(F.data == "support")
async def support_menu_handler(cb: CallbackQuery):
    await cb.message.edit_text(
        f"<b>💬 STORE SUPPORT</b>\n"
        f"{DIVIDER}\n\n"
        f"Need assistance? Open a support ticket directly inside the bot, or chat with us on Telegram.\n\n"
        f"🕒 <b>Avg. response time:</b> <code>5–30 min</code>\n\n"
        f"{DIVIDER}",
        reply_markup=kb.support_menu()
    )
    await cb.answer()


@router.callback_query(F.data == "open_ticket")
async def open_ticket_handler(cb: CallbackQuery, state: FSMContext):
    await state.set_state(SupportTicket.message)
    await cb.message.edit_text(
        "🎫 <b>OPEN SUPPORT TICKET</b>\n\n"
        "Please describe your issue in detail. You can send text or screenshot. "
        "Our support agents will respond shortly.",
        reply_markup=kb.back_menu()
    )
    await cb.answer()


@router.message(SupportTicket.message)
async def support_ticket_message(message: Message, state: FSMContext):
    await state.clear()
    
    admins = ADMIN_IDS
    sent_count = 0
    for admin in admins:
        try:
            admin_text = (
                f"🎫 <b>NEW SUPPORT TICKET</b>\n"
                f"From User: <code>{message.from_user.id}</code> ({message.from_user.first_name})\n\n"
                f"Message:"
            )
            if message.text:
                await message.bot.send_message(
                    admin,
                    f"{admin_text}\n{message.text}",
                    reply_markup=kb.admin_ticket_reply_menu(message.from_user.id)
                )
            elif message.photo:
                await message.bot.send_photo(
                    admin,
                    photo=message.photo[-1].file_id,
                    caption=f"{admin_text}\n[Photo Attachment] {message.caption or ''}",
                    reply_markup=kb.admin_ticket_reply_menu(message.from_user.id)
                )
            sent_count += 1
        except Exception:
            pass
            
    if sent_count > 0:
        await message.answer(
            "✅ <b>Ticket Submitted.</b>\n"
            "Your message has been forwarded to our support team. We will reply to you here shortly.",
            reply_markup=kb.back_menu()
        )
    else:
        await message.answer("❌ Error opening ticket. Please try again later or contact direct support.")


@router.callback_query(F.data == "about")
async def about(cb: CallbackQuery):
    await cb.message.edit_text(
        f"<b>ℹ️ ABOUT STORE</b>\n"
        f"{DIVIDER}\n\n"
        f"🛍️ <b>Digital Services Store</b>\n"
        f"⚡ <i>Fast Support</i>\n"
        f"🔒 <i>Secure & Trusted</i>\n"
        f"💎 <i>Premium Quality Licenses</i>\n\n"
        f"{DIVIDER}",
        reply_markup=kb.back_menu())
    await cb.answer()


@router.callback_query(F.data == "close")
async def close(cb: CallbackQuery):
    with suppress(TelegramBadRequest):
        await cb.message.delete()
    await cb.answer("Closed. Use /start to reopen.")


async def check_and_alert_low_stock(bot, pid):
    from config import CHANNEL_ID
    cnt = await db.stock_count(pid)
    if cnt <= 3:
        p = await db.get_product(pid)
        if not p:
            return
            
        emoji = p[1]
        name = p[2]
        price = p[3]
        
        if cnt == 0:
            msg = (
                f"❌ <b>OUT OF STOCK!</b>\n{DIVIDER}\n\n"
                f"{emoji} <b>{name}</b> is now out of stock!\n\n"
                f"Admins have been notified to restock. 📦"
            )
        else:
            price_str = "Free 🎁" if price == 0 else f"${price:.2f}"
            msg = (
                f"⚠️ <b>LOW STOCK ALERT!</b>\n{DIVIDER}\n\n"
                f"{emoji} <b>{name}</b> is running low on stock!\n\n"
                f"🔢 Remaining: <b>{cnt} item(s)</b>\n"
                f"💰 Price: {price_str}\n\n"
                f"🛒 Buy now before it sells out! 👇"
            )
            
        if CHANNEL_ID:
            with suppress(Exception):
                reply_markup = kb.buy_now_kb() if cnt > 0 else None
                await bot.send_message(CHANNEL_ID, msg, reply_markup=reply_markup)
                
        admin_msg = (
            f"🚨 <b>ADMIN ALERT: STOCK LOW</b>\n{DIVIDER}\n\n"
            f"Product: {emoji} <b>{name}</b> (ID: {pid})\n"
            f"Current Stock: <b>{cnt}</b>\n\n"
            f"Please restock soon!"
        )
        for admin_id in ADMIN_IDS:
            with suppress(Exception):
                await bot.send_message(admin_id, admin_msg)
