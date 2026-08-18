import sqlite3
import os
import random
import uuid
import datetime
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path
from config import DB_PATH
from logger import logger

def get_connection() -> sqlite3.Connection:
    """Creates directory if needed and returns a database connection."""
    db_file = Path(DB_PATH)
    db_file.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_file), timeout=15.0)
    conn.row_factory = sqlite3.Row
    return conn

def init_db() -> None:
    """Initializes SQLite database tables and indexes."""
    conn = get_connection()
    try:
        with conn:
            # Create users table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER UNIQUE NOT NULL,
                    username TEXT,
                    first_name TEXT,
                    balance REAL NOT NULL DEFAULT 0.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Create deposits table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS deposits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_user_id INTEGER NOT NULL,
                    order_id TEXT UNIQUE NOT NULL,
                    transaction_id TEXT,
                    amount REAL NOT NULL,
                    gateway TEXT NOT NULL DEFAULT 'TranzUPI',
                    status TEXT NOT NULL DEFAULT 'PENDING',
                    payment_reference TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    verified_at TIMESTAMP,
                    FOREIGN KEY (telegram_user_id) REFERENCES users(telegram_id)
                );
            """)

            # Indexes for performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_deposits_order_id ON deposits(order_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_deposits_telegram_user ON deposits(telegram_user_id, created_at DESC);")

            # Create Sensi Buy tables
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sensi_catalog (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    brand TEXT NOT NULL,
                    model TEXT NOT NULL,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(brand, model)
                );
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS sensi_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS sensi_orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id TEXT UNIQUE NOT NULL,
                    telegram_id INTEGER NOT NULL,
                    brand TEXT NOT NULL,
                    model TEXT NOT NULL,
                    ram TEXT NOT NULL,
                    storage TEXT NOT NULL,
                    payment_method TEXT NOT NULL,
                    price REAL NOT NULL,
                    status TEXT NOT NULL DEFAULT 'PENDING',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS sensi_deliveries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER NOT NULL,
                    order_id TEXT UNIQUE NOT NULL,
                    brand TEXT NOT NULL,
                    model TEXT NOT NULL,
                    variant TEXT NOT NULL,
                    general INTEGER NOT NULL,
                    red_dot INTEGER NOT NULL,
                    scope_2x INTEGER NOT NULL,
                    scope_4x INTEGER NOT NULL,
                    sniper INTEGER NOT NULL,
                    free_look INTEGER NOT NULL,
                    fire_button INTEGER NOT NULL,
                    dpi INTEGER NOT NULL,
                    pointer_speed INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (order_id) REFERENCES sensi_orders(order_id)
                );
            """)

            # Create Gmail Recovery table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS gmail_recovery_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER NOT NULL,
                    email TEXT NOT NULL,
                    problem_description TEXT NOT NULL,
                    order_id TEXT UNIQUE NOT NULL,
                    payment_method TEXT NOT NULL,
                    amount REAL NOT NULL,
                    status TEXT NOT NULL DEFAULT 'PENDING_PAYMENT',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Create Panel Buy catalog and orders tables
            conn.execute("""
                CREATE TABLE IF NOT EXISTS panel_catalog (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_name TEXT UNIQUE NOT NULL,
                    price REAL DEFAULT NULL,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS panel_orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id TEXT UNIQUE NOT NULL,
                    telegram_id INTEGER NOT NULL,
                    product_name TEXT NOT NULL,
                    price REAL NOT NULL,
                    payment_method TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'PENDING',
                    key_code TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Create Daily Spin and Referral tracking tables
            conn.execute("""
                CREATE TABLE IF NOT EXISTS spin_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER NOT NULL,
                    result INTEGER NOT NULL,
                    is_special INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS referrals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    referrer_id INTEGER NOT NULL,
                    referred_user_id INTEGER UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Create DK AI orders table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS dk_ai_orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id TEXT UNIQUE NOT NULL,
                    telegram_id INTEGER NOT NULL,
                    price REAL NOT NULL,
                    payment_method TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'PENDING',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Create Panel Variants table (Duration-based pricing & stock control)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS panel_variants (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_name TEXT NOT NULL,
                    duration TEXT NOT NULL,
                    price REAL DEFAULT NULL,
                    is_in_stock INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(product_name, duration)
                );
            """)

            # Create Tournament orders table (₹99 entry system lock)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tournament_orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id TEXT UNIQUE NOT NULL,
                    telegram_id INTEGER NOT NULL,
                    price REAL NOT NULL,
                    payment_method TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'PENDING',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            conn.execute("CREATE INDEX IF NOT EXISTS idx_sensi_orders_id ON sensi_orders(order_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sensi_orders_user ON sensi_orders(telegram_id, created_at DESC);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sensi_deliveries_user ON sensi_deliveries(telegram_id, created_at DESC);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_gmail_requests_user ON gmail_recovery_requests(telegram_id, created_at DESC);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_gmail_requests_order ON gmail_recovery_requests(order_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_panel_orders_user ON panel_orders(telegram_id, created_at DESC);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_panel_variants_product ON panel_variants(product_name);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_panel_orders_id ON panel_orders(order_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_spin_history_user ON spin_history(telegram_id, created_at DESC);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_referrals_referrer ON referrals(referrer_id);")

            # Seed default Sensi price (₹59.0) and Gmail fee (₹299.0)
            conn.execute("INSERT INTO sensi_settings (key, value) VALUES ('sensi_price', '59.0') ON CONFLICT(key) DO UPDATE SET value = '59.0';")
            conn.execute("INSERT OR IGNORE INTO sensi_settings (key, value) VALUES ('gmail_fee', '299.0');")

            # Seed 16 initial unique panel products if catalog is empty
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM panel_catalog")
            if cursor.fetchone()["count"] == 0:
                exact_panels = [
                    "BALA MOD MAIN ID",
                    "BR MOD ROOT",
                    "DRIP CLIENT APKMOD",
                    "DRIP CLIENT PROXY",
                    "DRIP CLIENT ROOT",
                    "ESIGN CERTIFICATE",
                    "HG CHEATS APKMOD",
                    "HG CHEATS PROXY",
                    "IOS FLUORITE",
                    "IOS MIGUEL (MONITE)",
                    "PATO TEAM MOD",
                    "PRIME HOOK APKMOD",
                    "RAPID CORE ROOT",
                    "REAPER X PRO ROOT",
                    "SILENT CHEATS NONROOT",
                    "SILENT CHEATS ROOT"
                ]
                conn.executemany("INSERT OR IGNORE INTO panel_catalog (product_name, price) VALUES (?, NULL)", [(p,) for p in exact_panels])
                logger.info(f"Seeded panel catalog with {len(exact_panels)} unique products.")

            # Seed panel variants with exact requested prices & stock statuses
            exact_variants = [
                # BR MOD ROOT
                ("BR MOD ROOT", "1 Day", 70.0, 1),
                ("BR MOD ROOT", "7 Days", 300.0, 1),
                ("BR MOD ROOT", "15 Days", 500.0, 1),
                ("BR MOD ROOT", "30 Days", 700.0, 1),

                # DRIP CLIENT PROXY
                ("DRIP CLIENT PROXY", "1 Day", 59.0, 1),
                ("DRIP CLIENT PROXY", "3 Days", 139.0, 1),
                ("DRIP CLIENT PROXY", "7 Days", 249.0, 1),
                ("DRIP CLIENT PROXY", "30 Days", 599.0, 1),

                # IOS FLUORITE
                ("IOS FLUORITE", "1 Day", 400.0, 1),
                ("IOS FLUORITE", "7 Days", 1340.0, 1),
                ("IOS FLUORITE", "30 Days", 2200.0, 1),

                # IOS MIGUEL (MONITE)
                ("IOS MIGUEL (MONITE)", "1 Day", 390.0, 1),
                ("IOS MIGUEL (MONITE)", "7 Days", 990.0, 1),
                ("IOS MIGUEL (MONITE)", "30 Days", 1980.0, 1),

                # HG CHEATS PROXY
                ("HG CHEATS PROXY", "1 Day", 75.0, 1),
                ("HG CHEATS PROXY", "7 Days", 290.0, 1),
                ("HG CHEATS PROXY", "10 Days", 340.0, 1),
                ("HG CHEATS PROXY", "30 Days", 790.0, 1),

                # Out of Stock / Unpriced Default Items
                ("BALA MOD MAIN ID", "1 Day", None, 0),
                ("DRIP CLIENT APKMOD", "1 Day", None, 0),
                ("DRIP CLIENT ROOT", "1 Day", None, 0),
                ("ESIGN CERTIFICATE", "1 Day", None, 0),
                ("HG CHEATS APKMOD", "1 Day", None, 0),
                ("PATO TEAM MOD", "1 Day", None, 0),
                ("PRIME HOOK APKMOD", "1 Day", None, 0),
                ("RAPID CORE ROOT", "1 Day", None, 0),
                ("REAPER X PRO ROOT", "1 Day", None, 0),
                ("SILENT CHEATS NONROOT", "1 Day", None, 0),
                ("SILENT CHEATS ROOT", "1 Day", None, 0),
            ]
            conn.executemany("""
                INSERT OR IGNORE INTO panel_variants (product_name, duration, price, is_in_stock)
                VALUES (?, ?, ?, ?)
            """, exact_variants)

            # Seed initial mobile brand catalog if empty
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM sensi_catalog")
            if cursor.fetchone()["count"] == 0:
                default_catalog = [
                    ("Vivo", "Vivo T4x 5G"), ("Vivo", "Vivo T3 5G"), ("Vivo", "Vivo T2 Pro"), ("Vivo", "Vivo V50"), ("Vivo", "Vivo V40"), ("Vivo", "Vivo Y300"), ("Vivo", "Vivo Y200"), ("Vivo", "Vivo Y100"),
                    ("Samsung", "Samsung A15"), ("Samsung", "Samsung A35"), ("Samsung", "Samsung M35"), ("Samsung", "Samsung S24"), ("Samsung", "Samsung F15"), ("Samsung", "Samsung A55"), ("Samsung", "Samsung S23 FE"),
                    ("Realme", "Realme P1 5G"), ("Realme", "Realme Narzo 70"), ("Realme", "Realme 12 Pro+"), ("Realme", "Realme GT 6T"), ("Realme", "Realme 13 Pro"),
                    ("Xiaomi", "Xiaomi 14"), ("Xiaomi", "Xiaomi 13 Pro"),
                    ("Redmi", "Redmi Note 13 Pro+"), ("Redmi", "Redmi 13C"), ("Redmi", "Redmi Note 12"), ("Redmi", "Redmi 12 5G"),
                    ("POCO", "POCO X6 Pro"), ("POCO", "POCO M6 Pro"), ("POCO", "POCO F6"), ("POCO", "POCO C65"), ("POCO", "POCO X5 Pro"),
                    ("iQOO", "iQOO Z9 5G"), ("iQOO", "iQOO Neo 9 Pro"), ("iQOO", "iQOO 12"), ("iQOO", "iQOO Z7 Pro"),
                    ("OnePlus", "OnePlus Nord CE4"), ("OnePlus", "OnePlus 12R"), ("OnePlus", "OnePlus 12"), ("OnePlus", "OnePlus Nord 4"), ("OnePlus", "OnePlus 11R"),
                    ("Motorola", "Moto G64"), ("Motorola", "Moto Edge 50 Fusion"), ("Motorola", "Moto G84"), ("Motorola", "Moto Edge 40 Neo"),
                    ("Infinix", "Infinix GT 20 Pro"), ("Infinix", "Infinix Note 40"), ("Infinix", "Infinix Smart 8"),
                    ("Tecno", "Tecno Pova 6 Pro"), ("Tecno", "Tecno Camon 30"),
                    ("Lava", "Lava Blaze Curve 5G"), ("Lava", "Lava Agni 2"),
                    ("Nothing", "Nothing Phone 2a"), ("Nothing", "Nothing Phone 2"), ("Nothing", "CMF Phone 1"),
                    ("Apple", "iPhone 13"), ("Apple", "iPhone 14"), ("Apple", "iPhone 15"), ("Apple", "iPhone 15 Pro"), ("Apple", "iPhone 16"), ("Apple", "iPhone 16 Pro"),
                    ("Google Pixel", "Pixel 7a"), ("Google Pixel", "Pixel 8"), ("Google Pixel", "Pixel 8a"), ("Google Pixel", "Pixel 9"),
                    ("OPPO", "OPPO Reno 12 Pro"), ("OPPO", "OPPO F27 Pro+"), ("OPPO", "OPPO A3 Pro"),
                    ("Nokia", "Nokia G42 5G"),
                    ("Asus", "ROG Phone 8 Pro"),
                    ("Honor", "Honor 200 5G"),
                    ("Huawei", "Huawei P60 Pro"),
                    ("Lenovo", "Lenovo Legion Phone")
                ]
                conn.executemany("INSERT OR IGNORE INTO sensi_catalog (brand, model, is_active) VALUES (?, ?, 1)", default_catalog)
                logger.info(f"Seeded default mobile catalog with {len(default_catalog)} models.")

        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    finally:
        conn.close()

def sync_user_balance_integrity(telegram_id: int) -> float:
    """
    Self-healing balance integrity check:
    Calculates exact net balance = (Total Approved Deposits + Spin Rewards) - Total Completed Purchases.
    If stored balance is less than calculated net balance, automatically heals and updates user balance.
    Returns the verified wallet balance.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        
        # Ensure user exists first
        cursor.execute("""
            INSERT INTO users (telegram_id, username, first_name, balance)
            VALUES (?, 'User', 'User', 0.0)
            ON CONFLICT(telegram_id) DO NOTHING;
        """, (telegram_id,))
        
        # 1. Total Successful Deposits (Include all successful status tags)
        cursor.execute("SELECT SUM(amount) as total FROM deposits WHERE telegram_user_id = ? AND status IN ('SUCCESS', 'COMPLETED', 'PAID', 'SUCCESSFUL', '1')", (telegram_id,))
        dep_row = cursor.fetchone()
        tot_dep = float(dep_row["total"]) if (dep_row and dep_row["total"]) else 0.0
        
        # 2. Total Spin Rewards
        cursor.execute("SELECT SUM(result) as total FROM spin_history WHERE telegram_id = ?", (telegram_id,))
        spin_row = cursor.fetchone()
        tot_spin = float(spin_row["total"]) if (spin_row and spin_row["total"]) else 0.0

        # 3. Total Sensi Spent
        cursor.execute("SELECT SUM(price) as total FROM sensi_orders WHERE telegram_id = ? AND status = 'SUCCESS'", (telegram_id,))
        sensi_row = cursor.fetchone()
        tot_sensi = float(sensi_row["total"]) if (sensi_row and sensi_row["total"]) else 0.0

        # 4. Total Panel Spent
        cursor.execute("SELECT SUM(price) as total FROM panel_orders WHERE telegram_id = ? AND status = 'SUCCESS'", (telegram_id,))
        panel_row = cursor.fetchone()
        tot_panel = float(panel_row["total"]) if (panel_row and panel_row["total"]) else 0.0

        # 5. Total Tournament Spent
        cursor.execute("SELECT SUM(price) as total FROM tournament_orders WHERE telegram_id = ? AND status = 'SUCCESS'", (telegram_id,))
        trn_row = cursor.fetchone()
        tot_trn = float(trn_row["total"]) if (trn_row and trn_row["total"]) else 0.0

        # 6. Total DK AI Spent
        cursor.execute("SELECT SUM(price) as total FROM dk_ai_orders WHERE telegram_id = ? AND status = 'SUCCESS'", (telegram_id,))
        dk_row = cursor.fetchone()
        tot_dk = float(dk_row["total"]) if (dk_row and dk_row["total"]) else 0.0

        # 7. Total Gmail Spent
        cursor.execute("SELECT SUM(amount) as total FROM gmail_recovery_requests WHERE telegram_id = ? AND status IN ('UNDER_REVIEW', 'COMPLETED', 'PAID')", (telegram_id,))
        gmail_row = cursor.fetchone()
        tot_gmail = float(gmail_row["total"]) if (gmail_row and gmail_row["total"]) else 0.0

        calculated_net_balance = max(0.0, (tot_dep + tot_spin) - (tot_sensi + tot_panel + tot_trn + tot_dk + tot_gmail))

        cursor.execute("SELECT balance FROM users WHERE telegram_id = ?", (telegram_id,))
        user_row = cursor.fetchone()
        current_bal = float(user_row["balance"]) if user_row else 0.0

        if calculated_net_balance > current_bal:
            with conn:
                conn.execute("""
                    UPDATE users
                    SET balance = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE telegram_id = ?
                """, (calculated_net_balance, telegram_id))
            logger.info(f"🛡️ [BALANCE HEALED] User {telegram_id}: Stored={current_bal:.2f} -> Healed={calculated_net_balance:.2f}")
            return calculated_net_balance

        return current_bal
    except Exception as e:
        logger.error(f"Error in sync_user_balance_integrity for {telegram_id}: {e}")
        return 0.0
    finally:
        conn.close()

def get_or_create_user(telegram_id: int, username: Optional[str] = None, first_name: Optional[str] = None) -> Dict[str, Any]:
    """Retrieves existing user or registers new user with server-side 0.0 balance."""
    sync_user_balance_integrity(telegram_id)
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, telegram_id, username, first_name, balance, created_at, updated_at FROM users WHERE telegram_id = ?", (telegram_id,))
        row = cursor.fetchone()
        
        if row:
            if row["username"] != username or row["first_name"] != first_name:
                with conn:
                    conn.execute("""
                        UPDATE users SET username = ?, first_name = ?, updated_at = CURRENT_TIMESTAMP WHERE telegram_id = ?
                    """, (username, first_name, telegram_id))
                cursor.execute("SELECT id, telegram_id, username, first_name, balance, created_at, updated_at FROM users WHERE telegram_id = ?", (telegram_id,))
                row = cursor.fetchone()
            return dict(row)
        else:
            with conn:
                conn.execute("""
                    INSERT INTO users (telegram_id, username, first_name, balance) VALUES (?, ?, ?, 0.0)
                """, (telegram_id, username, first_name))
            logger.info(f"Registered new user telegram_id={telegram_id}, username={username}")
            
            cursor.execute("SELECT id, telegram_id, username, first_name, balance, created_at, updated_at FROM users WHERE telegram_id = ?", (telegram_id,))
            return dict(cursor.fetchone())
    except Exception as e:
        logger.error(f"Error in get_or_create_user for {telegram_id}: {e}")
        raise
    finally:
        conn.close()

def get_user_balance(telegram_id: int) -> float:
    """Retrieves server-side stored wallet balance for user."""
    return sync_user_balance_integrity(telegram_id)

def create_deposit(telegram_user_id: int, amount: float, order_id: str, gateway: str = "TranzUPI") -> Dict[str, Any]:
    """Creates a new PENDING deposit record."""
    conn = get_connection()
    try:
        with conn:
            conn.execute("""
                INSERT INTO deposits (telegram_user_id, order_id, amount, gateway, status)
                VALUES (?, ?, ?, ?, 'PENDING')
            """, (telegram_user_id, order_id, amount, gateway))
        logger.info(f"Deposit created: Order ID={order_id}, User={telegram_user_id}, Amount=₹{amount:.2f}")
        
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM deposits WHERE order_id = ?", (order_id,))
        return dict(cursor.fetchone())
    except Exception as e:
        logger.error(f"Error creating deposit for user {telegram_user_id}: {e}")
        raise
    finally:
        conn.close()

def get_deposit_by_order_id(order_id: str) -> Optional[Dict[str, Any]]:
    """Fetches a deposit record by unique order_id."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM deposits WHERE order_id = ?", (order_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def get_user_deposit_history(telegram_user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """Fetches maximum `limit` recent deposits for user, sorted descending by creation time."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT order_id, amount, status, created_at, gateway
            FROM deposits
            WHERE telegram_user_id = ?
            ORDER BY id DESC
            LIMIT ?
        """, (telegram_user_id, limit))
        rows = cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def credit_wallet_transaction(
    order_id: str,
    transaction_id: str,
    payment_reference: str,
    verified_amount: float
) -> Tuple[bool, str]:
    """
    Executes transaction-safe wallet credit enforcing strict security rules:
    1. Order must exist
    2. Order status must be PENDING (not already SUCCESS, FAILED, or EXPIRED)
    3. Amount must match verified_amount
    4. Updates user balance AND marks deposit SUCCESS atomically.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT telegram_user_id, amount, status FROM deposits WHERE order_id = ?", (order_id,))
        deposit = cursor.fetchone()

        if not deposit:
            logger.warning(f"Credit failed: Order {order_id} does not exist.")
            return False, "Order does not exist"

        telegram_user_id = deposit["telegram_user_id"]
        expected_amount = float(deposit["amount"])
        current_status = deposit["status"]

        if current_status == "SUCCESS":
            logger.warning(f"Duplicate credit attempt blocked for Order {order_id}.")
            return False, "Order already processed as SUCCESS"

        if current_status != "PENDING":
            logger.warning(f"Credit failed: Order {order_id} status is {current_status}.")
            return False, f"Order status is {current_status}"

        if verified_amount is None or verified_amount <= 0.0:
            verified_amount = expected_amount

        if abs(expected_amount - verified_amount) > 0.01:
            logger.warning(f"Credit failed for Order {order_id}: Amount mismatch (Expected ₹{expected_amount}, Got ₹{verified_amount}).")
            return False, "Deposit amount mismatch"

        # ATOMIC TRANSACTION: Update user balance and deposit status in single transaction
        with conn:
            # 0. Ensure user record exists
            cursor.execute("""
                INSERT INTO users (telegram_id, username, first_name, balance)
                VALUES (?, 'User', 'User', 0.0)
                ON CONFLICT(telegram_id) DO NOTHING;
            """, (telegram_user_id,))

            # 1. Update deposit status first with status check
            cursor.execute("""
                UPDATE deposits
                SET status = 'SUCCESS',
                    transaction_id = ?,
                    payment_reference = ?,
                    verified_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE order_id = ? AND status = 'PENDING'
            """, (transaction_id, payment_reference, order_id))

            if cursor.rowcount == 0:
                # Race condition: Another process already updated this order
                return False, "Order state changed concurrently"

            # 2. Credit user wallet balance server-side
            cursor.execute("""
                UPDATE users
                SET balance = balance + ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE telegram_id = ?
            """, (expected_amount, telegram_user_id))

        sync_user_balance_integrity(telegram_user_id)
        logger.info(f"Wallet credit SUCCESS: Order={order_id}, User={telegram_user_id}, Credited=₹{expected_amount:.2f}")
        return True, "Wallet credited successfully"
    except Exception as e:
        logger.error(f"Error during credit_wallet_transaction for order {order_id}: {e}")
        return False, f"Database transaction error: {str(e)}"
    finally:
        conn.close()

def update_deposit_status(order_id: str, new_status: str) -> bool:
    """Updates deposit status (e.g. FAILED, EXPIRED)."""
    if new_status not in ["PENDING", "SUCCESS", "FAILED", "EXPIRED"]:
        return False
    conn = get_connection()
    try:
        with conn:
            conn.execute("""
                UPDATE deposits
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE order_id = ?
            """, (new_status, order_id))
        return True
    finally:
        conn.close()

# =====================================================================
# SENSI BUY DATABASE HELPERS & ATOMIC PAYMENTS
# =====================================================================

def get_sensi_price() -> float:
    """Retrieves current Sensi purchase price from settings (default 29.0)."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM sensi_settings WHERE key = 'sensi_price'")
        row = cursor.fetchone()
        return float(row["value"]) if row else 29.0
    except Exception as e:
        logger.error(f"Error fetching sensi price: {e}")
        return 29.0
    finally:
        conn.close()

def set_sensi_price(new_price: float) -> bool:
    """Updates Sensi purchase price in settings."""
    conn = get_connection()
    try:
        with conn:
            conn.execute("""
                INSERT INTO sensi_settings (key, value) VALUES ('sensi_price', ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value;
            """, (str(new_price),))
        logger.info(f"Updated Sensi price to ₹{new_price:.2f}")
        return True
    except Exception as e:
        logger.error(f"Error setting sensi price: {e}")
        return False
    finally:
        conn.close()

def get_sensi_brands() -> List[str]:
    """Returns unique list of active mobile brands sorted alphabetically."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT brand FROM sensi_catalog WHERE is_active = 1 ORDER BY brand ASC")
        return [row["brand"] for row in cursor.fetchall()]
    finally:
        conn.close()

def get_sensi_models_by_brand(brand: str) -> List[str]:
    """Returns active phone models for a given brand."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT model FROM sensi_catalog WHERE brand = ? AND is_active = 1 ORDER BY model ASC", (brand,))
        return [row["model"] for row in cursor.fetchall()]
    finally:
        conn.close()

def add_sensi_catalog_model(brand: str, model: str) -> bool:
    """Adds a new model to catalog."""
    conn = get_connection()
    try:
        with conn:
            conn.execute("""
                INSERT OR IGNORE INTO sensi_catalog (brand, model, is_active) VALUES (?, ?, 1)
            """, (brand.strip(), model.strip()))
        return True
    except Exception as e:
        logger.error(f"Error adding model {model} for brand {brand}: {e}")
        return False
    finally:
        conn.close()

def create_sensi_order(
    telegram_id: int,
    brand: str,
    model: str,
    ram: str,
    storage: str,
    payment_method: str,
    price: float,
    order_id: str
) -> Dict[str, Any]:
    """Creates a new pending Sensi order record."""
    conn = get_connection()
    try:
        with conn:
            conn.execute("""
                INSERT INTO sensi_orders (
                    order_id, telegram_id, brand, model, ram, storage, payment_method, price, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PENDING')
            """, (order_id, telegram_id, brand, model, ram, storage, payment_method, price))
        
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sensi_orders WHERE order_id = ?", (order_id,))
        return dict(cursor.fetchone())
    finally:
        conn.close()

def get_sensi_order_by_id(order_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a Sensi order record by order ID."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sensi_orders WHERE order_id = ?", (order_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def process_wallet_sensi_payment(order_id: str) -> Tuple[bool, str]:
    """
    Atomically deducts wallet balance for a Sensi order and marks order as SUCCESS.
    Prevents double-spending, race conditions, or insufficient balance.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sensi_orders WHERE order_id = ?", (order_id,))
        order = cursor.fetchone()

        if not order:
            return False, "Order not found"

        if order["status"] == "SUCCESS":
            return False, "Order already completed"

        telegram_id = order["telegram_id"]
        price = float(order["price"])

        # Check current balance
        cursor.execute("SELECT balance FROM users WHERE telegram_id = ?", (telegram_id,))
        user_row = cursor.fetchone()

        if not user_row:
            return False, "User not found"

        current_balance = float(user_row["balance"])

        if current_balance < price:
            return False, f"Insufficient wallet balance (Required: ₹{price:.2f}, Balance: ₹{current_balance:.2f})"

        with conn:
            # 1. Update order status to SUCCESS atomically
            cursor.execute("""
                UPDATE sensi_orders
                SET status = 'SUCCESS'
                WHERE order_id = ? AND status = 'PENDING'
            """, (order_id,))

            if cursor.rowcount == 0:
                return False, "Order state changed concurrently"

            # 2. Deduct user wallet balance
            cursor.execute("""
                UPDATE users
                SET balance = balance - ?, updated_at = CURRENT_TIMESTAMP
                WHERE telegram_id = ?
            """, (price, telegram_id))

        logger.info(f"Sensi Wallet Payment SUCCESS: Order={order_id}, User={telegram_id}, Deducted=₹{price:.2f}")
        return True, "Payment successful"
    except Exception as e:
        logger.error(f"Error in process_wallet_sensi_payment for {order_id}: {e}")
        return False, f"Transaction error: {str(e)}"
    finally:
        conn.close()

def mark_sensi_order_success(order_id: str) -> bool:
    """Marks Sensi order as SUCCESS (used by UPI gateway verifier)."""
    conn = get_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE sensi_orders
                SET status = 'SUCCESS'
                WHERE order_id = ? AND status = 'PENDING'
            """, (order_id,))
            return cursor.rowcount > 0
    finally:
        conn.close()

def save_sensi_delivery(
    telegram_id: int,
    order_id: str,
    brand: str,
    model: str,
    variant: str,
    general: int,
    red_dot: int,
    scope_2x: int,
    scope_4x: int,
    sniper: int,
    free_look: int,
    fire_button: int,
    dpi: int,
    pointer_speed: int
) -> Optional[Dict[str, Any]]:
    """Saves generated sensitivity profile delivery record."""
    conn = get_connection()
    try:
        with conn:
            conn.execute("""
                INSERT INTO sensi_deliveries (
                    telegram_id, order_id, brand, model, variant,
                    general, red_dot, scope_2x, scope_4x, sniper, free_look,
                    fire_button, dpi, pointer_speed
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                telegram_id, order_id, brand, model, variant,
                general, red_dot, scope_2x, scope_4x, sniper, free_look,
                fire_button, dpi, pointer_speed
            ))

        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sensi_deliveries WHERE order_id = ?", (order_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except Exception as e:
        logger.error(f"Error saving sensi delivery for {order_id}: {e}")
        return None
    finally:
        conn.close()

def get_user_sensi_history(telegram_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """Returns recent purchased sensitivity setups for user."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM sensi_deliveries
            WHERE telegram_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (telegram_id, limit))
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()

def get_sensi_sales_summary() -> Dict[str, Any]:
    """Returns Sensi sales metrics for Admin panel."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as total_orders, SUM(price) as total_revenue FROM sensi_orders WHERE status = 'SUCCESS'")
        row = cursor.fetchone()
        total_orders = row["total_orders"] if row else 0
        total_revenue = row["total_revenue"] if (row and row["total_revenue"]) else 0.0

        cursor.execute("SELECT brand, COUNT(*) as count FROM sensi_orders WHERE status = 'SUCCESS' GROUP BY brand ORDER BY count DESC LIMIT 5")
        top_brands = [dict(r) for r in cursor.fetchall()]

        return {
            "total_orders": total_orders,
            "total_revenue": total_revenue,
            "top_brands": top_brands
        }
    finally:
        conn.close()

# =====================================================================
# GMAIL RECOVERY DATABASE HELPERS & ATOMIC PAYMENTS
# =====================================================================

def get_gmail_fee() -> float:
    """Retrieves current Gmail Recovery service fee (default 299.0)."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM sensi_settings WHERE key = 'gmail_fee'")
        row = cursor.fetchone()
        return float(row["value"]) if row else 299.0
    except Exception as e:
        logger.error(f"Error fetching gmail fee: {e}")
        return 299.0
    finally:
        conn.close()

def set_gmail_fee(new_fee: float) -> bool:
    """Updates Gmail Recovery service fee in settings."""
    conn = get_connection()
    try:
        with conn:
            conn.execute("""
                INSERT INTO sensi_settings (key, value) VALUES ('gmail_fee', ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value;
            """, (str(new_fee),))
        logger.info(f"Updated Gmail fee to ₹{new_fee:.2f}")
        return True
    except Exception as e:
        logger.error(f"Error setting gmail fee: {e}")
        return False
    finally:
        conn.close()

def create_gmail_recovery_request(
    telegram_id: int,
    email: str,
    problem_description: str,
    order_id: str,
    payment_method: str,
    amount: float
) -> Dict[str, Any]:
    """Creates a new Gmail recovery request entry with status PENDING_PAYMENT."""
    conn = get_connection()
    try:
        with conn:
            conn.execute("""
                INSERT INTO gmail_recovery_requests (
                    order_id, telegram_id, email, problem_description, payment_method, amount, status
                ) VALUES (?, ?, ?, ?, ?, ?, 'PENDING_PAYMENT')
            """, (order_id, telegram_id, email, problem_description, payment_method, amount))
        
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM gmail_recovery_requests WHERE order_id = ?", (order_id,))
        return dict(cursor.fetchone())
    finally:
        conn.close()

def get_gmail_request_by_id(order_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a Gmail recovery request record by order ID."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM gmail_recovery_requests WHERE order_id = ?", (order_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def update_gmail_recovery_email(order_id: str, email: str) -> bool:
    """Updates target Gmail address for a paid recovery request."""
    conn = get_connection()
    try:
        with conn:
            conn.execute("""
                UPDATE gmail_recovery_requests
                SET email = ?, status = 'UNDER_REVIEW', updated_at = CURRENT_TIMESTAMP
                WHERE order_id = ?
            """, (email.strip(), order_id))
        return True
    except Exception as e:
        logger.error(f"Error updating email for order {order_id}: {e}")
        return False
    finally:
        conn.close()

def process_wallet_gmail_recovery_payment(order_id: str) -> Tuple[bool, str]:
    """
    Atomically deducts wallet balance for Gmail Recovery service and updates status to UNDER_REVIEW.
    Prevents double-spending, race conditions, or insufficient balance.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM gmail_recovery_requests WHERE order_id = ?", (order_id,))
        req = cursor.fetchone()

        if not req:
            return False, "Request not found"

        if req["status"] in ["PAID", "UNDER_REVIEW", "COMPLETED"]:
            return False, "Request already paid/processed"

        telegram_id = req["telegram_id"]
        fee = float(req["amount"])

        # Check current user balance
        cursor.execute("SELECT balance FROM users WHERE telegram_id = ?", (telegram_id,))
        user_row = cursor.fetchone()

        if not user_row:
            return False, "User not found"

        current_balance = float(user_row["balance"])

        if current_balance < fee:
            return False, f"Insufficient wallet balance (Required: ₹{fee:.2f}, Balance: ₹{current_balance:.2f})"

        with conn:
            # 1. Update request status to UNDER_REVIEW atomically
            cursor.execute("""
                UPDATE gmail_recovery_requests
                SET status = 'UNDER_REVIEW', payment_method = 'WALLET', updated_at = CURRENT_TIMESTAMP
                WHERE order_id = ? AND status = 'PENDING_PAYMENT'
            """, (order_id,))

            if cursor.rowcount == 0:
                return False, "Request state changed concurrently"

            # 2. Deduct user wallet balance
            cursor.execute("""
                UPDATE users
                SET balance = balance - ?, updated_at = CURRENT_TIMESTAMP
                WHERE telegram_id = ?
            """, (fee, telegram_id))

        logger.info(f"Gmail Recovery Wallet Payment SUCCESS: Order={order_id}, User={telegram_id}, Deducted=₹{fee:.2f}")
        return True, "Payment successful"
    except Exception as e:
        logger.error(f"Error in process_wallet_gmail_recovery_payment for {order_id}: {e}")
        return False, f"Transaction error: {str(e)}"
    finally:
        conn.close()

def mark_gmail_recovery_paid(order_id: str) -> bool:
    """Marks Gmail Recovery request as UNDER_REVIEW (used by UPI gateway verifier)."""
    conn = get_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE gmail_recovery_requests
                SET status = 'UNDER_REVIEW', updated_at = CURRENT_TIMESTAMP
                WHERE order_id = ? AND status = 'PENDING_PAYMENT'
            """, (order_id,))
            return cursor.rowcount > 0
    finally:
        conn.close()

def get_user_gmail_recovery_requests(telegram_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """Returns recent Gmail recovery requests for a user."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM gmail_recovery_requests
            WHERE telegram_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (telegram_id, limit))
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()

def get_all_gmail_recovery_requests(status_filter: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
    """Returns all Gmail recovery requests for Admin review."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        if status_filter:
            cursor.execute("""
                SELECT * FROM gmail_recovery_requests
                WHERE status = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (status_filter, limit))
        else:
            cursor.execute("""
                SELECT * FROM gmail_recovery_requests
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()

def update_gmail_recovery_status(order_id: str, new_status: str) -> bool:
    """Updates status of a Gmail recovery request (UNDER_REVIEW, COMPLETED, REJECTED, CANCELLED)."""
    allowed_statuses = ["PENDING_PAYMENT", "PAID", "UNDER_REVIEW", "COMPLETED", "REJECTED", "CANCELLED"]
    if new_status not in allowed_statuses:
        return False
    conn = get_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE gmail_recovery_requests
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE order_id = ?
            """, (new_status, order_id))
            return cursor.rowcount > 0
    finally:
        conn.close()

# =====================================================================
# PANEL BUY DATABASE HELPERS & ATOMIC PAYMENTS
# =====================================================================

def get_panel_catalog(page: int = 0, per_page: int = 6) -> Tuple[List[Dict[str, Any]], int]:
    """Retrieves paginated panel catalog list and total page count."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM panel_catalog WHERE is_active = 1")
        total_items = cursor.fetchone()["count"]
        total_pages = (total_items + per_page - 1) // per_page if total_items > 0 else 1

        page = max(0, min(page, total_pages - 1))
        offset = page * per_page

        cursor.execute("""
            SELECT * FROM panel_catalog
            WHERE is_active = 1
            ORDER BY id ASC
            LIMIT ? OFFSET ?
        """, (per_page, offset))

        items = [dict(row) for row in cursor.fetchall()]
        return items, total_pages
    finally:
        conn.close()

def get_panel_by_name(product_name: str) -> Optional[Dict[str, Any]]:
    """Retrieves a panel product by exact name."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM panel_catalog WHERE product_name = ?", (product_name,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def set_panel_price(product_name: str, price: float) -> bool:
    """Sets or updates the price for a panel product."""
    conn = get_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE panel_catalog
                SET price = ?, updated_at = CURRENT_TIMESTAMP
                WHERE product_name = ?
            """, (price, product_name))
            return cursor.rowcount > 0
    finally:
        conn.close()

def create_panel_order(
    telegram_id: int,
    product_name: str,
    price: float,
    order_id: str,
    payment_method: str = "PENDING"
) -> Dict[str, Any]:
    """Creates a new Panel Buy order record."""
    conn = get_connection()
    try:
        with conn:
            conn.execute("""
                INSERT INTO panel_orders (
                    order_id, telegram_id, product_name, price, payment_method, status
                ) VALUES (?, ?, ?, ?, ?, 'PENDING')
            """, (order_id, telegram_id, product_name, price, payment_method))

        cursor = conn.cursor()
        cursor.execute("SELECT * FROM panel_orders WHERE order_id = ?", (order_id,))
        return dict(cursor.fetchone())
    finally:
        conn.close()

def get_panel_order_by_id(order_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a Panel order by order ID."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM panel_orders WHERE order_id = ?", (order_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def process_wallet_panel_payment(order_id: str) -> Tuple[bool, str]:
    """
    Atomically deducts wallet balance for Panel purchase and marks status SUCCESS.
    Prevents double-spending, race conditions, or insufficient balance.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM panel_orders WHERE order_id = ?", (order_id,))
        order = cursor.fetchone()

        if not order:
            return False, "Order not found"

        if order["status"] == "SUCCESS":
            return False, "Order already completed"

        telegram_id = order["telegram_id"]
        price = float(order["price"])

        # Check current user balance
        cursor.execute("SELECT balance FROM users WHERE telegram_id = ?", (telegram_id,))
        user_row = cursor.fetchone()

        if not user_row:
            return False, "User not found"

        current_balance = float(user_row["balance"])

        if current_balance < price:
            return False, f"Insufficient wallet balance (Required: ₹{price:.2f}, Balance: ₹{current_balance:.2f})"

        with conn:
            # 1. Update order status to SUCCESS atomically
            cursor.execute("""
                UPDATE panel_orders
                SET status = 'SUCCESS', payment_method = 'WALLET', updated_at = CURRENT_TIMESTAMP
                WHERE order_id = ? AND status = 'PENDING'
            """, (order_id,))

            if cursor.rowcount == 0:
                return False, "Order state changed concurrently"

            # 2. Deduct user wallet balance
            cursor.execute("""
                UPDATE users
                SET balance = balance - ?, updated_at = CURRENT_TIMESTAMP
                WHERE telegram_id = ?
            """, (price, telegram_id))

        logger.info(f"Panel Wallet Payment SUCCESS: Order={order_id}, User={telegram_id}, Deducted=₹{price:.2f}")
        return True, "Payment successful"
    except Exception as e:
        logger.error(f"Error in process_wallet_panel_payment for {order_id}: {e}")
        return False, f"Transaction error: {str(e)}"
    finally:
        conn.close()

def mark_panel_order_success(order_id: str, key_code: Optional[str] = None) -> bool:
    """Marks Panel order as SUCCESS (used by UPI gateway verifier)."""
    conn = get_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE panel_orders
                SET status = 'SUCCESS', key_code = ?, updated_at = CURRENT_TIMESTAMP
                WHERE order_id = ? AND status = 'PENDING'
            """, (key_code, order_id))
            return cursor.rowcount > 0
    finally:
        conn.close()

def get_user_panel_orders(telegram_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """Returns recent completed Panel orders for a user."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM panel_orders
            WHERE telegram_id = ? AND status = 'SUCCESS'
            ORDER BY created_at DESC
            LIMIT ?
        """, (telegram_id, limit))
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()

def get_panel_sales_summary() -> Dict[str, Any]:
    """Returns Panel Buy sales metrics for Admin panel."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as total_orders, SUM(price) as total_revenue FROM panel_orders WHERE status = 'SUCCESS'")
        row = cursor.fetchone()
        total_orders = row["total_orders"] if row else 0
        total_revenue = row["total_revenue"] if (row and row["total_revenue"]) else 0.0

        cursor.execute("SELECT product_name, COUNT(*) as count FROM panel_orders WHERE status = 'SUCCESS' GROUP BY product_name ORDER BY count DESC LIMIT 5")
        top_products = [dict(r) for r in cursor.fetchall()]

        return {
            "total_orders": total_orders,
            "total_revenue": total_revenue,
            "top_products": top_products
        }
    finally:
        conn.close()

# =====================================================================
# PROFILE, DAILY SPIN, REFERRAL & ADMIN DASHBOARD HELPERS
# =====================================================================

def get_user_profile_stats(telegram_id: int) -> Dict[str, Any]:
    """Calculates complete profile statistics for a user."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        user_row = cursor.fetchone()

        if not user_row:
            return {
                "telegram_id": telegram_id,
                "username": None,
                "balance": 0.0,
                "total_deposited": 0.0,
                "total_purchases": 0.0,
                "total_orders": 0,
                "joined_date": "N/A"
            }

        balance = float(user_row["balance"])
        username = user_row["username"]
        created_at_raw = str(user_row["created_at"])
        try:
            dt = datetime.strptime(created_at_raw.split(".")[0], "%Y-%m-%d %H:%M:%S")
            joined_date = dt.strftime("%d %b %Y")
        except Exception:
            joined_date = created_at_raw.split(" ")[0] if " " in created_at_raw else created_at_raw

        # Total Deposited (Historical Sum of Completed Deposits)
        cursor.execute("SELECT SUM(amount) as sum_dep FROM deposits WHERE telegram_user_id = ? AND status = 'COMPLETED'", (telegram_id,))
        dep_row = cursor.fetchone()
        total_deposited = float(dep_row["sum_dep"]) if (dep_row and dep_row["sum_dep"]) else 0.0

        # Total Sensi Purchases
        cursor.execute("SELECT SUM(price) as sensi_sum, COUNT(*) as sensi_cnt FROM sensi_orders WHERE telegram_id = ? AND status = 'SUCCESS'", (telegram_id,))
        sensi_row = cursor.fetchone()
        sensi_sum = float(sensi_row["sensi_sum"]) if (sensi_row and sensi_row["sensi_sum"]) else 0.0
        sensi_cnt = int(sensi_row["sensi_cnt"]) if sensi_row else 0

        # Total Panel Purchases
        cursor.execute("SELECT SUM(price) as panel_sum, COUNT(*) as panel_cnt FROM panel_orders WHERE telegram_id = ? AND status = 'SUCCESS'", (telegram_id,))
        panel_row = cursor.fetchone()
        panel_sum = float(panel_row["panel_sum"]) if (panel_row and panel_row["panel_sum"]) else 0.0
        panel_cnt = int(panel_row["panel_cnt"]) if panel_row else 0

        # Total Gmail Requests
        cursor.execute("SELECT SUM(amount) as gmail_sum, COUNT(*) as gmail_cnt FROM gmail_recovery_requests WHERE telegram_id = ? AND status IN ('UNDER_REVIEW', 'COMPLETED', 'PAID')", (telegram_id,))
        gmail_row = cursor.fetchone()
        gmail_sum = float(gmail_row["gmail_sum"]) if (gmail_row and gmail_row["gmail_sum"]) else 0.0
        gmail_cnt = int(gmail_row["gmail_cnt"]) if gmail_row else 0

        total_purchases = sensi_sum + panel_sum + gmail_sum
        total_orders = sensi_cnt + panel_cnt + gmail_cnt

        return {
            "telegram_id": telegram_id,
            "username": username,
            "balance": balance,
            "total_deposited": total_deposited,
            "total_purchases": total_purchases,
            "total_orders": total_orders,
            "joined_date": joined_date
        }
    finally:
        conn.close()

def can_user_spin(telegram_id: int) -> Tuple[bool, int, int]:
    """Checks if 24 hours have elapsed since user's last spin. Returns (can_spin, hours_left, mins_left)."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT created_at FROM spin_history WHERE telegram_id = ? ORDER BY created_at DESC LIMIT 1", (telegram_id,))
        row = cursor.fetchone()

        if not row:
            return True, 0, 0

        last_spin_raw = str(row["created_at"]).split(".")[0]
        try:
            last_spin_dt = datetime.strptime(last_spin_raw, "%Y-%m-%d %H:%M:%S")
        except Exception:
            return True, 0, 0

        now = datetime.utcnow()
        elapsed = now - last_spin_dt
        seconds_in_24h = 86400

        if elapsed.total_seconds() >= seconds_in_24h:
            return True, 0, 0
        else:
            remaining_sec = int(seconds_in_24h - elapsed.total_seconds())
            hours_left = remaining_sec // 3600
            mins_left = (remaining_sec % 3600) // 60
            return False, hours_left, mins_left
    finally:
        conn.close()

def record_user_spin(telegram_id: int) -> Tuple[Optional[int], bool, float, Optional[str]]:
    """
    Performs server-side RNG spin for user if eligible.
    Probability of special number 20 is exactly 1/200 (0.005). Otherwise 1-9.
    Automatically credits reward amount to user's wallet balance immediately.
    Returns (result_number, is_special, reward_amount, error_message).
    """
    can_spin, h_left, m_left = can_user_spin(telegram_id)
    if not can_spin:
        return None, False, 0.0, f"⏳ Next spin available in {h_left}h {m_left}m."

    # Server-Side Secure RNG: 1/200 chance = 0.005
    if random.random() < 0.005:
        result = 20
        is_special = True
        reward_amount = 100.0
    else:
        result = random.randint(1, 9)
        is_special = False
        reward_amount = float(result)

    conn = get_connection()
    try:
        with conn:
            # 1. Record spin history
            conn.execute("""
                INSERT INTO spin_history (telegram_id, result, is_special)
                VALUES (?, ?, ?)
            """, (telegram_id, result, 1 if is_special else 0))

            # 2. Automatically credit reward to user's wallet balance immediately
            conn.execute("""
                UPDATE users
                SET balance = balance + ?, updated_at = CURRENT_TIMESTAMP
                WHERE telegram_id = ?
            """, (reward_amount, telegram_id))

        logger.info(f"Recorded Spin for User {telegram_id}: Result={result}, Special={is_special}, Wallet Credited=₹{reward_amount:.2f}")
        return result, is_special, reward_amount, None
    finally:
        conn.close()

def record_referral(referrer_id: int, referred_user_id: int) -> bool:
    """
    Records a new user referral if valid.
    Prevents self-referral and duplicate referrer assignments.
    """
    if referrer_id == referred_user_id:
        return False

    conn = get_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO referrals (referrer_id, referred_user_id)
                VALUES (?, ?)
            """, (referrer_id, referred_user_id))
            return cursor.rowcount > 0
    finally:
        conn.close()

def get_user_referral_count(referrer_id: int) -> int:
    """Returns the total number of successful referrals for a user."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM referrals WHERE referrer_id = ?", (referrer_id,))
        row = cursor.fetchone()
        return row["count"] if row else 0
    finally:
        conn.close()

