import unittest
import secrets
import database as db

class TestShopSpinTournamentFeatures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        db.init_db()

    def test_01_panel_variants_exact_prices(self):
        br_variants = db.get_panel_variants("BR MOD ROOT")
        self.assertEqual(len(br_variants), 4)

        price_map = {v["duration"]: v["price"] for v in br_variants}
        self.assertEqual(price_map["1 Day"], 70.0)
        self.assertEqual(price_map["7 Days"], 300.0)
        self.assertEqual(price_map["15 Days"], 500.0)
        self.assertEqual(price_map["30 Days"], 700.0)

        # Check IOS FLUORITE
        ios_variants = db.get_panel_variants("IOS FLUORITE")
        ios_price_map = {v["duration"]: v["price"] for v in ios_variants}
        self.assertEqual(ios_price_map["1 Day"], 400.0)
        self.assertEqual(ios_price_map["7 Days"], 1340.0)
        self.assertEqual(ios_price_map["30 Days"], 2200.0)
        print("✅ Test 1 Passed: Panel catalog duration-wise exact prices validated.")

    def test_02_out_of_stock_unpriced_products(self):
        drip_variants = db.get_panel_variants("DRIP CLIENT APKMOD")
        self.assertGreater(len(drip_variants), 0)
        for v in drip_variants:
            self.assertEqual(v["is_in_stock"], 0)
            self.assertIsNone(v["price"])
        print("✅ Test 2 Passed: Unpriced products properly configured as OUT OF STOCK.")

    def test_03_panel_variant_wallet_purchase(self):
        user_id = secrets.randbelow(800000000) + 100000
        db.get_or_create_user(user_id, "panelbuyer", "PanelBuyer")

        # Credit user ₹500
        dep = db.create_deposit(user_id, 500.0, f"KIR-DEP_{user_id}")
        db.credit_wallet_transaction(dep["order_id"], "TXN_TEST", "UTR_TEST", 500.0)

        v_list = db.get_panel_variants("BR MOD ROOT")
        v_7d = [v for v in v_list if v["duration"] == "7 Days"][0]

        order = db.create_panel_variant_order(user_id, v_7d["id"], v_7d["price"])
        success, key_code = db.process_wallet_panel_variant_payment(order["order_id"])

        self.assertTrue(success)
        self.assertTrue(key_code.startswith("KEY-"))

        # Verify updated wallet balance (₹500 - ₹300 = ₹200)
        user_rec = db.get_or_create_user(user_id)
        self.assertAlmostEqual(user_rec["balance"], 200.0, places=2)
        print("✅ Test 3 Passed: Atomic panel variant wallet purchase & License Key issuance.")

    def test_04_spin_auto_wallet_credit(self):
        user_id = secrets.randbelow(800000000) + 100000
        db.get_or_create_user(user_id, "spinwinner", "SpinWinner")

        init_bal = db.get_or_create_user(user_id)["balance"]
        res, is_spec, reward_amt, err = db.record_user_spin(user_id)

        self.assertIsNone(err)
        self.assertGreater(reward_amt, 0.0)

        new_bal = db.get_or_create_user(user_id)["balance"]
        self.assertAlmostEqual(new_bal, init_bal + reward_amt, places=2)
        print(f"✅ Test 4 Passed: Spin reward (₹{reward_amt}) automatically credited to wallet balance.")

    def test_05_tournament_99_lock_and_unlock(self):
        user_id = secrets.randbelow(800000000) + 100000
        db.get_or_create_user(user_id, "gamer", "Gamer")

        # 1. Unlocked initially False
        self.assertFalse(db.has_user_unlocked_tournament(user_id))

        # 2. Attempt wallet payment with ₹0 balance (must fail)
        trn_order = db.create_tournament_order(user_id, 99.0)
        success, msg = db.process_wallet_tournament_payment(trn_order["order_id"])
        self.assertFalse(success)
        self.assertFalse(db.has_user_unlocked_tournament(user_id))

        # 3. Credit user ₹100 & pay ₹99
        dep = db.create_deposit(user_id, 100.0, f"KIR-TRNDEP_{user_id}")
        db.credit_wallet_transaction(dep["order_id"], "TXN_TEST", "UTR_TEST", 100.0)

        success2, msg2 = db.process_wallet_tournament_payment(trn_order["order_id"])
        self.assertTrue(success2)
        self.assertTrue(db.has_user_unlocked_tournament(user_id))
        print("✅ Test 5 Passed: Tournament ₹99 payment lock & persistent access unlock verified.")

    def test_06_admin_price_and_stock_controls(self):
        self.assertTrue(db.admin_set_panel_variant_price("BALA MOD MAIN ID", "1 Day", 120.0))
        variants = db.get_panel_variants("BALA MOD MAIN ID")
        var_1d = [v for v in variants if v["duration"] == "1 Day"][0]
        self.assertEqual(var_1d["price"], 120.0)
        self.assertEqual(var_1d["is_in_stock"], 1)

        self.assertTrue(db.admin_toggle_panel_variant_stock("BALA MOD MAIN ID", "1 Day", 0))
        variants2 = db.get_panel_variants("BALA MOD MAIN ID")
        var_1d_off = [v for v in variants2 if v["duration"] == "1 Day"][0]
        self.assertEqual(var_1d_off["is_in_stock"], 0)
        print("✅ Test 6 Passed: Admin price setting and stock toggle controls validated.")

if __name__ == "__main__":
    unittest.main()
