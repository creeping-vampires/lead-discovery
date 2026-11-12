"""
Unit tests for Intent Classifier and Qualification Engine.
"""

import unittest
from workflow.processors.intent_classifier import IntentClassifier


class TestIntentClassifier(unittest.TestCase):
    def setUp(self):
        self.classifier = IntentClassifier()

    def test_strong_signal_classification(self):
        text = "I am ready to buy an off-plan 1BHK in JVC Dubai with Danube. Have a budget of AED 850k and planning to book next month."
        geo_info = {
            "state": "Karnataka",
            "city": "Bengaluru",
            "city_state": "Bengaluru, Karnataka",
            "confidence": "HIGH"
        }
        res = self.classifier.classify_lead(text, geo_info)
        self.assertEqual(res["qualification_status"], "Strong Signal")
        self.assertIn("AED 850k", res["ticket_size_budget"])
        self.assertIn("Jvc", res["preferred_areas"])

    def test_broker_rejection(self):
        text = "I am an agent for Emaar and Danube. DM me for details and brochures. Exclusive inventory available!"
        geo_info = {
            "state": "Karnataka",
            "city": "Bengaluru",
            "city_state": "Bengaluru, Karnataka",
            "confidence": "HIGH"
        }
        res = self.classifier.classify_lead(text, geo_info)
        self.assertEqual(res["qualification_status"], "Reject")
        self.assertIn("Disqualified: Identified as property seller/broker", res["qualification_reason"])

    def test_job_hunter_rejection(self):
        text = "Looking for job in Dubai on visit visa. CV attached. Software developer from Hyderabad."
        geo_info = {
            "state": "Telangana",
            "city": "Hyderabad",
            "city_state": "Hyderabad, Telangana",
            "confidence": "HIGH"
        }
        res = self.classifier.classify_lead(text, geo_info)
        self.assertEqual(res["qualification_status"], "Reject")

    def test_needs_validation_classification(self):
        text = "Comparing rental yields between Bangalore and Dubai. How does LRS and 20% TCS apply when remitting for real estate?"
        geo_info = {
            "state": "Karnataka",
            "city": "Bengaluru",
            "city_state": "Bengaluru, Karnataka",
            "confidence": "HIGH"
        }
        res = self.classifier.classify_lead(text, geo_info)
        self.assertEqual(res["qualification_status"], "Needs Validation")
        self.assertIn("Purchase budget / ticket size not specified", res["unverified_information"])

    def test_freshness_gate_under_6_months(self):
        from datetime import date, timedelta
        # 45 days old (well within 180 days / 6 months)
        recent_date = (date.today() - timedelta(days=45)).isoformat()
        text = "I am ready to buy an off-plan 1BHK in JVC Dubai with Danube. Have a budget of AED 850k and planning to book next month."
        geo_info = {
            "state": "Karnataka",
            "city": "Bengaluru",
            "city_state": "Bengaluru, Karnataka",
            "confidence": "HIGH"
        }
        res = self.classifier.classify_lead(text, geo_info, signal_date_str=recent_date)
        self.assertEqual(res["qualification_status"], "Strong Signal")
        self.assertTrue(res["is_fresh"])
        self.assertLessEqual(res["signal_age_days"], 180)

    def test_freshness_gate_exceeds_6_months_downgrades_to_needs_validation(self):
        from datetime import date, timedelta
        # 210 days old (> 180 days / 6 months)
        old_date = (date.today() - timedelta(days=210)).isoformat()
        text = "I am ready to buy an off-plan 1BHK in JVC Dubai with Danube. Have a budget of AED 850k and planning to book next month."
        geo_info = {
            "state": "Karnataka",
            "city": "Bengaluru",
            "city_state": "Bengaluru, Karnataka",
            "confidence": "HIGH"
        }
        res = self.classifier.classify_lead(text, geo_info, signal_date_str=old_date)
        # Must be downgraded from Strong Signal to Needs Validation due to strict 6-month rule
        self.assertEqual(res["qualification_status"], "Needs Validation")
        self.assertFalse(res["is_fresh"])
        self.assertGreater(res["signal_age_days"], 180)
        self.assertIn("Freshness limit exceeded", res["qualification_reason"])
        self.assertIn("freshness threshold", res["unverified_information"])

    def test_custom_configurable_freshness_constant(self):
        from datetime import date, timedelta
        # Instantiate with a 90-day (3-month) constant threshold
        custom_classifier = IntentClassifier(max_freshness_days=90)
        
        geo_info = {
            "state": "Karnataka",
            "city": "Bengaluru",
            "city_state": "Bengaluru, Karnataka",
            "confidence": "HIGH"
        }
        text = "I am ready to buy an off-plan 1BHK in JVC Dubai with Danube. Have a budget of AED 850k and planning to book next month."
        
        # 100 days old (fails 90-day threshold)
        res_fail = custom_classifier.classify_lead(
            text, geo_info, signal_date_str=(date.today() - timedelta(days=100)).isoformat()
        )
        self.assertEqual(res_fail["qualification_status"], "Needs Validation")
        self.assertFalse(res_fail["is_fresh"])

        # 60 days old (passes 90-day threshold)
        res_pass = custom_classifier.classify_lead(
            text, geo_info, signal_date_str=(date.today() - timedelta(days=60)).isoformat()
        )
        self.assertEqual(res_pass["qualification_status"], "Strong Signal")
        self.assertTrue(res_pass["is_fresh"])

    def test_score_0_to_100_scale_and_threshold_70(self):
        # Test full qualification scoring on 0-100 scale
        geo_info = {
            "state": "Karnataka",
            "city": "Bengaluru",
            "city_state": "Bengaluru, Karnataka",
            "confidence": "HIGH"
        }
        high_intent_text = (
            "I am ready to buy an off-plan 1BHK in JVC Dubai with Danube. "
            "Have a budget of AED 850k and planning to book next month. "
            "How does LRS remittance work?"
        )
        res_high = self.classifier.classify_lead(high_intent_text, geo_info)
        self.assertGreaterEqual(res_high["score"], 0)
        self.assertLessEqual(res_high["score"], 100)
        self.assertGreater(res_high["score"], 70)
        self.assertTrue(res_high["is_qualified"])

        # Test low intent lead scoring below 70
        low_intent_text = "What is the rental yield in Dubai property?"
        res_low = self.classifier.classify_lead(low_intent_text, geo_info)
        self.assertLessEqual(res_low["score"], 70)
        self.assertFalse(res_low["is_qualified"])

    def test_strong_signal_strictly_requires_current_resident(self):
        high_intent_text = "Ready to buy off-plan 1BHK in JVC with Danube. Budget AED 850k. Remitting under LRS."

        # Case 1: CURRENT_RESIDENT -> Strong Signal
        geo_resident = {
            "location_verification_status": "CURRENT_RESIDENT",
            "state": "Karnataka",
            "city": "Bengaluru",
            "city_state": "Bengaluru, Karnataka",
            "confidence": "HIGH",
            "location_evidence_text": "Living in HSR Layout Bangalore",
            "location_evidence_url": "https://reddit.com/r/bangalore/comments/1"
        }
        res_res = self.classifier.classify_lead(high_intent_text, geo_resident)
        self.assertEqual(res_res["qualification_status"], "Strong Signal")
        self.assertTrue(res_res["is_qualified"])

        # Case 2: LOCATION_UNVERIFIED -> Needs Validation (Never Strong Signal, Never Reject)
        geo_unverified = {
            "location_verification_status": "LOCATION_UNVERIFIED",
            "state": "Unverified",
            "city": "Unverified",
            "city_state": "Unverified",
            "confidence": "NONE",
            "location_evidence_text": "None - unverified",
            "location_evidence_url": "https://reddit.com/r/bangalore/comments/1"
        }
        res_unver = self.classifier.classify_lead(high_intent_text, geo_unverified)
        self.assertEqual(res_unver["qualification_status"], "Needs Validation")
        self.assertFalse(res_unver["is_qualified"])

        # Case 3: ORIGIN_ONLY -> Needs Validation (Never Strong Signal, Never Reject)
        geo_origin = {
            "location_verification_status": "ORIGIN_ONLY",
            "state": "Kerala",
            "city": "Thrissur",
            "city_state": "Thrissur, Kerala (Origin Only)",
            "confidence": "LOW",
            "location_evidence_text": "Thrissur native",
            "location_evidence_url": "https://reddit.com/r/kerala/comments/1"
        }
        res_orig = self.classifier.classify_lead(high_intent_text, geo_origin)
        self.assertEqual(res_orig["qualification_status"], "Needs Validation")
        self.assertFalse(res_orig["is_qualified"])

        # Case 4: OUTSIDE_TARGET -> Reject
        geo_outside = {
            "location_verification_status": "OUTSIDE_TARGET",
            "state": "Outside Target",
            "city": "Delhi",
            "city_state": "Delhi (Outside Target)",
            "confidence": "NONE",
            "location_evidence_text": "Living in South Delhi / Gurgaon",
            "location_evidence_url": "https://reddit.com/r/IndiaInvestments/comments/1"
        }
        res_out = self.classifier.classify_lead(high_intent_text, geo_outside)
        self.assertEqual(res_out["qualification_status"], "Reject")
        self.assertEqual(res_out["score"], 0)
        self.assertFalse(res_out["is_qualified"])


if __name__ == "__main__":
    unittest.main()