def get_admin_dashboard_stats() -> Dict[str, Any]:
    """Aggregates system-wide analytics for Admin dashboard."""
    conn = get_connection()
    try:
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) as c FROM users")
        total_users = cursor.fetchone()["c"]

        cursor.execute("SELECT COUNT(*) as c, SUM(amount) as s FROM deposits WHERE status = 'COMPLETED'")
        dep_row = cursor.fetchone()
        total_deposits_count = dep_row["c"] if dep_row else 0
        total_deposits_sum = float(dep_row["s"]) if (dep_row and dep_row["s"]) else 0.0

        cursor.execute("SELECT COUNT(*) as c FROM sensi_orders WHERE status = 'SUCCESS'")
        sensi_count = cursor.fetchone()["c"]

        cursor.execute("SELECT COUNT(*) as c FROM panel_orders WHERE status = 'SUCCESS'")
        panel_count = cursor.fetchone()["c"]

        cursor.execute("SELECT COUNT(*) as c FROM gmail_recovery_requests")
        gmail_count = cursor.fetchone()["c"]

        cursor.execute("SELECT COUNT(*) as c FROM spin_history")
        spin_count = cursor.fetchone()["c"]

        cursor.execute("SELECT COUNT(*) as c FROM referrals")
        referral_count = cursor.fetchone()["c"]

        return {
            "total_users": total_users,
            "total_deposits_count": total_deposits_count,
            "total_deposits_sum": total_deposits_sum,
            "sensi_orders_count": sensi_count,
            "panel_orders_count": panel_count,
            "gmail_requests_count": gmail_count,
            "total_spins_count": spin_count,
            "total_referrals_count": referral_count
        }
    finally:
        conn.close()

