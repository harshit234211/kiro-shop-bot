# Kiro Shop Telegram Bot (V1)

**Kiro Shop Bot** is a secure, clean, and mobile-friendly Telegram bot built with Python (`python-telegram-bot`), SQLite3, and `python-dotenv`. It provides server-side wallet balance storage, deposit creation, deposit history tracking, payment gateway abstractions (TranzUPI), and coming soon placeholders for future modules.

---

## 🚀 Quick Setup & Installation Guide

### 1. Prerequisites
- **Python 3.9+** installed on your system.
- Telegram Bot Token obtained from [@BotFather](https://t.me/BotFather).

### 2. Installation Commands

#### **Windows**
```cmd
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python bot.py
```

#### **Linux / macOS**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python bot.py
```

---

## ⚙️ Environment Variables Configuration (`.env`)

Create a `.env` file in the root directory (refer to `.env.example`):

```env
# Telegram Bot Token from @BotFather
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyZ_example

# Database Path
DB_PATH=data/kiro_shop.db

# Deposit Validation
MIN_DEPOSIT_AMOUNT=10.0

# TranzUPI Merchant Credentials
TRANZUPI_API_KEY=your_tranzupi_api_key
TRANZUPI_MERCHANT_ID=your_tranzupi_merchant_id
TRANZUPI_SECRET=your_tranzupi_secret
TRANZUPI_UPI_ID=your_upi_vpa@upi
```

---

## 🗄️ Database Structure

The bot uses SQLite (`data/kiro_shop.db`) with parameterized queries and atomic SQL transactions.

### 1. `users` Table
- `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
- `telegram_id` (INTEGER UNIQUE NOT NULL)
- `username` (TEXT)
- `first_name` (TEXT)
- `balance` (REAL NOT NULL DEFAULT 0.0) — **Stored strictly server-side**
- `created_at` (TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
- `updated_at` (TIMESTAMP DEFAULT CURRENT_TIMESTAMP)

### 2. `deposits` Table
- `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
- `telegram_user_id` (INTEGER NOT NULL)
- `order_id` (TEXT UNIQUE NOT NULL) — Format: `KIR-XXXXXXXX`
- `transaction_id` (TEXT)
- `amount` (REAL NOT NULL)
- `gateway` (TEXT DEFAULT 'TranzUPI')
- `status` (TEXT DEFAULT 'PENDING') — Statuses: `PENDING`, `SUCCESS`, `FAILED`, `EXPIRED`
- `payment_reference` (TEXT)
- `created_at` (TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
- `updated_at` (TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
- `verified_at` (TIMESTAMP)

---

## 💳 TranzUPI Gateway & Webhook Integration

1. **Order Generation**: Every deposit request generates a unique order ID (e.g. `KIR-85480Q88`).
2. **Intent Deep Linking**: Builds UPI intent URLs (`upi://pay?pa=...&am=...&tr=KIR-XXXXXXXX`) for direct mobile app payment handling.
3. **Webhook Verification Flow**:
   - The payment gateway sends a POST request to your webhook listener endpoint.
   - `gateway.process_tranzupi_webhook_payload()` validates the payload.
   - Atomic credit occurs via `database.credit_wallet_transaction()` only if:
     - Payment status is `SUCCESS`.
     - `order_id` exists in the database.
     - `order_id` status is currently `PENDING` (prevents replay/duplicate crediting).
     - Verified payment amount matches expected deposit amount.

---

## 🛡️ Security Features

- **No Secret Leakage**: Custom log filter redacts `BOT_TOKEN`, API keys, and secret credentials from all logs.
- **Parameterized SQL**: All database queries use binding parameters to prevent SQL injection.
- **Atomic Transactions**: Wallet updates and order status changes execute within a single SQL transaction context.
- **Server-Side Balance Integrity**: Client messages are never trusted for balance calculation.
- **Git Protection**: `.gitignore` explicitly prevents `.env` and SQLite database files (`*.db`) from being committed.

---

## 🧪 Running Automated Tests

Run the included automated test suite to verify database schemas, deposit validation, duplicate payment protection, and security filters:

```bash
python test_bot.py
```
