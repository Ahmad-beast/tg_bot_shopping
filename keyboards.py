from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import SUPPORT_USERNAME


def main_menu(is_admin=False):
    rows = [
        [InlineKeyboardButton(text="🛍️ BROWSE CATALOG", callback_data="products")],
        [
            InlineKeyboardButton(text="💳 Wallet Balance", callback_data="balance"),
            InlineKeyboardButton(text="📦 My Purchases", callback_data="orders"),
        ],
        [
            InlineKeyboardButton(text="👥 Invite & Earn", callback_data="referrals"),
            InlineKeyboardButton(text="🎁 Daily Reward", callback_data="daily_claim"),
        ],
        [
            InlineKeyboardButton(text="💬 Help & Support", callback_data="support"),
            InlineKeyboardButton(text="ℹ️ About Store", callback_data="about"),
        ],
    ]
    if is_admin:
        rows.append([InlineKeyboardButton(text="⚙️ ADMIN DASHBOARD", callback_data="admin")])
    rows.append([InlineKeyboardButton(text="❌ Close Menu", callback_data="close")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def categories_menu(categories):
    rows = []
    for c in categories:  # (id, emoji, name)
        rows.append([InlineKeyboardButton(text=f"{c[1]} {c[2]}", callback_data=f"cat:{c[0]}")])
    rows.append([InlineKeyboardButton(text="✨ Show All Products", callback_data="cat_all")])
    rows.append([
        InlineKeyboardButton(text="⬅️ Back", callback_data="home"),
        InlineKeyboardButton(text="❌ Close", callback_data="close"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def products_menu(products, stocks, category_id="all"):
    """products: rows; stocks: dict {pid: count}"""
    rows = []
    for p in products:  # (id, emoji, name, price, desc, category_id)
        cnt = stocks.get(p[0], 0)
        tag = f"${p[3]:.2f}" if cnt > 0 else "❌ Out of stock"
        rows.append([InlineKeyboardButton(
            text=f"{p[1]} {p[2]} — {tag}", callback_data=f"view:{p[0]}")])
    
    # If filtered, go back to categories menu, otherwise go back home
    back_cb = "products" if category_id != "all" else "home"
    rows.append([
        InlineKeyboardButton(text="⬅️ Back", callback_data=back_cb),
        InlineKeyboardButton(text="❌ Close", callback_data="close"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def product_detail_menu(pid, in_stock, category_id=None):
    rows = []
    if in_stock:
        rows.append([InlineKeyboardButton(text="✅ Buy with Balance", callback_data=f"buy_qty:{pid}")])
    
    back_cb = f"cat:{category_id}" if category_id else "products"
    rows.append([
        InlineKeyboardButton(text="⬅️ Back", callback_data=back_cb),
        InlineKeyboardButton(text="🏠 Home", callback_data="home"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def quantity_menu(pid, available):
    rows = [
        [
            InlineKeyboardButton(text="1", callback_data=f"qsel:{pid}:1"),
            InlineKeyboardButton(text="2", callback_data=f"qsel:{pid}:2"),
            InlineKeyboardButton(text="5", callback_data=f"qsel:{pid}:5"),
        ],
        [
            InlineKeyboardButton(text="10", callback_data=f"qsel:{pid}:10"),
            InlineKeyboardButton(text="✏️ Custom", callback_data=f"qsel:{pid}:custom"),
        ],
        [
            InlineKeyboardButton(text="⬅️ Cancel", callback_data=f"view:{pid}"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def checkout_menu(pid, quantity, has_promo=False):
    rows = []
    rows.append([InlineKeyboardButton(text="✅ Confirm Purchase", callback_data=f"chk_pay:{pid}:{quantity}")])
    if not has_promo:
        rows.append([InlineKeyboardButton(text="🎟️ Apply Promo Code", callback_data=f"chk_promo:{pid}:{quantity}")])
    rows.append([InlineKeyboardButton(text="❌ Cancel", callback_data=f"view:{pid}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def review_stars_menu(product_id):
    rows = [
        [
            InlineKeyboardButton(text="⭐ 1", callback_data=f"rate:{product_id}:1"),
            InlineKeyboardButton(text="⭐ 2", callback_data=f"rate:{product_id}:2"),
            InlineKeyboardButton(text="⭐ 3", callback_data=f"rate:{product_id}:3"),
            InlineKeyboardButton(text="⭐ 4", callback_data=f"rate:{product_id}:4"),
            InlineKeyboardButton(text="⭐ 5", callback_data=f"rate:{product_id}:5"),
        ],
        [InlineKeyboardButton(text="Skip ➡️", callback_data="skip_review")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def balance_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎟️ Redeem Promo Code", callback_data="redeem_promo")],
        [InlineKeyboardButton(text="💎 Top Up (Binance Pay)", callback_data="topup")],
        [InlineKeyboardButton(text="⬅️ Back", callback_data="home")],
    ])


def back_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⬅️ Back", callback_data="home"),
            InlineKeyboardButton(text="❌ Close", callback_data="close"),
        ]
    ])


def admin_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Statistics", callback_data="a_stats"),
            InlineKeyboardButton(text="⏳ Pending Top-ups", callback_data="a_topups_list")
        ],
        [
            InlineKeyboardButton(text="➕ Add Product", callback_data="a_addprod"),
            InlineKeyboardButton(text="🗂 Manage Products", callback_data="a_listprod"),
        ],
        [
            InlineKeyboardButton(text="📁 Manage Categories", callback_data="a_categories"),
            InlineKeyboardButton(text="🎟️ Promo Codes", callback_data="a_promos"),
        ],
        [InlineKeyboardButton(text="📁 Bulk Add (CSV)", callback_data="a_bulk")],
        [
            InlineKeyboardButton(text="💳 Add Balance", callback_data="a_addbal"),
            InlineKeyboardButton(text="👤 User Lookup", callback_data="a_lookup"),
        ],
        [
            InlineKeyboardButton(text="📢 Broadcast", callback_data="a_broadcast"),
            InlineKeyboardButton(text="📣 Channel Post", callback_data="a_channel"),
        ],
        [
            InlineKeyboardButton(text="🚫 Ban User", callback_data="a_ban"),
            InlineKeyboardButton(text="✅ Unban User", callback_data="a_unban"),
        ],
        [
            InlineKeyboardButton(text="📥 Backup DB", callback_data="a_backup"),
            InlineKeyboardButton(text="⬅️ Back", callback_data="home"),
        ],
    ])


def pending_topups_menu(topups):
    """topups: list of rows (id, user_id, amount, name)"""
    rows = []
    for t in topups:
        rows.append([InlineKeyboardButton(text=f"Review #{t[0]} — {t[3]} (${t[2]:.2f})", callback_data=f"a_tpreview:{t[0]}")])
    rows.append([InlineKeyboardButton(text="⬅️ Admin Panel", callback_data="admin")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def category_admin_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Add Category", callback_data="a_addcat")],
        [InlineKeyboardButton(text="⬅️ Admin Panel", callback_data="admin")],
    ])


def promo_admin_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Create Promo Code", callback_data="a_addpromo")],
        [InlineKeyboardButton(text="⬅️ Admin Panel", callback_data="admin")],
    ])


def manage_product_menu(pid):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✏️ Name", callback_data=f"edit:{pid}:name"),
            InlineKeyboardButton(text="💲 Price", callback_data=f"edit:{pid}:price"),
        ],
        [
            InlineKeyboardButton(text="📝 Desc", callback_data=f"edit:{pid}:desc"),
            InlineKeyboardButton(text="😀 Emoji", callback_data=f"edit:{pid}:emoji"),
        ],
        [InlineKeyboardButton(text="➕ Add Stock", callback_data=f"addstock:{pid}")],
        [InlineKeyboardButton(text="🗑 Delete", callback_data=f"del:{pid}")],
        [InlineKeyboardButton(text="⬅️ Back", callback_data="a_listprod")],
    ])


def admin_back():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Admin Panel", callback_data="admin")]
    ])


def topup_review_menu(tid):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Approve", callback_data=f"tu_ok:{tid}"),
            InlineKeyboardButton(text="❌ Reject", callback_data=f"tu_no:{tid}"),
        ]
    ])


def buy_now_kb():
    from config import BOT_USERNAME
    url = f"https://t.me/{BOT_USERNAME}" if BOT_USERNAME else "https://t.me/"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Buy Now", url=url)]
    ])