# --- DK AI ASSISTANT HELPERS ---

def create_dk_ai_order(telegram_id: int, price: float = 99.0, order_id: str = None, payment_method: str = "PENDING") -> dict:
    """Creates a new DK AI Assistant order in PENDING status."""
    if not order_id:
        order_id = f"DKAI-{uuid.uuid4().hex[:8].upper()}"
    conn = get_connection()
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO dk_ai_orders (order_id, telegram_id, price, payment_method, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, 'PENDING', ?, ?)
    """, (order_id, telegram_id, price, payment_method, now_str, now_str))
    conn.commit()
    conn.close()
    return {"order_id": order_id, "telegram_id": telegram_id, "price": price, "status": "PENDING"}

def get_dk_ai_order_by_id(order_id: str) -> Optional[dict]:
    """Retrieves DK AI order by order_id."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM dk_ai_orders WHERE order_id = ?", (order_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def has_user_unlocked_dk_ai(telegram_id: int) -> bool:
    """Returns True if telegram_id has at least one SUCCESS order in dk_ai_orders."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM dk_ai_orders WHERE telegram_id = ? AND status = 'SUCCESS' LIMIT 1", (telegram_id,))
    row = cursor.fetchone()
    conn.close()
    return True if row else False

def mark_dk_ai_order_success(order_id: str) -> bool:
    """Marks DK AI order as SUCCESS (idempotent)."""
    conn = get_connection()
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("UPDATE dk_ai_orders SET status = 'SUCCESS', updated_at = ? WHERE order_id = ?", (now_str, order_id))
    conn.commit()
    conn.close()
    return True

def process_wallet_dk_ai_payment(order_id: str) -> Tuple[bool, str]:
    """Atomic wallet deduction for DK AI Assistant (₹99 exact price)."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM dk_ai_orders WHERE order_id = ?", (order_id,))
        order_row = cursor.fetchone()
        if not order_row:
            return False, "❌ DK AI Order not found."

        order = dict(order_row)
        if order["status"] == "SUCCESS":
            return True, "✅ Order already completed."

        telegram_id = order["telegram_id"]
        price = float(order["price"])

        # Check user balance
        cursor.execute("SELECT balance FROM users WHERE telegram_id = ?", (telegram_id,))
        u_row = cursor.fetchone()
        if not u_row:
            return False, "❌ User record not found."

        current_bal = float(u_row["balance"])
        if current_bal < price:
            return False, f"INSUFFICIENT_BALANCE|Required: ₹{price:.0f}\nYour Balance: ₹{current_bal:.2f}"

        with conn:
            # 1. Update order status to SUCCESS atomically
            cursor.execute("""
                UPDATE dk_ai_orders
                SET status = 'SUCCESS', payment_method = 'WALLET', updated_at = CURRENT_TIMESTAMP
                WHERE order_id = ? AND status = 'PENDING'
            """, (order_id,))

            if cursor.rowcount == 0:
                return False, "Order state changed concurrently"

            # 2. Deduct user wallet balance
            cursor.execute("""
                UPDATE users
                SET balance = balance - ?, updated_at = CURRENT_TIMESTAMP
                WHERE telegram_id = ?
            """, (price, telegram_id))

        logger.info(f"DK AI Wallet Payment SUCCESS: Order={order_id}, User={telegram_id}, Deducted=₹{price:.2f}")
        return True, "✅ Payment successful! DK AI Assistant Unlocked."

    except Exception as e:
        logger.error(f"Error processing DK AI wallet payment for {order_id}: {e}")
        return False, f"❌ Transaction error: {e}"
    finally:
        conn.close()

