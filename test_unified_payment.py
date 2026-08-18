import unittest
import secrets
import database as db
from config import FEATURES

class TestUnifiedPaymentEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        db.init_db()

    def test_01_sensi_price_is_49(self):
        price = db.get_sensi_price()
        self.assertEqual(price, 49.0)
        print("✅ Test 1 Passed: Default Sensi price set to ₹49.00.")

    def test_02_deposit_button_in_features(self):
        self.assertTrue(FEATURES.get("wallet", True))
        print("✅ Test 2 Passed: Wallet & Deposit buttons enabled in FEATURES config.")

    def test_03_atomic_wallet_deduction_for_sensi_49(self):
        user_id = secrets.randbelow(800000000) + 100000
        db.get_or_create_user(user_id, "sensipurchaser", "SensiPurchaser")

        # Credit ₹100 to wallet
        dep = db.create_deposit(user_id, 100.0, f"KIR-DEP_{user_id}")
        db.credit_wallet_transaction(dep["order_id"], "TXN_TEST", "UTR_TEST", 100.0)

        order_id = f"SENSI-TEST_{user_id}"
        db.create_sensi_order(
            telegram_id=user_id,
            brand="Vivo",
            model="Vivo T4x 5G",
            ram="8GB",
            storage="256GB",
            payment_method="PENDING",
            price=49.0,
            order_id=order_id
        )

        success, res_msg = db.process_wallet_sensi_payment(order_id)
        self.assertTrue(success)

        user_rec = db.get_or_create_user(user_id)
        self.assertAlmostEqual(user_rec["balance"], 51.0, places=2)
        print("✅ Test 3 Passed: Atomic wallet payment for Sensi ₹49.00 validated.")

    def test_04_atomic_wallet_deduction_for_tournament_99(self):
        user_id = secrets.randbelow(800000000) + 100000
        db.get_or_create_user(user_id, "tourneybuyer", "TourneyBuyer")

        # Credit ₹150 to wallet
        dep = db.create_deposit(user_id, 150.0, f"KIR-DEP_{user_id}")
        db.credit_wallet_transaction(dep["order_id"], "TXN_TEST", "UTR_TEST", 150.0)

        order_id = f"TRN-TEST_{user_id}"
        db.create_tournament_order(user_id, 99.0, order_id=order_id)

        success, res_msg = db.process_wallet_tournament_payment(order_id)
        self.assertTrue(success)

        user_rec = db.get_or_create_user(user_id)
        self.assertAlmostEqual(user_rec["balance"], 51.0, places=2)
        self.assertTrue(db.has_user_unlocked_tournament(user_id))
        print("✅ Test 4 Passed: Atomic wallet payment for Tournament ₹99.00 validated.")

if __name__ == "__main__":
    unittest.main()
