import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [
    int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()
]
BINANCE_PAY_ID = os.getenv("BINANCE_PAY_ID", "N/A")
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "your_username")

DIVIDER = "━━━━━━━━━━━━━━━━━━━━"
DB_PATH = os.getenv("DB_PATH", "store.db")

SENSITIVE_DELETE_AFTER = 30  # seconds
ANTISPAM_RATE = 0.7          # min seconds between actions per user
MIN_TOPUP = 1.0              # minimum top-up amount (USD)

CHANNEL_ID = os.getenv("CHANNEL_ID")  # e.g. -1001234567890
LINK_MUTE_SECONDS = 60  # mute duration for sending links
WARN_BEFORE_MUTE = 1  # number of warnings before mute

CHANNEL_ID = os.getenv("CHANNEL_ID")               # e.g. -1001234567890
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")   # e.g. mychannel (without @)
LINK_MUTE_SECONDS = 60

BOT_USERNAME = os.getenv("BOT_USERNAME")  # without @, e.g. shopflixd_bot

REFERRAL_COMMISSION_PERCENT = 10.0  # 10% commission on top-ups
DAILY_REWARD_AMOUNT = 0.05  # $0.05 daily check-in reward

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS
