import aiosqlite
from config import DB_PATH


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id           INTEGER PRIMARY KEY,
                name              TEXT,
                balance           REAL DEFAULT 0,
                banned            INTEGER DEFAULT 0,
                joined_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                referred_by       INTEGER DEFAULT NULL,
                referral_earnings REAL DEFAULT 0.0
            )""")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id    INTEGER PRIMARY KEY AUTOINCREMENT,
                emoji TEXT DEFAULT '📁',
                name  TEXT
            )""")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER DEFAULT NULL,
                emoji       TEXT DEFAULT '📦',
                name        TEXT,
                price       REAL,
                desc        TEXT
            )""")
        # Each delivery item (account/key) for a product. Sold when bought.
        await db.execute("""
            CREATE TABLE IF NOT EXISTS stock_items (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER,
                content    TEXT,
                sold       INTEGER DEFAULT 0
            )""")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER,
                product    TEXT,
                content    TEXT,
                price      REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS topups (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER,
                amount     REAL,
                status     TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS promo_codes (
                code       TEXT PRIMARY KEY,
                type       TEXT,
                value      REAL,
                max_uses   INTEGER,
                used_count INTEGER DEFAULT 0,
                expiry     TIMESTAMP DEFAULT NULL
            )""")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS promo_redemptions (
                code        TEXT,
                user_id     INTEGER,
                redeemed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (code, user_id)
            )""")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS daily_claims (
                user_id         INTEGER PRIMARY KEY,
                last_claimed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS reviews (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER,
                product_id INTEGER,
                rating     INTEGER,
                comment    TEXT DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
        await db.commit()

    # Run migrations for older databases (adds any missing columns)
    await _migrate()


async def _migrate():
    """Add missing columns to existing tables so old databases keep working."""
    # (table, column, definition)
    required = [
        ("users", "banned", "INTEGER DEFAULT 0"),
        ("users", "balance", "REAL DEFAULT 0"),
        ("users", "joined_at", "TIMESTAMP"),
        ("users", "referred_by", "INTEGER DEFAULT NULL"),
        ("users", "referral_earnings", "REAL DEFAULT 0.0"),
        ("products", "category_id", "INTEGER DEFAULT NULL"),
        ("products", "emoji", "TEXT DEFAULT '📦'"),
        ("products", "desc", "TEXT"),
        ("orders", "content", "TEXT"),
        ("topups", "status", "TEXT DEFAULT 'pending'"),
    ]
    async with aiosqlite.connect(DB_PATH) as db:
        for table, column, definition in required:
            # check existing columns of the table
            async with db.execute(f"PRAGMA table_info({table})") as c:
                cols = [r[1] for r in await c.fetchall()]
            if column not in cols:
                await db.execute(
                    f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        await db.commit()


# ---------- USERS ----------
async def add_user(user_id, name):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, name) VALUES (?, ?)",
            (user_id, name))
        await db.commit()


async def is_banned(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT banned FROM users WHERE user_id=?", (user_id,)) as c:
            r = await c.fetchone()
            return bool(r[0]) if r else False


async def set_banned(user_id, value):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET banned=? WHERE user_id=?", (1 if value else 0, user_id))
        await db.commit()


async def get_balance(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT balance FROM users WHERE user_id=?", (user_id,)) as c:
            r = await c.fetchone()
            return r[0] if r else 0.0


async def update_balance(user_id, amount):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (amount, user_id))
        await db.commit()


async def all_user_ids():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM users WHERE banned=0") as c:
            return [r[0] for r in await c.fetchall()]


async def user_count():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as c:
            return (await c.fetchone())[0]


async def get_user(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id,name,balance,banned FROM users WHERE user_id=?", (user_id,)) as c:
            return await c.fetchone()
        
async def user_profile(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT user_id,name,balance,banned FROM users WHERE user_id=?", (user_id,)) as c:
            u = await c.fetchone()
        if not u:
            return None
        async with db.execute(
            "SELECT COUNT(*), COALESCE(SUM(price),0) FROM orders WHERE user_id=?", (user_id,)) as c:
            o = await c.fetchone()
    return {"id": u[0], "name": u[1], "balance": u[2], "banned": bool(u[3]),
            "orders": o[0], "spent": o[1]}



# ---------- PRODUCTS ----------
async def add_product(emoji, name, price, desc, category_id=None):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO products (emoji,name,price,desc,category_id) VALUES (?,?,?,?,?)",
            (emoji, name, price, desc, category_id))
        await db.commit()
        return cur.lastrowid


async def get_products(category_id=None):
    async with aiosqlite.connect(DB_PATH) as db:
        if category_id is not None:
            async with db.execute("SELECT id,emoji,name,price,desc,category_id FROM products WHERE category_id=?", (category_id,)) as c:
                return await c.fetchall()
        else:
            async with db.execute("SELECT id,emoji,name,price,desc,category_id FROM products") as c:
                return await c.fetchall()


async def get_product(pid):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id,emoji,name,price,desc,category_id FROM products WHERE id=?", (pid,)) as c:
            return await c.fetchone()


async def delete_product(pid):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM products WHERE id=?", (pid,))
        await db.execute("DELETE FROM stock_items WHERE product_id=?", (pid,))
        await db.commit()


async def update_product_field(pid, field, value):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE products SET {field}=? WHERE id=?", (value, pid))
        await db.commit()


# ---------- STOCK ----------
async def add_stock_items(product_id, items):
    """items: list of strings, each is one deliverable account/key."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executemany(
            "INSERT INTO stock_items (product_id, content) VALUES (?, ?)",
            [(product_id, it) for it in items])
        await db.commit()