def stats_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Refresh", callback_data="a_stats")],
        [InlineKeyboardButton(text="⚠️ Low Stock", callback_data="a_lowstock")],
        [InlineKeyboardButton(text="⬅️ Admin Panel", callback_data="admin")],
    ])


def addbal_user_menu(uid):
    """Quick amount buttons after selecting a user."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="+$5", callback_data=f"qbal:{uid}:5"),
            InlineKeyboardButton(text="+$10", callback_data=f"qbal:{uid}:10"),
            InlineKeyboardButton(text="+$20", callback_data=f"qbal:{uid}:20"),
        ],
        [
            InlineKeyboardButton(text="+$50", callback_data=f"qbal:{uid}:50"),
            InlineKeyboardButton(text="+$100", callback_data=f"qbal:{uid}:100"),
        ],
        [InlineKeyboardButton(text="✏️ Custom Amount", callback_data=f"cbal:{uid}")],
        [InlineKeyboardButton(text="⬅️ Admin Panel", callback_data="admin")],
    ])


def support_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎫 Open Support Ticket", callback_data="open_ticket")],
        [InlineKeyboardButton(text="👤 Direct Support Chat", url=f"https://t.me/{SUPPORT_USERNAME}")],
        [InlineKeyboardButton(text="⬅️ Back", callback_data="home")],
    ])


def admin_ticket_reply_menu(user_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Reply to User", callback_data=f"t_reply:{user_id}")],
        [InlineKeyboardButton(text="🚫 Ban User", callback_data=f"a_ban_id:{user_id}")],
    ])


def broadcast_button_choice_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚫 No Button", callback_data="bc_btn:none")],
        [InlineKeyboardButton(text="🛒 Link a Product", callback_data="bc_btn:prod")],
        [InlineKeyboardButton(text="🔗 Custom URL Button", callback_data="bc_btn:custom")],
        [InlineKeyboardButton(text="⬅️ Cancel", callback_data="admin")],
    ])


def broadcast_products_list(products):
    rows = []
    for p in products:  # (id, emoji, name, price, desc, category_id)
        rows.append([InlineKeyboardButton(text=f"{p[1]} {p[2]} (${p[3]:.2f})", callback_data=f"bc_prod:{p[0]}")])
    rows.append([InlineKeyboardButton(text="⬅️ Cancel", callback_data="admin")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
