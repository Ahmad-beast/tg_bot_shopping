from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import SUPPORT_USERNAME


def main_menu(is_admin=False):
    rows = [
        [InlineKeyboardButton(text="🛒 Browse Products", callback_data="products")],
        [
            InlineKeyboardButton(text="💰 Balance", callback_data="balance"),
            InlineKeyboardButton(text="📦 My Orders", callback_data="orders"),
        ],
        [
            InlineKeyboardButton(text="💬 Support", callback_data="support"),
            InlineKeyboardButton(text="ℹ️ About", callback_data="about"),
        ],
    ]
    if is_admin:
        rows.append([InlineKeyboardButton(text="👑 Admin Panel", callback_data="admin")])
    rows.append([InlineKeyboardButton(text="❌ Close", callback_data="close")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def products_menu(products, stocks):
    """products: rows; stocks: dict {pid: count}"""
    rows = []
    for p in products:  # (id, emoji, name, price, desc)
        cnt = stocks.get(p[0], 0)
        tag = f"${p[3]:.2f}" if cnt > 0 else "❌ Out of stock"
        rows.append([InlineKeyboardButton(
            text=f"{p[1]} {p[2]} — {tag}", callback_data=f"view:{p[0]}")])
    rows.append([
        InlineKeyboardButton(text="⬅️ Back", callback_data="home"),
        InlineKeyboardButton(text="❌ Close", callback_data="close"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def product_detail_menu(pid, in_stock):
    rows = []
    if in_stock:
        rows.append([InlineKeyboardButton(text="✅ Buy with Balance", callback_data=f"buy:{pid}")])
    rows.append([
        InlineKeyboardButton(text="⬅️ Products", callback_data="products"),
        InlineKeyboardButton(text="🏠 Home", callback_data="home"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def balance_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
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
        [InlineKeyboardButton(text="📊 Statistics", callback_data="a_stats")],
        [
            InlineKeyboardButton(text="➕ Add Product", callback_data="a_addprod"),
            InlineKeyboardButton(text="🗂 Manage Products", callback_data="a_listprod"),
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
        [InlineKeyboardButton(text="⬅️ Back", callback_data="home")],
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
