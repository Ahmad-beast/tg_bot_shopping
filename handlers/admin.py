from contextlib import suppress

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from config import CHANNEL_ID
from states import ChannelPost
from config import ADMIN_IDS, DIVIDER, is_admin, CHANNEL_ID


import csv
import io
from states import (AddProduct, EditProduct, AddStock, Broadcast, AddBalance, BanUser, BulkUpload, UserLookup, CustomBalance)
import database as db
import keyboards as kb
from config import ADMIN_IDS, DIVIDER, is_admin
from states import AddProduct, EditProduct, AddStock, Broadcast, AddBalance, BanUser

router = Router()


@router.callback_query(F.data == "admin")
async def admin_home(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id):
        return await cb.answer("⛔ Access Denied!", show_alert=True)
    await state.clear()
    await cb.message.edit_text(
        f"<b>👑 ADMIN PANEL</b>\n{DIVIDER}\n\nManage your store below 👇",
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
    await state.set_state(AddProduct.emoji)
    await cb.message.edit_text("➕ <b>Add Product</b>\n\nSend an <b>emoji</b> (e.g. 🎬):")
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



@router.message(BulkUpload.file)
async def bulk_no_file(m: Message):
    await m.answer("❌ Please upload a .csv <b>file</b> (not text).")


@router.message(AddProduct.emoji)
async def ap_emoji(m: Message, state: FSMContext):
    await state.update_data(emoji=m.text)
    await state.set_state(AddProduct.name)
    await m.answer("Send product <b>name</b>:")


@router.message(AddProduct.name)
async def ap_name(m: Message, state: FSMContext):
    await state.update_data(name=m.text)
    await state.set_state(AddProduct.price)
    await m.answer("Send <b>price</b> (USD, e.g. 5):")


@router.message(AddProduct.price)
async def ap_price(m: Message, state: FSMContext):
    try:
        price = float(m.text)
        if price < 0:
            raise ValueError
    except ValueError:
        return await m.answer("❌ Enter a valid price.")
    await state.update_data(price=price)
    await state.set_state(AddProduct.desc)
    await m.answer("Send a short <b>description</b>:")


@router.message(AddProduct.desc)
async def ap_desc(m: Message, state: FSMContext):
    await state.update_data(desc=m.text)
    await state.set_state(AddProduct.stock)
    await m.answer(
        "Send the <b>stock items</b> (accounts/keys/IDs).\n"
        "One item per line — each line is delivered to one buyer:")


@router.message(AddProduct.stock)
async def ap_stock(m: Message, state: FSMContext):
    data = await state.get_data()
    items = [line.strip() for line in m.text.splitlines() if line.strip()]
    pid = await db.add_product(data["emoji"], data["name"], data["price"], data["desc"])
    if items:
        await db.add_stock_items(pid, items)
    await state.clear()
    await m.answer(
        f"✅ Product <b>{data['name']}</b> added with {len(items)} stock item(s)!",
        reply_markup=kb.admin_back())

    # Notify all users about the new product
    announce = (
        f"🆕 <b>NEW PRODUCT AVAILABLE!</b>\n{DIVIDER}\n\n"
        f"{data['emoji']} <b>{data['name']}</b>\n\n"
        f"{data['desc']}\n\n💰 <b>Price:</b> ${data['price']:.2f}\n\n"
        f"Open the store and grab it now! 🛒")
    sent = 0
    for uid in await db.all_user_ids():
        with suppress(Exception):
            await m.bot.send_message(uid, announce)
            sent += 1
    await m.answer(f"📢 New product announced to {sent} user(s).")
    # Auto-post new product to the channel (with price + Buy Now button)
    if CHANNEL_ID:
        with suppress(Exception):
            await m.bot.send_message(
                CHANNEL_ID,
                f"🆕 <b>NEW PRODUCT!</b>\n{DIVIDER}\n\n"
                f"{data['emoji']} <b>{data['name']}</b>\n\n"
                f"{data['desc']}\n\n💰 <b>Price:</b> ${data['price']:.2f}\n\n"
                f"🛒 Available now 👇",
                reply_markup=kb.buy_now_kb(),
            )




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
    field, value = data["field"], m.text
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
    await db.update_balance(tu[1], tu[2])
    await db.set_topup_status(tid, "approved")
    await cb.message.edit_text(f"✅ Top-up #{tid} approved. ${tu[2]:.2f} credited.")
    with suppress(Exception):
        await cb.bot.send_message(tu[1], f"✅ Your top-up of ${tu[2]:.2f} was approved!")
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
    await cb.message.edit_text("📢 Send the <b>message</b> to broadcast to all users:")
    await cb.answer()


@router.message(Broadcast.message)
async def bc_send(m: Message, state: FSMContext):
    await state.clear()
    sent, failed = 0, 0
    for uid in await db.all_user_ids():
        try:
            await m.bot.send_message(uid, f"📢 <b>Announcement</b>\n\n{m.html_text}")
            sent += 1
        except Exception:
            failed += 1
    await m.answer(f"✅ Broadcast done.\nSent: {sent} | Failed: {failed}", reply_markup=kb.admin_back())


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

