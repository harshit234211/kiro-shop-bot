import os
import sys
import tempfile
import sqlite3
import datetime
from pathlib import Path

# Override DB_PATH for testing
test_db_dir = tempfile.mkdtemp()
test_db_path = os.path.join(test_db_dir, "test_kiro_shop.db")
os.environ["DB_PATH"] = test_db_path
os.environ["BOT_TOKEN"] = "1234567890:TEST_BOT_TOKEN_SECRET"
os.environ["TRANZUPI_SECRET"] = "TEST_SECRET_KEY_12345"

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import config
config.DB_PATH = test_db_path

import database as db
import gateway as gtw
from logger import logger, SensitiveDataFilter

def test_suite():
    print("=" * 65)
    print("🧪 RUNNING KIRO SHOP BOT V1 AUTOMATED TEST SUITE")
    print("=" * 65)

    # 1. Test DB Initialization
    print("\n[TEST 1] Testing Database Initialization & Schemas...")
    db.init_db()
    conn = db.get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('users', 'deposits');")
    tables = [row["name"] for row in cursor.fetchall()]
    assert "users" in tables, "Users table missing!"
    assert "deposits" in tables, "Deposits table missing!"
    conn.close()
    print("✅ Database tables created successfully.")

    # 2. Test User Registration & Server-side Balance
    print("\n[TEST 2] Testing User Registration & Server-Side Balance...")
    test_user_id = 987654321
    user = db.get_or_create_user(test_user_id, "testuser", "TestUser")
    assert user["telegram_id"] == test_user_id
    assert user["balance"] == 0.0
    
    balance = db.get_user_balance(test_user_id)
    assert balance == 0.0, f"Expected 0.0 balance, got {balance}"
    print(f"✅ User registered cleanly. Initial balance: ₹{balance:.2f}")

    # 3. Test Deposit Creation & Order ID Generation
    print("\n[TEST 3] Testing Deposit Creation & Order ID Generator...")
    order_id_1 = gtw.generate_order_id()
    assert order_id_1.startswith("KIR-"), f"Invalid order ID prefix: {order_id_1}"
    assert len(order_id_1) == 12, f"Order ID length should be 12 chars (KIR-XXXXXXXX), got {len(order_id_1)}"

    deposit_1 = db.create_deposit(
        telegram_user_id=test_user_id,
        amount=100.0,
        order_id=order_id_1,
        gateway="TranzUPI"
    )
    assert deposit_1["order_id"] == order_id_1
    assert deposit_1["amount"] == 100.0
    assert deposit_1["status"] == "PENDING"
    print(f"✅ Deposit created: Order {order_id_1}, Status: PENDING, Amount: ₹100.00")

    # 4. Test Atomic Wallet Credit & Balance Update
    print("\n[TEST 4] Testing Atomic Wallet Credit Flow...")
    success, msg = db.credit_wallet_transaction(
        order_id=order_id_1,
        transaction_id="TXN123456",
        payment_reference="UTR987654321",
        verified_amount=100.0
    )
    assert success is True, f"Credit transaction failed: {msg}"
    
    new_balance = db.get_user_balance(test_user_id)
    assert new_balance == 100.0, f"Expected balance ₹100.0, got ₹{new_balance}"

    fetched_dep = db.get_deposit_by_order_id(order_id_1)
    assert fetched_dep["status"] == "SUCCESS", f"Expected SUCCESS status, got {fetched_dep['status']}"
    assert fetched_dep["transaction_id"] == "TXN123456"
    assert fetched_dep["payment_reference"] == "UTR987654321"
    print(f"✅ Wallet credited successfully. Updated Balance: ₹{new_balance:.2f}")

    # 5. Test Security: Duplicate Payment Protection (Double Credit Prevention)
    print("\n[TEST 5] Testing Security: Replay / Duplicate Payment Protection...")
    dup_success, dup_msg = db.credit_wallet_transaction(
        order_id=order_id_1,
        transaction_id="TXN123456_DUP",
        payment_reference="UTR987654321_DUP",
        verified_amount=100.0
    )
    assert dup_success is False, "Duplicate credit allowed! CRITICAL SECURITY BUG!"
    assert "already processed" in dup_msg.lower() or "status is" in dup_msg.lower()

    unmodified_balance = db.get_user_balance(test_user_id)
    assert unmodified_balance == 100.0, f"Balance changed on duplicate credit! Expected ₹100.0, got ₹{unmodified_balance}"
    print("✅ Duplicate payment attempt blocked cleanly. Balance unchanged.")

    # 6. Test Security: Amount Mismatch Protection
    print("\n[TEST 6] Testing Security: Amount Mismatch Protection...")
    order_id_2 = gtw.generate_order_id()
    db.create_deposit(telegram_user_id=test_user_id, amount=500.0, order_id=order_id_2)

    mismatch_success, mismatch_msg = db.credit_wallet_transaction(
        order_id=order_id_2,
        transaction_id="TXN_MISMATCH",
        payment_reference="UTR_MISMATCH",
        verified_amount=10.0  # Paid ₹10 instead of ₹500
    )
    assert mismatch_success is False, "Amount mismatch credit allowed! CRITICAL SECURITY BUG!"
    assert "mismatch" in mismatch_msg.lower()
    print("✅ Amount mismatch credit attempt blocked cleanly.")

    # 7. Test Deposit History Limit (Max 10 records)
    print("\n[TEST 7] Testing Deposit History Query (Max 10 limit)...")
    # Insert 12 deposits
    for i in range(12):
        oid = gtw.generate_order_id()
        db.create_deposit(telegram_user_id=test_user_id, amount=(i + 1) * 10.0, order_id=oid)

    history = db.get_user_deposit_history(telegram_user_id=test_user_id, limit=10)
    assert len(history) == 10, f"Expected 10 history items, got {len(history)}"
    print(f"✅ Deposit history accurately limits to max {len(history)} recent records.")

    # 8. Test Empty Deposit History State
    print("\n[TEST 8] Testing Empty Deposit History for New User...")
    new_user_id = 111222333
    db.get_or_create_user(new_user_id, "emptyuser", "EmptyUser")
    empty_history = db.get_user_deposit_history(telegram_user_id=new_user_id, limit=10)
    assert len(empty_history) == 0, f"Expected 0 history items for new user, got {len(empty_history)}"
    print("✅ Empty deposit history returns empty list as expected.")

    # 9. Test Logger Redaction (No secret in log messages)
    print("\n[TEST 9] Testing Sensitive Logger Filter Redaction...")
    filter_inst = SensitiveDataFilter()
    class DummyRecord:
        def __init__(self, msg, args=()):
            self.msg = msg
            self.args = args
    
    rec = DummyRecord("Connecting with BOT_TOKEN=1234567890:TEST_BOT_TOKEN_SECRET and key TEST_SECRET_KEY_12345")
    filter_inst.filter(rec)
    assert "1234567890:TEST_BOT_TOKEN_SECRET" not in rec.msg, "BOT_TOKEN was not redacted!"
    assert "TEST_SECRET_KEY_12345" not in rec.msg, "TRANZUPI_SECRET was not redacted!"
    assert "[REDACTED]" in rec.msg
    print("✅ Sensitive credentials (BOT_TOKEN, API keys) redacted from logs.")

    print("\n" + "=" * 65)
    print("🎉 ALL TEST SUITE CHECKS PASSED SUCCESSFULLY!")
    print("=" * 65)

if __name__ == "__main__":
    test_suite()
