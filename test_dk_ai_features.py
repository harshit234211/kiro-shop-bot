import unittest
import secrets
import database as db
import config
from bot import get_main_keyboard

class TestDKAIFeatures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        db.init_db()

    def test_01_dk_ai_order_creation_and_insufficient_balance(self):
        user_id = secrets.randbelow(800000000) + 100000
        db.get_or_create_user(user_id, "pooruser", "PoorUser")

        order = db.create_dk_ai_order(telegram_id=user_id, price=99.0)
        self.assertEqual(order["status"], "PENDING")
        self.assertEqual(order["price"], 99.0)

        # Attempt wallet payment with ₹0 balance (must fail with INSUFFICIENT_BALANCE)
        success, msg = db.process_wallet_dk_ai_payment(order["order_id"])
        self.assertFalse(success)
        self.assertTrue(msg.startswith("INSUFFICIENT_BALANCE"))
        self.assertFalse(db.has_user_unlocked_dk_ai(user_id))
        print("✅ Test 1 Passed: Insufficient wallet balance blocks DK AI unlock cleanly.")

    def test_02_dk_ai_wallet_payment_success_and_unlock(self):
        user_id = secrets.randbelow(800000000) + 100000
        db.get_or_create_user(user_id, "richuser", "RichUser")

        # Credit user ₹150
        dep_id = f"KIR-TESTDK_{user_id}"
        dep = db.create_deposit(telegram_user_id=user_id, amount=150.0, order_id=dep_id)
        db.credit_wallet_transaction(dep["order_id"], "TXN_TEST", "UTR_TEST", 150.0)

        order = db.create_dk_ai_order(telegram_id=user_id, price=99.0)

        # Atomic wallet payment for ₹99
        success, msg = db.process_wallet_dk_ai_payment(order["order_id"])
        self.assertTrue(success)
        self.assertIn("Payment successful", msg)

        # Verify updated balance (₹150 - ₹99 = ₹51)
        user_rec = db.get_or_create_user(user_id)
        self.assertAlmostEqual(user_rec["balance"], 51.0, places=2)

        # Verify persistent access
        self.assertTrue(db.has_user_unlocked_dk_ai(user_id))
        print("✅ Test 2 Passed: Atomic ₹99 wallet payment unlocks DK AI & persists access.")

    def test_03_dynamic_features_config(self):
        # Verify initial main menu contains 12 buttons (6 rows x 2 buttons)
        kb = get_main_keyboard()
        button_texts = [btn.text for row in kb.keyboard for btn in row]
        self.assertIn("🤖 DK AI Assistant", button_texts)
        self.assertIn("🏆 Tournament App", button_texts)
        self.assertIn("📸 @_x_harshit_66", button_texts)
        self.assertIn("📸 @kiro_shop_66", button_texts)

        # Dynamically disable dk_ai feature
        config.FEATURES["dk_ai"] = False
        kb_disabled = get_main_keyboard()
        button_texts_disabled = [btn.text for row in kb_disabled.keyboard for btn in row]
        self.assertNotIn("🤖 DK AI Assistant", button_texts_disabled)

        # Re-enable dk_ai feature
        config.FEATURES["dk_ai"] = True
        print("✅ Test 3 Passed: Dynamic FEATURES config dictionary controls menu visibility.")

if __name__ == "__main__":
    unittest.main()
