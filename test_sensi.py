import unittest
import secrets
import database as db
import sensi_engine as sensi_eng

class TestSensiBuyFeature(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        db.init_db()

    def test_01_catalog_seeding(self):
        brands = db.get_sensi_brands()
        self.assertIn("Vivo", brands)
        self.assertIn("Samsung", brands)
        self.assertIn("Apple", brands)
        self.assertIn("Realme", brands)
        
        vivo_models = db.get_sensi_models_by_brand("Vivo")
        self.assertIn("Vivo T4x 5G", vivo_models)
        print("✅ Test 1 Passed: Mobile catalog seeded with brands and models.")

    def test_02_sensi_price_config(self):
        price = db.get_sensi_price()
        self.assertGreater(price, 0)
        
        db.set_sensi_price(49.0)
        self.assertEqual(db.get_sensi_price(), 49.0)

        db.set_sensi_price(29.0)
        self.assertEqual(db.get_sensi_price(), 29.0)
        print("✅ Test 2 Passed: Dynamic Sensi price configuration.")

    def test_03_sensitivity_generator_ranges(self):
        test_user = 999888777
        order_id = f"SENSI-TEST001_{secrets.token_hex(4)}"
        data, formatted_text = sensi_eng.generate_ff_sensitivity(
            telegram_id=test_user,
            order_id=order_id,
            brand="Vivo",
            model="Vivo T4x 5G",
            variant="8GB + 256GB"
        )

        self.assertTrue(1 <= data["general"] <= 200)
        self.assertTrue(1 <= data["red_dot"] <= 200)
        self.assertTrue(1 <= data["scope_2x"] <= 200)
        self.assertTrue(1 <= data["scope_4x"] <= 200)
        self.assertTrue(1 <= data["sniper"] <= 200)
        self.assertTrue(1 <= data["free_look"] <= 200)
        self.assertTrue(38 <= data["fire_button"] <= 60)
        self.assertTrue(420 <= data["dpi"] <= 650)
        self.assertTrue(5 <= data["pointer_speed"] <= 10)
        self.assertIn("Kiro Sensi Delivered", formatted_text)
        print("✅ Test 3 Passed: Random Free Fire sensitivity generator ranges validated.")

    def test_04_wallet_sensi_payment_atomic(self):
        user_id = 777666555
        db.get_or_create_user(user_id, "sensitest", "SensiUser")

        # Reset balance to 0 for initial test
        conn = db.get_connection()
        with conn:
            conn.execute("UPDATE users SET balance = 0.0 WHERE telegram_id = ?", (user_id,))
        conn.close()

        order_id = f"SENSI-TESTWAL_{secrets.token_hex(4)}"
        db.create_sensi_order(
            telegram_id=user_id,
            brand="Samsung",
            model="Samsung A15",
            ram="6GB",
            storage="128GB",
            payment_method="WALLET",
            price=29.0,
            order_id=order_id
        )

        # 1. Attempt payment with 0 balance (should fail)
        success, msg = db.process_wallet_sensi_payment(order_id)
        self.assertFalse(success)
        self.assertIn("Insufficient", msg)

        # 2. Credit wallet balance ₹100
        conn = db.get_connection()
        with conn:
            conn.execute("UPDATE users SET balance = 100.0 WHERE telegram_id = ?", (user_id,))
        conn.close()

        # 3. Retry wallet payment (should succeed)
        success, msg = db.process_wallet_sensi_payment(order_id)
        self.assertTrue(success)

        # 4. Verify balance is now ₹71.00
        bal = db.get_user_balance(user_id)
        self.assertEqual(bal, 71.0)
        print("✅ Test 4 Passed: Wallet Sensi payment atomic deduction & balance validation.")

    def test_05_sensi_history(self):
        user_id = 999888777
        history = db.get_user_sensi_history(user_id)
        self.assertGreater(len(history), 0)
        self.assertTrue(history[0]["order_id"].startswith("SENSI-TEST001"))
        print("✅ Test 5 Passed: Sensi history query validated.")

if __name__ == "__main__":
    unittest.main()