# --- PANEL VARIANTS & DURATION HELPERS ---

def get_panel_variants(product_name: str) -> List[Dict[str, Any]]:
    """Retrieves all duration variants for a panel product."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM panel_variants WHERE product_name = ? ORDER BY id ASC", (product_name,))
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()

def get_panel_variant_by_id(variant_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves a panel variant by ID."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM panel_variants WHERE id = ?", (variant_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def create_panel_variant_order(telegram_id: int, variant_id: int, price: float, order_id: Optional[str] = None, payment_method: str = "PENDING") -> Dict[str, Any]:
    """Creates a new panel variant order in PENDING status."""
    v = get_panel_variant_by_id(variant_id)
    if not v:
        raise ValueError("Invalid variant_id")
    if not order_id:
        order_id = f"PNL-VAR_{uuid.uuid4().hex[:8].upper()}"

    prod_desc = f"{v['product_name']} ({v['duration']})"
    conn = get_connection()
    try:
        with conn:
            conn.execute("""
                INSERT INTO panel_orders (order_id, telegram_id, product_name, price, payment_method, status)
                VALUES (?, ?, ?, ?, ?, 'PENDING')
            """, (order_id, telegram_id, prod_desc, price, payment_method))
        return {"order_id": order_id, "product_name": prod_desc, "price": price, "status": "PENDING"}
    finally:
        conn.close()

def process_wallet_panel_variant_payment(order_id: str) -> Tuple[bool, str]:
    """Atomic wallet deduction for Panel Variant purchase."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM panel_orders WHERE order_id = ?", (order_id,))
        order_row = cursor.fetchone()
        if not order_row:
            return False, "❌ Order not found."

        order = dict(order_row)
        if order["status"] == "SUCCESS":
            return True, "✅ Order already completed."

        telegram_id = order["telegram_id"]
        price = float(order["price"])

        cursor.execute("SELECT balance FROM users WHERE telegram_id = ?", (telegram_id,))
        u_row = cursor.fetchone()
        if not u_row:
            return False, "❌ User record not found."

        current_bal = float(u_row["balance"])
        if current_bal < price:
            return False, f"INSUFFICIENT_BALANCE|Required: ₹{price:.0f}\nYour Balance: ₹{current_bal:.2f}"

        key_code = f"KEY-{uuid.uuid4().hex[:12].upper()}"
        with conn:
            cursor.execute("""
                UPDATE panel_orders
                SET status = 'SUCCESS', payment_method = 'WALLET', key_code = ?, updated_at = CURRENT_TIMESTAMP
                WHERE order_id = ? AND status = 'PENDING'
            """, (key_code, order_id))

            if cursor.rowcount == 0:
                return False, "Order state changed concurrently"

            cursor.execute("""
                UPDATE users
                SET balance = balance - ?, updated_at = CURRENT_TIMESTAMP
                WHERE telegram_id = ?
            """, (price, telegram_id))

        logger.info(f"Panel Variant Wallet Payment SUCCESS: Order={order_id}, User={telegram_id}, Key={key_code}")
        return True, key_code
    except Exception as e:
        logger.error(f"Error processing panel variant wallet payment: {e}")
        return False, f"❌ Transaction error: {e}"
    finally:
        conn.close()

