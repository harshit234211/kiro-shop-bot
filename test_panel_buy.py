import unittest
import secrets
import database as db

class TestPanelBuyFeature(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        db.init_db()

    def test_01_catalog_seeding_exact_16(self):
        items, total_pages = db.get_panel_catalog(page=0, per_page=50)
        self.assertEqual(len(items), 16)
        
        expected_names = {
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
        }
        actual_names = {item["product_name"] for item in items}
        self.assertEqual(actual_names, expected_names)
        print("✅ Test 1 Passed: Panel catalog seeded with exact 16 unique products.")

    def test_02_initial_prices_null(self):
        item = db.get_panel_by_name("BR MOD ROOT")
        self.assertIsNotNone(item)
        self.assertIsNone(item["price"])
        print("✅ Test 2 Passed: Initial product prices are NULL (Coming Soon / Not Set).")

    def test_03_admin_price_update(self):
        p_name = "BALA MOD MAIN ID"
        success = db.set_panel_price(p_name, 499.0)
        self.assertTrue(success)

        item = db.get_panel_by_name(p_name)
        self.assertEqual(item["price"], 499.0)
        print("✅ Test 3 Passed: Admin panel price setting validated.")

    def test_04_wallet_panel_payment_atomic(self):
        user_id = 666555444
        db.get_or_create_user(user_id, "paneluser", "PanelUser")

        # Reset balance to 0
        conn = db.get_connection()
        with conn:
            conn.execute("UPDATE users SET balance = 0.0 WHERE telegram_id = ?", (user_id,))
        conn.close()

        order_id = f"PNL-WAL_{secrets.token_hex(4)}"
        db.create_panel_order(
            telegram_id=user_id,
            product_name="BALA MOD MAIN ID",
            price=499.0,
            order_id=order_id,
            payment_method="WALLET"
        )

        # 1. Attempt payment with 0 balance (must fail)
        success, msg = db.process_wallet_panel_payment(order_id)
        self.assertFalse(success)
        self.assertIn("Insufficient", msg)

        # 2. Credit wallet balance ₹1000
        conn = db.get_connection()
        with conn:
            conn.execute("UPDATE users SET balance = 1000.0 WHERE telegram_id = ?", (user_id,))
        conn.close()

        # 3. Retry wallet payment (must succeed)
        success, msg = db.process_wallet_panel_payment(order_id)
        self.assertTrue(success)

        # 4. Verify balance is now ₹501.00 (1000 - 499)
        bal = db.get_user_balance(user_id)
        self.assertEqual(bal, 501.0)

        # 5. Verify order status is SUCCESS
        order = db.get_panel_order_by_id(order_id)
        self.assertEqual(order["status"], "SUCCESS")
        print("✅ Test 4 Passed: Atomic wallet deduction & Panel order completion.")

    def test_05_panel_sales_summary(self):
        summary = db.get_panel_sales_summary()
        self.assertGreater(summary["total_orders"], 0)
        self.assertGreater(summary["total_revenue"], 0.0)
        print("✅ Test 5 Passed: Panel Buy sales summary query validated.")

if __name__ == "__main__":
    unittest.main()
