import unittest
import secrets
import database as db
import config

class TestGmailRecoveryFeature(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        db.init_db()

    def test_01_gmail_fee_config(self):
        fee = db.get_gmail_fee()
        self.assertEqual(fee, 299.0)
        print("✅ Test 1 Passed: Default Gmail recovery service fee (₹299.0) validated.")

    def test_02_request_creation_pending(self):
        user_id = 888777666
        order_id = f"KR-TEST_{secrets.token_hex(4)}"
        req = db.create_gmail_recovery_request(
            telegram_id=user_id,
            email="victim@gmail.com",
            problem_description="I lost access to my recovery phone.",
            order_id=order_id,
            payment_method="PENDING",
            amount=299.0
        )
        self.assertEqual(req["status"], "PENDING_PAYMENT")
        self.assertEqual(req["email"], "victim@gmail.com")
        print("✅ Test 2 Passed: Gmail recovery request creation in PENDING_PAYMENT status.")

    def test_03_wallet_payment_atomic(self):
        user_id = 888777666
        db.get_or_create_user(user_id, "gmailuser", "GmailUser")

        # Reset balance to 0
        conn = db.get_connection()
        with conn:
            conn.execute("UPDATE users SET balance = 0.0 WHERE telegram_id = ?", (user_id,))
        conn.close()

        order_id = f"KR-WAL_{secrets.token_hex(4)}"
        db.create_gmail_recovery_request(
            telegram_id=user_id,
            email="user2@gmail.com",
            problem_description="Forgot password and 2FA lost.",
            order_id=order_id,
            payment_method="WALLET",
            amount=299.0
        )

        # 1. Payment with 0 balance (must fail)
        success, msg = db.process_wallet_gmail_recovery_payment(order_id)
        self.assertFalse(success)
        self.assertIn("Insufficient", msg)

        # 2. Add ₹500 balance
        conn = db.get_connection()
        with conn:
            conn.execute("UPDATE users SET balance = 500.0 WHERE telegram_id = ?", (user_id,))
        conn.close()

        # 3. Retry wallet payment (must succeed)
        success, msg = db.process_wallet_gmail_recovery_payment(order_id)
        self.assertTrue(success)

        # 4. Verify balance is now ₹201.00 (500 - 299)
        bal = db.get_user_balance(user_id)
        self.assertEqual(bal, 201.0)

        # 5. Verify status updated to UNDER_REVIEW
        req = db.get_gmail_request_by_id(order_id)
        self.assertEqual(req["status"], "UNDER_REVIEW")
        print("✅ Test 3 Passed: Atomic wallet deduction & UNDER_REVIEW status transition.")

    def test_04_admin_authorization(self):
        admin_id = 8568912134
        non_admin_id = 111111111
        self.assertTrue(config.is_admin(admin_id))
        self.assertFalse(config.is_admin(non_admin_id))
        print("✅ Test 4 Passed: ADMIN_USER_IDS security authorization checks.")

    def test_05_admin_status_update(self):
        order_id = f"KR-STATUS_{secrets.token_hex(4)}"
        db.create_gmail_recovery_request(
            telegram_id=888777666,
            email="user3@gmail.com",
            problem_description="Hacked account",
            order_id=order_id,
            payment_method="UPI",
            amount=299.0
        )
        db.update_gmail_recovery_status(order_id, "UNDER_REVIEW")
        req = db.get_gmail_request_by_id(order_id)
        self.assertEqual(req["status"], "UNDER_REVIEW")

        db.update_gmail_recovery_status(order_id, "COMPLETED")
        req = db.get_gmail_request_by_id(order_id)
        self.assertEqual(req["status"], "COMPLETED")
        print("✅ Test 5 Passed: Admin Gmail recovery status transitions.")

if __name__ == "__main__":
    unittest.main()