def admin_set_panel_variant_price(product_name: str, duration: str, price: float) -> bool:
    """Admin command helper to set variant price and mark in stock."""
    conn = get_connection()
    try:
        with conn:
            conn.execute("""
                INSERT INTO panel_variants (product_name, duration, price, is_in_stock)
                VALUES (?, ?, ?, 1)
                ON CONFLICT(product_name, duration) DO UPDATE SET price = excluded.price, is_in_stock = 1, updated_at = CURRENT_TIMESTAMP
            """, (product_name, duration, price))
        return True
    except Exception as e:
        logger.error(f"Error setting panel variant price: {e}")
        return False
    finally:
        conn.close()

def admin_toggle_panel_variant_stock(product_name: str, duration: str, is_in_stock: int) -> bool:
    """Admin command helper to toggle variant stock status (1=In Stock, 0=Out of Stock)."""
    conn = get_connection()
    try:
        with conn:
            conn.execute("""
                UPDATE panel_variants
                SET is_in_stock = ?, updated_at = CURRENT_TIMESTAMP
                WHERE product_name = ? AND duration = ?
            """, (is_in_stock, product_name, duration))
        return True
    except Exception as e:
        logger.error(f"Error toggling panel variant stock: {e}")
        return False
    finally:
        conn.close()

