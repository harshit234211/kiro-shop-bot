import unittest
import secrets
import database as db
import config

class TestProfileSpinReferralFeatures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        db.init_db()

    def test_01_profile_stats(self):
        user_id = 555444333
        db.get_or_create_user(user_id, "profileuser", "ProfileUser")

        stats = db.get_user_profile_stats(user_id)
        self.assertEqual(stats["telegram_id"], user_id)
        self.assertEqual(stats["username"], "profileuser")
        self.assertEqual(stats["total_deposited"], 0.0)
        self.assertEqual(stats["total_purchases"], 0.0)
        self.assertEqual(stats["total_orders"], 0)
        print("✅ Test 1 Passed: User profile statistics query validated.")

    def test_02_daily_spin_cooldown_and_logging(self):
        user_id = secrets.randbelow(800000000) + 100000
        db.get_or_create_user(user_id, "spinuser", "SpinUser")

        # First spin (must succeed)
        res, is_spec, reward_amt, err = db.record_user_spin(user_id)
        self.assertIsNone(err)
        self.assertIn(res, [1, 2, 3, 4, 5, 6, 7, 8, 9, 20])

        # Immediate second spin (must fail due to 24h cooldown)
        res2, is_spec2, reward_amt2, err2 = db.record_user_spin(user_id)
        self.assertIsNone(res2)
        self.assertIsNotNone(err2)
        self.assertIn("Next spin available", err2)
        print("✅ Test 2 Passed: Daily spin 24-hour cooldown enforcement and logging.")

    def test_03_referral_tracking_rules(self):
        referrer_id = secrets.randbelow(800000000) + 100000
        referred_user_id = secrets.randbelow(800000000) + 100000

        db.get_or_create_user(referrer_id, "ref_boss", "RefBoss")
        db.get_or_create_user(referred_user_id, "ref_newbie", "RefNewbie")

        # 1. Self-referral (must fail)
        self.assertFalse(db.record_referral(referrer_id, referrer_id))

        # 2. Valid referral (must succeed)
        self.assertTrue(db.record_referral(referrer_id, referred_user_id))

        # 3. Duplicate referral assignment for same referred user (must fail)
        self.assertFalse(db.record_referral(888777666, referred_user_id))

        # 4. Referral count query
        count = db.get_user_referral_count(referrer_id)
        self.assertEqual(count, 1)
        print("✅ Test 3 Passed: Referral tracking rules, self-referral block & duplicate prevention.")

    def test_04_admin_dashboard_stats(self):
        stats = db.get_admin_dashboard_stats()
        self.assertGreater(stats["total_users"], 0)
        self.assertIn("total_spins_count", stats)
        self.assertIn("total_referrals_count", stats)
        print("✅ Test 4 Passed: Admin dashboard system metrics aggregation.")

if __name__ == "__main__":
    unittest.main()
