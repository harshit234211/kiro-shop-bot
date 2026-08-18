import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
BASE_DIR = Path(__file__).resolve().parent
env_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=env_path)

# Bot Configuration
token_env = os.getenv("BOT_TOKEN", "").strip()
if not token_env or token_env == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
    BOT_TOKEN = "8815350090:AAHcgEg8hp1tbGOjfGyIJq22VUa0ihCROXU"
else:
    BOT_TOKEN = token_env

# Database Configuration
DB_PATH = os.getenv("DB_PATH", str(BASE_DIR / "data" / "kiro_shop.db"))

# Financial & Security Settings
MIN_DEPOSIT_AMOUNT = float(os.getenv("MIN_DEPOSIT_AMOUNT", "10.0"))

# Payment Gateway Configuration (TranzUPI)
key_env = os.getenv("TRANZUPI_API_KEY", "").strip()
TRANZUPI_API_KEY = key_env if key_env else "64c1cb9202d9646a0a75a7781decf3ee"
TRANZUPI_MERCHANT_ID = os.getenv("TRANZUPI_MERCHANT_ID", "")
TRANZUPI_SECRET = os.getenv("TRANZUPI_SECRET", "")
TRANZUPI_UPI_ID = os.getenv("TRANZUPI_UPI_ID", "paytm.s3h7hcx@pty")
MERCHANT_NAME = os.getenv("MERCHANT_NAME", "RAJ NARAYAN")

# Admin Security Settings
admin_ids_str = os.getenv("ADMIN_USER_IDS", "").strip()
if admin_ids_str:
    ADMIN_USER_IDS = [int(x.strip()) for x in admin_ids_str.split(",") if x.strip().isdigit()]
else:
    ADMIN_USER_IDS = [8568912134, 8021345661]

def is_admin(telegram_id: int) -> bool:
    """Checks if telegram_id is authorized in ADMIN_USER_IDS."""
    return telegram_id in ADMIN_USER_IDS

# Central Feature Toggle Configuration
FEATURES = {
    "wallet": True,
    "tournament": True,
    "sensi": True,
    "panel": True,
    "gmail_recovery": True,
    "profile": True,
    "spin": True,
    "support": True,
    "referral": True,
    "dk_ai": True,
    "instagram": True
}