# --- TOURNAMENT ORDERS & ENTRY HELPERS ---

def create_tournament_order(telegram_id: int, price: float = 99.0, order_id: str = None, payment_method: str = "PENDING") -> dict:
    """Creates a new Tournament App entry order in PENDING status."""
    if not order_id:
        order_id = f"TRN-{uuid.uuid4().hex[:8].upper()}"
    conn = get_connection()
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO tournament_orders (order_id, telegram_id, price, payment_method, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, 'PENDING', ?, ?)
    """, (order_id, telegram_id, price, payment_method, now_str, now_str))
    conn.commit()
    conn.close()
    return {"order_id": order_id, "telegram_id": telegram_id, "price": price, "status": "PENDING"}

def get_tournament_order_by_id(order_id: str) -> Optional[dict]:
    """Retrieves Tournament order by order_id."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tournament_orders WHERE order_id = ?", (order_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def has_user_unlocked_tournament(telegram_id: int) -> bool:
    """Returns True if telegram_id has at least one SUCCESS order in tournament_orders."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM tournament_orders WHERE telegram_id = ? AND status = 'SUCCESS' LIMIT 1", (telegram_id,))
    row = cursor.fetchone()
    conn.close()
    return True if row else False

def mark_tournament_order_success(order_id: str) -> bool:
    """Marks Tournament order as SUCCESS (idempotent)."""
    conn = get_connection()
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("UPDATE tournament_orders SET status = 'SUCCESS', updated_at = ? WHERE order_id = ?", (now_str, order_id))
    conn.commit()
    conn.close()
    return True

def process_wallet_tournament_payment(order_id: str) -> Tuple[bool, str]:
    """Atomic wallet deduction for Tournament App Entry (₹99 exact price)."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tournament_orders WHERE order_id = ?", (order_id,))
        order_row = cursor.fetchone()
        if not order_row:
            return False, "❌ Tournament Order not found."

        order = dict(order_row)
        if order["status"] == "SUCCESS":
            return True, "✅ Order already completed."

        telegram_id = order["telegram_id"]
        price = float(order["price"])

        cursor.execute("SELECT balance FROM users WHERE telegram_id = ?", (telegram_id,))
        u_row = cursor.fetchone()
        if not u_row:
            return False, "❌ User record not found."

        current_bal = float(u_row["balance"])
        if current_bal < price:
            return False, f"INSUFFICIENT_BALANCE|Required: ₹{price:.0f}\nYour Balance: ₹{current_bal:.2f}"

        with conn:
            cursor.execute("""
                UPDATE tournament_orders
                SET status = 'SUCCESS', payment_method = 'WALLET', updated_at = CURRENT_TIMESTAMP
                WHERE order_id = ? AND status = 'PENDING'
            """, (order_id,))

            if cursor.rowcount == 0:
                return False, "Order state changed concurrently"

            cursor.execute("""
                UPDATE users
                SET balance = balance - ?, updated_at = CURRENT_TIMESTAMP
                WHERE telegram_id = ?
            """, (price, telegram_id))

        logger.info(f"Tournament Wallet Payment SUCCESS: Order={order_id}, User={telegram_id}, Deducted=₹{price:.2f}")
        return True, "✅ Payment successful! Tournament Entry Unlocked."

    except Exception as e:
        logger.error(f"Error processing tournament wallet payment for {order_id}: {e}")
        return False, f"❌ Transaction error: {e}"
    finally:
        conn.close()