async def stock_count(product_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM stock_items WHERE product_id=? AND sold=0", (product_id,)) as c:
            return (await c.fetchone())[0]


async def take_stock_items(product_id, quantity):
    """Atomically fetch + mark N unsold items as sold. Returns list of contents, or empty list if insufficient."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id, content FROM stock_items WHERE product_id=? AND sold=0 LIMIT ?",
            (product_id, quantity)) as c:
            rows = await c.fetchall()
        if len(rows) < quantity:
            return []
        ids = [r[0] for r in rows]
        placeholders = ",".join("?" for _ in ids)
        await db.execute(f"UPDATE stock_items SET sold=1 WHERE id IN ({placeholders})", ids)
        await db.commit()
        return [r[1] for r in rows]


async def take_one_stock(product_id):
    """Atomically fetch + mark one unsold item as sold. Returns content or None."""
    res = await take_stock_items(product_id, 1)
    return res[0] if res else None


# ---------- ORDERS ----------
async def add_order(user_id, product, content, price):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO orders (user_id,product,content,price) VALUES (?,?,?,?)",
            (user_id, product, content, price))
        await db.commit()


async def get_user_orders(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT product,content,price,created_at FROM orders WHERE user_id=? ORDER BY id DESC",
            (user_id,)) as c:
            return await c.fetchall()


async def order_stats():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*), COALESCE(SUM(price),0) FROM orders") as c:
            return await c.fetchone()


# ---------- TOPUPS ----------
async def create_topup(user_id, amount):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO topups (user_id,amount) VALUES (?,?)", (user_id, amount))
        await db.commit()
        return cur.lastrowid


async def get_topup(tid):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id,user_id,amount,status FROM topups WHERE id=?", (tid,)) as c:
            return await c.fetchone()


async def set_topup_status(tid, status):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE topups SET status=? WHERE id=?", (status, tid))
        await db.commit()

# ---------- ADVANCED STATS ----------
async def best_selling(limit=5):
    """Top products by units sold."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT product, COUNT(*) c, COALESCE(SUM(price),0) rev "
            "FROM orders GROUP BY product ORDER BY c DESC LIMIT ?", (limit,)) as c:
            return await c.fetchall()


async def top_buyers(limit=5):
    """Top users by total spent, joined with their name."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT o.user_id, COALESCE(u.name,'Unknown'), COUNT(*) c, COALESCE(SUM(o.price),0) spent "
            "FROM orders o LEFT JOIN users u ON u.user_id=o.user_id "
            "GROUP BY o.user_id ORDER BY spent DESC LIMIT ?", (limit,)) as c:
            return await c.fetchall()


async def revenue_since(hours):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*), COALESCE(SUM(price),0) FROM orders "
            "WHERE created_at >= datetime('now', ?)", (f'-{hours} hours',)) as c:
            return await c.fetchone()


async def total_balance_held():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COALESCE(SUM(balance),0) FROM users") as c:
            return (await c.fetchone())[0]


async def banned_count():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users WHERE banned=1") as c:
            return (await c.fetchone())[0]


async def total_stock_available():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM stock_items WHERE sold=0") as c:
            return (await c.fetchone())[0]


async def low_stock_products(threshold=3):
    """Products with unsold stock <= threshold."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT p.emoji, p.name, "
            "(SELECT COUNT(*) FROM stock_items s WHERE s.product_id=p.id AND s.sold=0) cnt "
            "FROM products p ORDER BY cnt ASC") as c:
            rows = await c.fetchall()
    return [r for r in rows if r[2] <= threshold]


async def pending_topups_count():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM topups WHERE status='pending'") as c:
            return (await c.fetchone())[0]


async def find_users_by_name(query, limit=10):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT user_id, name, balance FROM users WHERE name LIKE ? LIMIT ?",
            (f"%{query}%", limit)) as c:
            return await c.fetchall()


async def recent_users(limit=10):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT user_id, name, balance FROM users ORDER BY rowid DESC LIMIT ?", (limit,)) as c:
            return await c.fetchall()


# ---------- CATEGORIES ----------
async def add_category(emoji, name):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("INSERT INTO categories (emoji, name) VALUES (?, ?)", (emoji, name))
        await db.commit()
        return cur.lastrowid


async def get_categories():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id, emoji, name FROM categories") as c:
            return await c.fetchall()


async def get_category(cid):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id, emoji, name FROM categories WHERE id=?", (cid,)) as c:
            return await c.fetchone()


async def delete_category(cid):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM categories WHERE id=?", (cid,))
        await db.execute("UPDATE products SET category_id=NULL WHERE category_id=?", (cid,))
        await db.commit()


# ---------- REFERRALS ----------
async def set_referrer(user_id, referrer_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT referred_by FROM users WHERE user_id=?", (user_id,)) as c:
            row = await c.fetchone()
        if row and row[0] is None:
            if referrer_id != user_id:
                await db.execute("UPDATE users SET referred_by=? WHERE user_id=?", (referrer_id, user_id))
                await db.commit()


async def get_referral_stats(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users WHERE referred_by=?", (user_id,)) as c:
            count = (await c.fetchone())[0]
        async with db.execute("SELECT referral_earnings FROM users WHERE user_id=?", (user_id,)) as c:
            earnings_row = await c.fetchone()
            earnings = earnings_row[0] if earnings_row else 0.0
        return count, earnings


async def add_referral_earnings(user_id, amount):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET balance=balance+?, referral_earnings=referral_earnings+? WHERE user_id=?", (amount, amount, user_id))
        await db.commit()


# ---------- PROMO CODES ----------
async def add_promo_code(code, type_, value, max_uses, expiry=None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO promo_codes (code, type, value, max_uses, expiry) VALUES (?, ?, ?, ?, ?)",
                         (code.upper(), type_, value, max_uses, expiry))
        await db.commit()


async def get_promo_code(code):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT code, type, value, max_uses, used_count, expiry FROM promo_codes WHERE code=?", (code.upper(),)) as c:
            return await c.fetchone()


async def get_all_promos():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT code, type, value, max_uses, used_count, expiry FROM promo_codes") as c:
            return await c.fetchall()


async def is_promo_used(code, user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT 1 FROM promo_redemptions WHERE code=? AND user_id=?", (code.upper(), user_id)) as c:
            return (await c.fetchone()) is not None


async def use_promo_code(code, user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT 1 FROM promo_redemptions WHERE code=? AND user_id=?", (code.upper(), user_id)) as c:
            if await c.fetchone():
                return False
        await db.execute("INSERT INTO promo_redemptions (code, user_id) VALUES (?, ?)", (code.upper(), user_id))
        await db.execute("UPDATE promo_codes SET used_count=used_count+1 WHERE code=?", (code.upper(),))
        await db.commit()
        return True


async def delete_promo_code(code):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM promo_codes WHERE code=?", (code.upper(),))
        await db.execute("DELETE FROM promo_redemptions WHERE code=?", (code.upper(),))
        await db.commit()


# ---------- DAILY REWARDS ----------
async def can_claim_daily(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT 1 FROM daily_claims WHERE user_id=? AND last_claimed_at > datetime('now', '-24 hours')",
            (user_id,)) as c:
            return (await c.fetchone()) is None


async def claim_daily_reward(user_id, amount):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO daily_claims (user_id, last_claimed_at) VALUES (?, datetime('now'))",
            (user_id,))
        await db.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (amount, user_id))
        await db.commit()


# ---------- REVIEWS ----------
async def add_review(user_id, product_id, rating, comment=None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO reviews (user_id, product_id, rating, comment) VALUES (?, ?, ?, ?)",
            (user_id, product_id, rating, comment))
        await db.commit()


async def get_product_rating(product_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COALESCE(AVG(rating), 0.0), COUNT(rating) FROM reviews WHERE product_id=?",
            (product_id,)) as c:
            row = await c.fetchone()
            return row[0], row[1]


async def get_pending_topups():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT t.id, t.user_id, t.amount, COALESCE(u.name, 'Unknown') "
            "FROM topups t LEFT JOIN users u ON u.user_id=t.user_id "
            "WHERE t.status='pending'") as c:
            return await c.fetchall()
