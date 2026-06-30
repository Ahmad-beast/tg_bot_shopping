from contextlib import suppress
import csv
import io

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from config import CHANNEL_ID, ADMIN_IDS, DIVIDER, is_admin
from states import (
    AddProduct, EditProduct, AddStock, Broadcast, AddBalance, BanUser, 
    BulkUpload, UserLookup, CustomBalance, ChannelPost, AddCategory, AddPromo, AdminReplySupport
)
import database as db
import keyboards as kb

router = Router()


@router.callback_query(F.data == "admin")
async def admin_home(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id):
        return await cb.answer("⛔ Access Denied!", show_alert=True)
    await state.clear()
    await cb.message.edit_text(
        f"<b>👑 ADMIN PANEL</b>\n{DIVIDER}\n\nManage your store below👇",
        reply_markup=kb.admin_menu())
    await cb.answer()


@router.callback_query(F.data == "a_stats")
async def stats(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        return await cb.answer("⛔", show_alert=True)

    users = await db.user_count()
    banned = await db.banned_count()
    prods = len(await db.get_products())
    stock = await db.total_stock_available()
    order_count, revenue = await db.order_stats()
    held = await db.total_balance_held()
    pending = await db.pending_topups_count()

    c24, r24 = await db.revenue_since(24)
    c7, r7 = await db.revenue_since(24 * 7)

    best = await db.best_selling(5)
    buyers = await db.top_buyers(5)

    aov = (revenue / order_count) if order_count else 0

    best_txt = "\n".join(
        f"   {i}. <b>{b[0]}</b> — {b[1]} sold (${b[2]:.2f})"
        for i, b in enumerate(best, 1)) or "   <i>No sales yet</i>"

    buyers_txt = "\n".join(
        f"   {i}. <b>{u[1]}</b> (<code>{u[0]}</code>) — ${u[3]:.2f} • {u[2]} orders"
        for i, u in enumerate(buyers, 1)) or "   <i>No buyers yet</i>"

    text = (
        f"<b>📊 STORE STATISTICS</b>\n{DIVIDER}\n\n"
        f"👥 <b>Users:</b> {users}  (🚫 {banned} banned)\n"
        f"📦 <b>Products:</b> {prods}  •  🔢 Stock: {stock}\n"
        f"💼 <b>Balance held:</b> ${held:.2f}\n"
        f"⏳ <b>Pending top-ups:</b> {pending}\n\n"

        f"💰 <b>REVENUE</b>\n"
        f"   • Total: <b>${revenue:.2f}</b> ({order_count} orders)\n"
        f"   • Last 24h: ${r24:.2f} ({c24})\n"
        f"   • Last 7d: ${r7:.2f} ({c7})\n"
        f"   • Avg order: ${aov:.2f}\n\n"

        f"🏆 <b>BEST SELLERS</b>\n{best_txt}\n\n"
        f"👑 <b>TOP BUYERS</b>\n{buyers_txt}\n\n"
        f"{DIVIDER}"
    )
    await cb.message.edit_text(text, reply_markup=kb.stats_menu())
    await cb.answer()


@router.callback_query(F.data == "a_lowstock")
async def low_stock(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        return await cb.answer("⛔", show_alert=True)
    low = await db.low_stock_products(3)
    if not low:
        body = "✅ All products have healthy stock."
    else:
        body = "\n".join(
            f"{'🔴' if r[2] == 0 else '🟡'} {r[0]} <b>{r[1]}</b> — {r[2]} left"
            for r in low)
    await cb.message.edit_text(
        f"<b>⚠️ LOW STOCK ALERT</b>\n{DIVIDER}\n\n{body}\n\n{DIVIDER}",
        reply_markup=kb.stats_menu())
    await cb.answer()



# ---------- ADD PRODUCT (+ notify all users) ----------
@router.callback_query(F.data == "a_addprod")
async def ap_start(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id):
        return await cb.answer("⛔", show_alert=True)
    
    categories = await db.get_categories()
    if not categories:
        await state.update_data(category_id=None)
        await state.set_state(AddProduct.details)
        prompt = (
            "➕ <b>Add Product (Quick Format)</b>\n\n"
            "Please send the product details in a single message separated by <b>|</b>:\n\n"
            "<code>Emoji | Name | Price | Description | Stock1 | Stock2 | ...</code>\n\n"
            "<b>Example:</b>\n"
            "<code>🎬 | Netflix Premium | 5.00 | 1 Month UHD. | acc1:pass | acc2:pass</code>\n\n"
            "<i>Formatting (spoilers, bold, quotes) is supported in the description!</i>"
        )
        await cb.message.edit_text(prompt, reply_markup=kb.admin_back())
        return await cb.answer()
        
    rows = []
    for c in categories:
        rows.append([InlineKeyboardButton(text=f"📁 {c[2]}", callback_data=f"ap_cat:{c[0]}")])
    rows.append([InlineKeyboardButton(text="❌ No Category", callback_data="ap_cat:none")])
    rows.append([InlineKeyboardButton(text="⬅️ Back", callback_data="admin")])
    
    await cb.message.edit_text(
        "➕ <b>Add Product</b>\n\nSelect the product category:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
    )
    await cb.answer()


@router.callback_query(F.data.startswith("ap_cat:"))
async def ap_cat_selected(cb: CallbackQuery, state: FSMContext):
    val = cb.data.split(":")[1]
    cat_id = None if val == "none" else int(val)
    await state.update_data(category_id=cat_id)
    await state.set_state(AddProduct.details)
    prompt = (
        "➕ <b>Add Product (Quick Format)</b>\n\n"
        "Please send the product details in a single message separated by <b>|</b>:\n\n"
        "<code>Emoji | Name | Price | Description | Stock1 | Stock2 | ...</code>\n\n"
        "<b>Example:</b>\n"
        "<code>🎬 | Netflix Premium | 5.00 | 1 Month UHD. | acc1:pass | acc2:pass</code>\n\n"
        "<i>Formatting (spoilers, bold, quotes) is supported in the description!</i>"
    )
    await cb.message.edit_text(prompt, reply_markup=kb.admin_back())
    await cb.answer()



# ---------- BULK ADD VIA CSV ----------
@router.callback_query(F.data == "a_bulk")
async def bulk_start(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id):
        return await cb.answer("⛔", show_alert=True)
    await state.set_state(BulkUpload.file)
    await cb.message.edit_text(
        "📁 <b>Bulk Add via CSV</b>\n" + DIVIDER + "\n\n"
        "Upload a <b>.csv</b> file with columns:\n\n"
        "<code>emoji,name,price,desc,stock</code>\n\n"
        "• Separate multiple stock items with <b>|</b> (pipe)\n"
        "• First row can be a header (auto-detected)\n\n"
        "<b>Example row:</b>\n"
        "<code>🎬,Netflix,5,Premium access,acc1:pass | acc2:pass</code>\n\n"
        "Send the file now 👇",
        reply_markup=kb.admin_back(),
    )
    await cb.answer()


@router.message(BulkUpload.file, F.document)
async def bulk_process(m: Message, state: FSMContext):
    doc = m.document
    if not (doc.file_name or "").lower().endswith(".csv"):
        return await m.answer("❌ Please upload a .csv file.")

    # download the file into memory
    buf = io.BytesIO()
    await m.bot.download(doc, destination=buf)
    buf.seek(0)
    try:
        text = buf.read().decode("utf-8-sig")  # handles Excel BOM
    except UnicodeDecodeError:
        return await m.answer("❌ Could not read file. Save it as UTF-8 CSV.")

    await state.clear()

    reader = csv.reader(io.StringIO(text))
    rows = [r for r in reader if any(cell.strip() for cell in r)]
    if not rows:
        return await m.answer("❌ The CSV is empty.", reply_markup=kb.admin_back())

    # skip header if first row looks like one
    first = [c.strip().lower() for c in rows[0]]
    if "name" in first and "price" in first:
        rows = rows[1:]

    added, total_stock, errors = 0, 0, 0
    new_for_announce = []

    for r in rows:
        try:
            emoji = (r[0].strip() or "📦") if len(r) > 0 else "📦"
            name = r[1].strip() if len(r) > 1 else ""
            price = float(r[2]) if len(r) > 2 and r[2].strip() else 0.0
            desc = r[3].strip() if len(r) > 3 else ""
            stock_raw = r[4] if len(r) > 4 else ""

            if not name:
                errors += 1
                continue

            pid = await db.add_product(emoji, name, price, desc)
            items = [s.strip() for s in stock_raw.split("|") if s.strip()]
            if items:
                await db.add_stock_items(pid, items)
                total_stock += len(items)
            added += 1
            new_for_announce.append((emoji, name, price, desc))
        except Exception:
            errors += 1

    await m.answer(
        f"✅ <b>Bulk add complete!</b>\n{DIVIDER}\n\n"
        f"📦 Products added: <b>{added}</b>\n"
        f"🔢 Stock items: <b>{total_stock}</b>\n"
        f"⚠️ Skipped rows: <b>{errors}</b>",
        reply_markup=kb.admin_back(),
    )

    # notify users + channel about each new product
    user_ids = await db.all_user_ids()
    for emoji, name, price, desc in new_for_announce:
        announce = (
            f"🆕 <b>NEW PRODUCT AVAILABLE!</b>\n{DIVIDER}\n\n"
            f"{emoji} <b>{name}</b>\n\n{desc}\n\n"
            f"💰 <b>Price:</b> ${price:.2f}\n\n🛒 Open the store to grab it!\n\n{DIVIDER} Bot: @{m.bot.username}"
        )
        for uid in user_ids:
            with suppress(Exception):
                await m.bot.send_message(uid, announce)
        if CHANNEL_ID:
            with suppress(Exception):
                await m.bot.send_message(CHANNEL_ID, announce, reply_markup=kb.buy_now_kb())

@router.message(AddProduct.details)
async def ap_details(m: Message, state: FSMContext):
    text = m.text or ""
    html = m.html_text or ""
    
    parts = [p.strip() for p in text.split("|")]
    html_parts = [p.strip() for p in html.split("|")]
    
    if len(parts) < 4:
        return await m.answer(
            "❌ <b>Invalid format!</b>\n\n"
            "Please make sure you have at least 4 parts: Emoji, Name, Price, and Description separated by <b>|</b>.\n\n"
            "<b>Example:</b>\n"
            "<code>🎬 | Netflix Premium | 5.00 | 1 Month UHD. | acc1:pass | acc2:pass</code>"
        )
        
    emoji = parts[0]
    name = parts[1]
    price_str = parts[2]
    desc = html_parts[3]
    
    try:
        price = float(price_str)
        if price < 0:
            raise ValueError
    except ValueError:
        return await m.answer("❌ Please enter a valid positive number for the price.")
        
    stock_items = parts[4:]
    stock_items = [s for s in stock_items if s]
    
    data = await state.get_data()
    category_id = data.get("category_id")
    await state.clear()
    
    pid = await db.add_product(emoji, name, price, desc, category_id)
    if stock_items:
        await db.add_stock_items(pid, stock_items)
        
    await m.answer(
        f"✅ Product <b>{name}</b> added successfully with {len(stock_items)} stock item(s)!",
        reply_markup=kb.admin_back()
    )
    
    announce = (
        f"🆕 <b>NEW PRODUCT AVAILABLE!</b>\n{DIVIDER}\n\n"
        f"{emoji} <b>{name}</b>\n\n"
        f"{desc}\n\n💰 <b>Price:</b> ${price:.2f}\n\n"
        f"Open the store and grab it now! 🛒"
    )
    sent = 0
    for uid in await db.all_user_ids():
        with suppress(Exception):
            await m.bot.send_message(uid, announce)
            sent += 1
    await m.answer(f"📢 New product announced to {sent} user(s).")
    
    if CHANNEL_ID:
        with suppress(Exception):
            await m.bot.send_message(
                CHANNEL_ID,
                f"🆕 <b>NEW PRODUCT!</b>\n{DIVIDER}\n\n"
                f"{emoji} <b>{name}</b>\n\n"
                f"{desc}\n\n💰 <b>Price:</b> ${price:.2f}\n\n"
                f"🛒 Available now 👇",
                reply_markup=kb.buy_now_kb(),
            )


@router.message(BulkUpload.file)
async def bulk_no_file(m: Message):
    await m.answer("❌ Please upload a .csv <b>file</b> (not text).")


# ---------- LIST / MANAGE PRODUCTS ----------
@router.callback_query(F.data == "a_listprod")
async def list_prod(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        return await cb.answer("⛔", show_alert=True)
    items = await db.get_products()
    if not items:
        await cb.message.edit_text("🗂 No products yet.", reply_markup=kb.admin_back())
        return await cb.answer()
    rows = []
    for p in items:
        cnt = await db.stock_count(p[0])
        rows.append([InlineKeyboardButton(
            text=f"{p[1]} {p[2]} (${p[3]:.2f}) • stock:{cnt}",
            callback_data=f"mng:{p[0]}")])
    rows.append([InlineKeyboardButton(text="⬅️ Admin Panel", callback_data="admin")])
    await cb.message.edit_text(
        f"<b>🗂 MANAGE PRODUCTS</b>\n{DIVIDER}\n\nTap a product to edit/delete:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    await cb.answer()


@router.callback_query(F.data.startswith("mng:"))
async def manage_prod(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        return await cb.answer("⛔", show_alert=True)
    pid = int(cb.data.split(":")[1])
    p = await db.get_product(pid)
    if not p:
        return await cb.answer("Not found", show_alert=True)
    cnt = await db.stock_count(pid)
    await cb.message.edit_text(
        f"<b>{p[1]} {p[2]}</b>\n{DIVIDER}\n\n"
        f"💰 ${p[3]:.2f}\n📦 Stock: {cnt}\n📝 {p[4]}\n\nChoose an action:",
        reply_markup=kb.manage_product_menu(pid))
    await cb.answer()


@router.callback_query(F.data.startswith("del:"))
async def del_prod(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        return await cb.answer("⛔", show_alert=True)
    pid = int(cb.data.split(":")[1])
    await db.delete_product(pid)
    await cb.message.edit_text("🗑 Product deleted.", reply_markup=kb.admin_back())
    await cb.answer("Deleted")


@router.callback_query(F.data.startswith("edit:"))
async def edit_prod(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id):
        return await cb.answer("⛔", show_alert=True)
    _, pid, field = cb.data.split(":")
    await state.update_data(pid=int(pid), field=field)
    await state.set_state(EditProduct.value)
    await cb.message.edit_text(f"✏️ Send new <b>{field}</b>:")
    await cb.answer()


@router.message(EditProduct.value)
async def edit_value(m: Message, state: FSMContext):
    data = await state.get_data()
    field, value = data["field"], m.html_text if data["field"] == "desc" else m.text
    if field == "price":
        try:
            value = float(value)
        except ValueError:
            return await m.answer("❌ Enter a valid number.")
    await db.update_product_field(data["pid"], field, value)
    await state.clear()
    await m.answer(f"✅ Updated <b>{field}</b>.", reply_markup=kb.admin_back())


# ---------- ADD STOCK ----------
@router.callback_query(F.data.startswith("addstock:"))
async def addstock_start(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id):
        return await cb.answer("⛔", show_alert=True)
    pid = int(cb.data.split(":")[1])
    await state.update_data(pid=pid)
    await state.set_state(AddStock.items)
    await cb.message.edit_text(
        "➕ <b>Add Stock</b>\n\nSend stock items (one account/key/ID per line):")
    await cb.answer()


@router.message(AddStock.items)
async def addstock_save(m: Message, state: FSMContext):
    data = await state.get_data()
    items = [line.strip() for line in m.text.splitlines() if line.strip()]
    if items:
        await db.add_stock_items(data["pid"], items)
    await state.clear()
    await m.answer(f"✅ Added {len(items)} stock item(s).", reply_markup=kb.admin_back())

    # Announce restock to channel (with price + Buy Now button)
    if items and CHANNEL_ID:
        p = await db.get_product(data["pid"])
        if p:
            cnt = await db.stock_count(data["pid"])
            with suppress(Exception):
                await m.bot.send_message(
                    CHANNEL_ID,
                    f"📦 <b>RESTOCKED!</b>\n{DIVIDER}\n\n"
                    f"{p[1]} <b>{p[2]}</b> is back in stock!\n\n"
                    f"🔢 Available: <b>{cnt}</b>\n"
                    f"💰 <b>Price:</b> ${p[3]:.2f}\n\n"
                    f"🛒 Grab it now 👇",
                    reply_markup=kb.buy_now_kb(),
                )



# ---------- ADD BALANCE (enhanced) ----------
@router.callback_query(F.data == "a_addbal")
async def addbal_start(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id):
        return await cb.answer("⛔", show_alert=True)
    await state.set_state(AddBalance.user_id)
    await cb.message.edit_text(
        "💳 <b>Add Balance</b>\n" + DIVIDER + "\n\n"
        "Send the <b>user ID</b> to credit.\n"
        "<i>Tip: find IDs via 👤 User Lookup.</i>",
        reply_markup=kb.admin_back())
    await cb.answer()


@router.message(AddBalance.user_id)
async def addbal_uid(m: Message, state: FSMContext):
    try:
        uid = int(m.text)
    except ValueError:
        return await m.answer("❌ Invalid user ID. Send numbers only.")
    prof = await db.user_profile(uid)
    await state.clear()
    if not prof:
        return await m.answer(
            f"⚠️ User <code>{uid}</code> not found in DB.\n"
            f"They must /start the bot at least once.",
            reply_markup=kb.admin_back())
    await m.answer(
        f"👤 <b>{prof['name']}</b>\n{DIVIDER}\n\n"
        f"🆔 <code>{prof['id']}</code>\n"
        f"💵 Balance: <b>${prof['balance']:.2f}</b>\n"
        f"🛒 Orders: {prof['orders']}  •  Spent: ${prof['spent']:.2f}\n"
        f"{'🚫 BANNED' if prof['banned'] else '✅ Active'}\n\n"
        f"Choose an amount to add:",
        reply_markup=kb.addbal_user_menu(uid))


@router.callback_query(F.data.startswith("qbal:"))
async def quick_balance(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        return await cb.answer("⛔", show_alert=True)
    _, uid, amount = cb.data.split(":")
    uid, amount = int(uid), float(amount)
    await db.update_balance(uid, amount)
    prof = await db.user_profile(uid)
    await cb.message.edit_text(
        f"✅ Added <b>${amount:.2f}</b> to <b>{prof['name']}</b>.\n\n"
        f"💵 New balance: <b>${prof['balance']:.2f}</b>",
        reply_markup=kb.admin_back())
    with suppress(Exception):
        await cb.bot.send_message(uid, f"💰 Your balance was topped up by ${amount:.2f}!")
    await cb.answer("Done")


@router.callback_query(F.data.startswith("cbal:"))
async def custom_balance_start(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id):
        return await cb.answer("⛔", show_alert=True)
    uid = int(cb.data.split(":")[1])
    await state.update_data(uid=uid)
    await state.set_state(CustomBalance.amount)
    await cb.message.edit_text(f"✏️ Send custom amount (USD) for user <code>{uid}</code>:")
    await cb.answer()


@router.message(CustomBalance.amount)
async def custom_balance_save(m: Message, state: FSMContext):
    try:
        amount = float(m.text)
    except ValueError:
        return await m.answer("❌ Enter a valid number.")
    data = await state.get_data()
    uid = data["uid"]
    await db.update_balance(uid, amount)
    await state.clear()
    prof = await db.user_profile(uid)
    await m.answer(
        f"✅ Added <b>${amount:.2f}</b> to <b>{prof['name']}</b>.\n"
        f"💵 New balance: <b>${prof['balance']:.2f}</b>",
        reply_markup=kb.admin_back())
    with suppress(Exception):
        await m.bot.send_message(uid, f"💰 Your balance was topped up by ${amount:.2f}!")



# ---------- TOPUP APPROVE / REJECT ----------
@router.callback_query(F.data.startswith("tu_ok:"))
async def topup_approve(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        return await cb.answer("⛔", show_alert=True)
    tid = int(cb.data.split(":")[1])
    tu = await db.get_topup(tid)
    if not tu or tu[3] != "pending":
        return await cb.answer("Already handled.", show_alert=True)
        
    user_id = tu[1]
    amount = tu[2]
    
    await db.update_balance(user_id, amount)
    await db.set_topup_status(tid, "approved")
    await cb.message.edit_text(f"✅ Top-up #{tid} approved. ${amount:.2f} credited.")
    
    with suppress(Exception):
        await cb.bot.send_message(user_id, f"✅ Your top-up of ${amount:.2f} was approved!")
        
    # Check for referral commission
    from config import REFERRAL_COMMISSION_PERCENT
    import aiosqlite
    try:
        async with aiosqlite.connect(db.DB_PATH) as conn:
            async with conn.execute("SELECT referred_by FROM users WHERE user_id=?", (user_id,)) as cur:
                row = await cur.fetchone()
                referrer_id = row[0] if row else None
        
        if referrer_id:
            commission = amount * (REFERRAL_COMMISSION_PERCENT / 100.0)
            await db.add_referral_earnings(referrer_id, commission)
            with suppress(Exception):
                await cb.bot.send_message(
                    referrer_id,
                    f"💰 <b>Referral Commission Received!</b>\n\n"
                    f"Your invitee topped up ${amount:.2f}. You earned a <b>{REFERRAL_COMMISSION_PERCENT:.0f}% commission</b> of <b>+${commission:.2f}</b>!"
                )
    except Exception:
        pass
        
    await cb.answer("Approved")


@router.callback_query(F.data.startswith("tu_no:"))
async def topup_reject(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        return await cb.answer("⛔", show_alert=True)
    tid = int(cb.data.split(":")[1])
    tu = await db.get_topup(tid)
    if not tu or tu[3] != "pending":
        return await cb.answer("Already handled.", show_alert=True)
    await db.set_topup_status(tid, "rejected")
    await cb.message.edit_text(f"❌ Top-up #{tid} rejected.")
    with suppress(Exception):
        await cb.bot.send_message(tu[1], f"❌ Your top-up request of ${tu[2]:.2f} was rejected.")
    await cb.answer("Rejected")


# ---------- BAN / UNBAN ----------
@router.callback_query(F.data == "a_ban")
async def ban_start(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id):
        return await cb.answer("⛔", show_alert=True)
    await state.set_state(BanUser.user_id)
    await state.update_data(action="ban")
    await cb.message.edit_text("🚫 Send the <b>user ID</b> to ban:")
    await cb.answer()


@router.callback_query(F.data == "a_unban")
async def unban_start(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id):
        return await cb.answer("⛔", show_alert=True)
    await state.set_state(BanUser.user_id)
    await state.update_data(action="unban")
    await cb.message.edit_text("✅ Send the <b>user ID</b> to unban:")
    await cb.answer()


@router.message(BanUser.user_id)
async def ban_apply(m: Message, state: FSMContext):
    try:
        uid = int(m.text)
    except ValueError:
        return await m.answer("❌ Invalid user ID.")
    data = await state.get_data()
    ban = data["action"] == "ban"
    await db.set_banned(uid, ban)
    await state.clear()
    await m.answer(
        f"{'🚫 Banned' if ban else '✅ Unbanned'} user <code>{uid}</code>.",
        reply_markup=kb.admin_back())


# ---------- BROADCAST ----------
@router.callback_query(F.data == "a_broadcast")
async def bc_start(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id):
        return await cb.answer("⛔", show_alert=True)
    await state.set_state(Broadcast.message)
    await cb.message.edit_text(
        "📢 <b>Rich Broadcast Campaign</b>\n\n"
        "Send your broadcast content now. It can be:\n"
        "• A plain <b>text message</b> with HTML formatting.\n"
        "• A <b>photo banner</b> with a formatted caption.\n\n"
        "Formatting (bold, italic, links) is fully supported.",
        reply_markup=kb.admin_back()
    )
    await cb.answer()


@router.message(Broadcast.message)
async def bc_capture_message(m: Message, state: FSMContext):
    text_content = m.html_text if m.text else (m.caption or "")
    photo_file_id = m.photo[-1].file_id if m.photo else None
    
    await state.update_data(
        bc_text=text_content,
        bc_photo=photo_file_id
    )
    
    await state.set_state(Broadcast.button_choice)
    await m.answer(
        "⚡ <b>Content Captured!</b>\n\n"
        "Do you want to attach an interactive button to this broadcast?",
        reply_markup=kb.broadcast_button_choice_menu()
    )


@router.callback_query(F.data.startswith("bc_btn:"), Broadcast.button_choice)
async def bc_button_chosen(cb: CallbackQuery, state: FSMContext):
    choice = cb.data.split(":")[1]
    
    if choice == "none":
        await execute_broadcast(cb.message, state, button_text=None, button_url=None)
        await cb.answer()
    elif choice == "prod":
        products = await db.get_products()
        if not products:
            await cb.answer("❌ No products available to link! Please create one first.", show_alert=True)
            return
        await state.set_state(Broadcast.product_select)
        await cb.message.edit_text(
            "🛒 <b>Link a Product</b>\n\nSelect the product you want to attach as a 'Buy Now' button:",
            reply_markup=kb.broadcast_products_list(products)
        )
        await cb.answer()
    elif choice == "custom":
        await state.set_state(Broadcast.custom_button)
        await cb.message.edit_text(
            "🔗 <b>Custom URL Button</b>\n\n"
            "Please send the button label and URL in this format:\n\n"
            "<code>Button Label | https://yourlink.com</code>\n\n"
            "Example:\n"
            "<code>Join Channel | https://t.me/shoppingxchannel</code>",
            reply_markup=kb.admin_back()
        )
        await cb.answer()


@router.callback_query(F.data.startswith("bc_prod:"), Broadcast.product_select)
async def bc_product_selected(cb: CallbackQuery, state: FSMContext):
    pid = int(cb.data.split(":")[1])
    p = await db.get_product(pid)
    if not p:
        await cb.answer("Product not found!", show_alert=True)
        return
        
    from config import BOT_USERNAME
    if not BOT_USERNAME:
        await cb.answer("❌ BOT_USERNAME not set in .env! Cannot build product deep-links.", show_alert=True)
        return
        
    button_text = f"🛒 Buy {p[2]}"
    button_url = f"https://t.me/{BOT_USERNAME}?start=prod_{pid}"
    
    await execute_broadcast(cb.message, state, button_text, button_url)
    await cb.answer()


@router.message(Broadcast.custom_button)
async def bc_custom_button_save(m: Message, state: FSMContext):
    text = m.text.strip()
    if "|" not in text:
        return await m.answer("❌ Invalid format! Please enter as: <code>Button Label | URL</code>")
        
    parts = text.split("|")
    label = parts[0].strip()
    url = parts[1].strip()
    
    if not (url.startswith("http://") or url.startswith("https://") or url.startswith("tg://")):
        return await m.answer("❌ Invalid URL! Must start with http://, https://, or tg://")
        
    await execute_broadcast(m, state, label, url)


async def execute_broadcast(message_obj, state: FSMContext, button_text=None, button_url=None):
    data = await state.get_data()
    text = data.get("bc_text", "")
    photo = data.get("bc_photo")
    await state.clear()
    
    reply_markup = None
    if button_text and button_url:
        reply_markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=button_text, url=button_url)]
        ])
        
    progress_msg = None
    if isinstance(message_obj, Message):
        progress_msg = await message_obj.answer("⏳ Sending broadcast to all users...")
    else:
        progress_msg = await message_obj.answer("⏳ Sending broadcast to all users...")
        with suppress(Exception):
            await message_obj.delete()
            
    sent, failed = 0, 0
    uids = await db.all_user_ids()
    
    for uid in uids:
        try:
            if photo:
                await message_obj.bot.send_photo(
                    chat_id=uid,
                    photo=photo,
                    caption=text,
                    parse_mode="HTML",
                    reply_markup=reply_markup
                )
            else:
                await message_obj.bot.send_message(
                    chat_id=uid,
                    text=text,
                    parse_mode="HTML",
                    reply_markup=reply_markup
                )
            sent += 1
        except Exception:
            failed += 1
            
    with suppress(Exception):
        await progress_msg.delete()
        
    result_text = (
        f"✅ <b>Broadcast Campaign Complete!</b>\n{DIVIDER}\n\n"
        f"👤 Total Sent: <b>{sent}</b>\n"
        f"❌ Failed/Blocked: <b>{failed}</b>"
    )
    
    if isinstance(message_obj, Message):
        await message_obj.answer(result_text, reply_markup=kb.admin_back())
    else:
        await message_obj.bot.send_message(message_obj.chat.id, result_text, reply_markup=kb.admin_back())


# ---------- POST TO CHANNEL ----------
@router.callback_query(F.data == "a_channel")
async def channel_start(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id):
        return await cb.answer("⛔", show_alert=True)
    if not CHANNEL_ID:
        return await cb.answer("❌ CHANNEL_ID not set in .env", show_alert=True)
    await state.set_state(ChannelPost.message)
    await cb.message.edit_text("📣 Send the <b>message</b> to post to the channel:")
    await cb.answer()


@router.message(ChannelPost.message)
async def channel_post(m: Message, state: FSMContext):
    await state.clear()
    try:
        await m.bot.send_message(CHANNEL_ID, m.html_text)
        await m.answer("✅ Posted to channel.", reply_markup=kb.admin_back())
    except Exception as e:
        await m.answer(f"❌ Failed to post: {e}", reply_markup=kb.admin_back())

# ---------- USER LOOKUP ----------
@router.callback_query(F.data == "a_lookup")
async def lookup_start(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id):
        return await cb.answer("⛔", show_alert=True)
    await state.set_state(UserLookup.query)
    await cb.message.edit_text(
        "👤 <b>User Lookup</b>\n" + DIVIDER + "\n\n"
        "Send a <b>user ID</b> or part of a <b>name</b> to search.\n"
        "Send <code>recent</code> to see latest users.",
        reply_markup=kb.admin_back())
    await cb.answer()


@router.message(UserLookup.query)
async def lookup_run(m: Message, state: FSMContext):
    await state.clear()
    q = m.text.strip()

    # exact ID
    if q.isdigit():
        prof = await db.user_profile(int(q))
        if not prof:
            return await m.answer("⚠️ No user with that ID.", reply_markup=kb.admin_back())
        return await m.answer(
            f"👤 <b>{prof['name']}</b>\n{DIVIDER}\n\n"
            f"🆔 <code>{prof['id']}</code>\n"
            f"💵 Balance: <b>${prof['balance']:.2f}</b>\n"
            f"🛒 Orders: {prof['orders']}  •  Spent: ${prof['spent']:.2f}\n"
            f"{'🚫 BANNED' if prof['banned'] else '✅ Active'}",
            reply_markup=kb.addbal_user_menu(prof["id"]))

    rows = await db.recent_users(10) if q.lower() == "recent" else await db.find_users_by_name(q, 10)
    if not rows:
        return await m.answer("⚠️ No users found.", reply_markup=kb.admin_back())
    body = "\n".join(
        f"• <b>{r[1]}</b> — <code>{r[0]}</code> • ${r[2]:.2f}" for r in rows)
    await m.answer(
        f"👥 <b>RESULTS</b>\n{DIVIDER}\n\n{body}\n\n"
        f"<i>Send a user ID via 💳 Add Balance to credit.</i>",
        reply_markup=kb.admin_back())


# ---------- CATEGORIES MANAGEMENT ----------
@router.callback_query(F.data == "a_categories")
async def a_categories(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        return await cb.answer("⛔", show_alert=True)
    cats = await db.get_categories()
    rows = []
    for c in cats:
        rows.append([
            InlineKeyboardButton(text=f"{c[1]} {c[2]}", callback_data="noop"),
            InlineKeyboardButton(text="🗑️ Delete", callback_data=f"delcat:{c[0]}")
        ])
    rows.append([InlineKeyboardButton(text="➕ Add Category", callback_data="a_addcat")])
    rows.append([InlineKeyboardButton(text="⬅️ Admin Panel", callback_data="admin")])
    
    await cb.message.edit_text(
        f"<b>📂 MANAGE CATEGORIES</b>\n{DIVIDER}\n\nList of categories:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
    )
    await cb.answer()


@router.callback_query(F.data == "a_addcat")
async def a_addcat_start(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id):
        return await cb.answer("⛔", show_alert=True)
    await state.set_state(AddCategory.emoji)
    await cb.message.edit_text("➕ <b>Add Category</b>\n\nSend a category <b>emoji</b> (e.g. 🔑):")
    await cb.answer()


@router.message(AddCategory.emoji)
async def a_addcat_emoji(m: Message, state: FSMContext):
    await state.update_data(emoji=m.text.strip())
    await state.set_state(AddCategory.name)
    await m.answer("Send category <b>name</b>:")


@router.message(AddCategory.name)
async def a_addcat_name(m: Message, state: FSMContext):
    data = await state.get_data()
    name = m.text.strip()
    emoji = data.get("emoji", "📁")
    await db.add_category(emoji, name)
    await state.clear()
    await m.answer(f"✅ Category <b>{emoji} {name}</b> added successfully!", reply_markup=kb.admin_back())


@router.callback_query(F.data.startswith("delcat:"))
async def a_delcat(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        return await cb.answer("⛔", show_alert=True)
    cid = int(cb.data.split(":")[1])
    await db.delete_category(cid)
    await cb.message.edit_text("🗑️ Category deleted successfully.", reply_markup=kb.admin_back())
    await cb.answer()


# ---------- PROMO CODES MANAGEMENT ----------
@router.callback_query(F.data == "a_promos")
async def a_promos(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        return await cb.answer("⛔", show_alert=True)
    promos = await db.get_all_promos()
    rows = []
    for p in promos:
        type_lbl = "Gift Card" if p[1] == "balance" else ("%" if p[1] == "percentage" else "$")
        val_lbl = f"${p[2]:.2f}" if p[1] != "percentage" else f"{p[2]:.0f}%"
        rows.append([
            InlineKeyboardButton(text=f"🔑 {p[0]} ({type_lbl}: {val_lbl}) • {p[4]}/{p[3] or '∞'}", callback_data="noop"),
            InlineKeyboardButton(text="🗑️", callback_data=f"delpromo:{p[0]}")
        ])
    rows.append([InlineKeyboardButton(text="➕ Create Promo Code", callback_data="a_addpromo")])
    rows.append([InlineKeyboardButton(text="⬅️ Admin Panel", callback_data="admin")])
    
    await cb.message.edit_text(
        f"<b>🎟️ MANAGE PROMO CODES</b>\n{DIVIDER}\n\nList of active promo codes:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
    )
    await cb.answer()


@router.callback_query(F.data == "a_addpromo")
async def a_addpromo_start(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id):
        return await cb.answer("⛔", show_alert=True)
    await state.set_state(AddPromo.code)
    await cb.message.edit_text("🎟️ <b>Create Promo Code</b>\n\nEnter the promo <b>code</b> name (e.g. SAVE20):")
    await cb.answer()


@router.message(AddPromo.code)
async def a_addpromo_code(m: Message, state: FSMContext):
    code = m.text.strip().upper()
    await state.update_data(code=code)
    
    rows = [
        [InlineKeyboardButton(text="💰 Gift Card (Credits Balance)", callback_data="ap_prtype:balance")],
        [InlineKeyboardButton(text="📈 Percentage Discount (Checkout)", callback_data="ap_prtype:percentage")],
        [InlineKeyboardButton(text="💵 Flat Discount (Checkout)", callback_data="ap_prtype:discount")],
    ]
    await m.answer(
        f"Select promo code type for <code>{code}</code>:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
    )


@router.callback_query(F.data.startswith("ap_prtype:"))
async def a_addpromo_type(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id):
        return await cb.answer("⛔", show_alert=True)
    ptype = cb.data.split(":")[1]
    await state.update_data(type=ptype)
    await state.set_state(AddPromo.value)
    
    prompt = "Enter flat dollar value (e.g. 5.00 for $5):" if ptype != "percentage" else "Enter discount percentage (e.g. 20 for 20%):"
    await cb.message.edit_text(f"🎟️ <b>Create Promo Code</b>\n\n{prompt}")
    await cb.answer()


@router.message(AddPromo.value)
async def a_addpromo_value(m: Message, state: FSMContext):
    try:
        val = float(m.text)
        if val <= 0:
            raise ValueError
    except ValueError:
        return await m.answer("❌ Please enter a valid positive number.")
    
    await state.update_data(value=val)
    await state.set_state(AddPromo.max_uses)
    await m.answer("Enter maximum allowed uses (integer, or 0 for unlimited):")


@router.message(AddPromo.max_uses)
async def a_addpromo_uses(m: Message, state: FSMContext):
    try:
        uses = int(m.text)
        if uses < 0:
            raise ValueError
    except ValueError:
        return await m.answer("❌ Please enter a valid non-negative integer.")
        
    data = await state.get_data()
    code = data.get("code")
    ptype = data.get("type")
    val = data.get("value")
    max_uses = None if uses == 0 else uses
    
    await db.add_promo_code(code, ptype, val, max_uses)
    await state.clear()
    
    type_lbl = "Gift Card" if ptype == "balance" else ("Percentage" if ptype == "percentage" else "Flat Checkout")
    await m.answer(
        f"✅ <b>Promo Code Created!</b>\n{DIVIDER}\n\n"
        f"🔑 Code: <code>{code}</code>\n"
        f"🏷️ Type: <b>{type_lbl}</b>\n"
        f"💰 Value: <b>{val}</b>\n"
        f"🔢 Max Uses: <b>{uses if uses > 0 else 'Unlimited'}</b>",
        reply_markup=kb.admin_back()
    )


@router.callback_query(F.data.startswith("delpromo:"))
async def a_delpromo(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        return await cb.answer("⛔", show_alert=True)
    code = cb.data.split(":")[1]
    await db.delete_promo_code(code)
    await cb.message.edit_text("🗑️ Promo code deleted successfully.", reply_markup=kb.admin_back())
    await cb.answer()


# ---------- SUPPORT TICKET ROUTING ----------
@router.callback_query(F.data.startswith("t_reply:"))
async def a_ticket_reply_start(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id):
        return await cb.answer("⛔", show_alert=True)
    uid = int(cb.data.split(":")[1])
    await state.update_data(target_user_id=uid)
    await state.set_state(AdminReplySupport.message)
    
    await cb.message.answer(
        f"💬 <b>Reply to User</b> <code>{uid}</code>:\n"
        f"Type your message below. It will be sent privately to this customer.",
        reply_markup=kb.admin_back()
    )
    await cb.answer()


@router.message(AdminReplySupport.message)
async def a_ticket_reply_save(m: Message, state: FSMContext):
    data = await state.get_data()
    uid = data.get("target_user_id")
    await state.clear()
    
    if not uid:
        return await m.answer("❌ Target user ID not found.")
        
    try:
        reply_text = (
            f"💬 <b>SUPPORT REPLY</b>\n{DIVIDER}\n\n"
            f"{m.text}"
        )
        if m.text:
            await m.bot.send_message(uid, reply_text)
        elif m.photo:
            await m.bot.send_photo(uid, photo=m.photo[-1].file_id, caption=f"💬 <b>SUPPORT REPLY</b>\n{DIVIDER}\n\n{m.caption or ''}")
            
        await m.answer(f"✅ Reply sent to User <code>{uid}</code>.", reply_markup=kb.admin_back())
    except Exception as e:
        await m.answer(f"❌ Failed to send reply: {e}", reply_markup=kb.admin_back())


@router.callback_query(F.data.startswith("a_ban_id:"))
async def a_ticket_ban(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        return await cb.answer("⛔", show_alert=True)
    uid = int(cb.data.split(":")[1])
    await db.set_banned(uid, True)
    await cb.message.edit_text(f"🚫 User <code>{uid}</code> has been banned.", reply_markup=kb.admin_back())
    await cb.answer()


# ---------- PENDING TOPUPS MANAGEMENT ----------
@router.callback_query(F.data == "a_topups_list")
async def a_topups_list(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        return await cb.answer("⛔", show_alert=True)
        
    topups = await db.get_pending_topups()
    if not topups:
        await cb.message.edit_text("⏳ <b>Pending Top-ups</b>\n\n✅ There are no pending top-up requests.", reply_markup=kb.admin_back())
        return await cb.answer()
        
    await cb.message.edit_text(
        f"⏳ <b>PENDING TOP-UPS</b>\n{DIVIDER}\n\nSelect a request to review/approve 👇",
        reply_markup=kb.pending_topups_menu(topups)
    )
    await cb.answer()


@router.callback_query(F.data.startswith("a_tpreview:"))
async def a_topup_preview(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        return await cb.answer("⛔", show_alert=True)
        
    tid = int(cb.data.split(":")[1])
    tu = await db.get_topup(tid)
    if not tu:
        return await cb.answer("Top-up request not found!", show_alert=True)
        
    prof = await db.user_profile(tu[1])
    name = prof["name"] if prof else "Unknown"
    
    await cb.message.edit_text(
        f"💳 <b>Top-up request #{tid}</b>\n{DIVIDER}\n\n"
        f"User: <code>{tu[1]}</code> ({name})\n"
        f"Amount: <b>${tu[2]:.2f}</b>\n"
        f"Status: <b>{tu[3].upper()}</b>\n\n"
        f"Verify the payment on Binance Pay, then approve/reject below:",
        reply_markup=kb.topup_review_menu(tid)
    )
    await cb.answer()


@router.callback_query(F.data == "a_backup")
async def a_backup(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        return await cb.answer("⛔", show_alert=True)
        
    from aiogram.types import FSInputFile
    from config import DB_PATH
    import os
    
    if not os.path.exists(DB_PATH):
        return await cb.answer("❌ Database file not found!", show_alert=True)
        
    try:
        db_file = FSInputFile(DB_PATH, filename="store_backup.db")
        await cb.message.answer_document(db_file, caption="📦 <b>Nova X Live Database Backup</b>")
        await cb.answer("✅ Backup sent successfully!")
    except Exception as e:
        await cb.answer(f"❌ Failed to send backup: {e}", show_alert=True)


# ---------- DATABASE RESTORE ----------
@router.message(F.document)
async def admin_restore_db(m: Message):
    if not is_admin(m.from_user.id):
        return
        
    doc = m.document
    if doc.file_name.endswith(".db"):
        from config import DB_PATH
        
        progress = await m.answer("⏳ Downloading and restoring database backup...")
        try:
            file_info = await m.bot.get_file(doc.file_id)
            await m.bot.download_file(file_info.file_path, DB_PATH)
            
            await progress.edit_text(
                f"✅ <b>DATABASE RESTORED!</b>\n{DIVIDER}\n\n"
                f"Your backup file <code>{doc.file_name}</code> has been uploaded to the server volume successfully!\n\n"
                f"🔄 <i>Please restart the bot service on Railway to apply all changes correctly.</i>"
            )
        except Exception as e:
            await progress.edit_text(f"❌ <b>Restoration Failed:</b>\n\n<code>{e}</code>")

