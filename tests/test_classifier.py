"""
Unit tests for Intent Classifier and Lead Qualification Engine.
Verifies mandatory evidence gates, 100-point weighted scoring model, and explainability.
"""

import unittest
from datetime import date, timedelta
from workflow.processors.intent_classifier import IntentClassifier


class TestIntentClassifier(unittest.TestCase):
    def setUp(self):
        self.classifier = IntentClassifier()

    def test_strong_signal_classification_passes_all_gates(self):
        recent_date = (date.today() - timedelta(days=20)).isoformat()
        text = (
            "I am ready to buy an off-plan 1BHK in JVC Dubai with Danube. "
            "Have a budget of AED 850k and planning to book next month. "
            "Remitting down payment under LRS."
        )
        geo_info = {
            "location_verification_status": "CURRENT_RESIDENT",
            "state": "Karnataka",
            "city": "Bengaluru",
            "city_state": "Bengaluru, Karnataka",
            "confidence": "HIGH",
            "location_evidence_text": "Living in HSR Layout Bangalore",
            "location_evidence_url": "https://www.reddit.com/r/bangalore/comments/12345"
        }
        res = self.classifier.classify_lead(
            text=text,
            geo_info=geo_info,
            signal_date_str=recent_date,
            source_link="https://www.reddit.com/r/bangalore/comments/12345",
            public_name_or_handle="u/buyer_blr",
            platform="Reddit (r/bangalore)"
        )
        self.assertEqual(res["qualification_status"], "Strong Signal")
        self.assertEqual(res["qualification_status_code"], "STRONG_SIGNAL")
        self.assertEqual(res["score"], 100)
        self.assertTrue(res["is_qualified"])

        # Check all 5 mandatory gates
        gates = res["mandatory_gates"]
        self.assertTrue(gates["gate_personal_intent"])
        self.assertTrue(gates["gate_verifiable_source"])
        self.assertTrue(gates["gate_current_resident"])
        self.assertTrue(gates["gate_freshness"])
        self.assertTrue(gates["gate_no_broker"])
        self.assertTrue(gates["all_mandatory_gates_pass"])

        # Check 6 scoring components
        breakdown = res["scoring_breakdown"]
        self.assertEqual(breakdown["explicit_personal_purchase_intent"], 30)
        self.assertEqual(breakdown["purchase_readiness"], 20)
        self.assertEqual(breakdown["budget_or_financing_requirements"], 15)
        self.assertEqual(breakdown["purchase_timeline"], 15)
        self.assertEqual(breakdown["specific_project_property_requirements"], 10)
        self.assertEqual(breakdown["freshness"], 10)

    def test_broker_rejection(self):
        text = "I am an agent for Emaar and Danube. DM me for details and brochures. Exclusive inventory available!"
        geo_info = {
            "location_verification_status": "CURRENT_RESIDENT",
            "state": "Karnataka",
            "city": "Bengaluru",
            "city_state": "Bengaluru, Karnataka",
            "confidence": "HIGH"
        }
        res = self.classifier.classify_lead(text, geo_info)
        self.assertEqual(res["qualification_status"], "Reject")
        self.assertEqual(res["qualification_status_code"], "REJECT")
        self.assertEqual(res["score"], 0)
        self.assertFalse(res["mandatory_gates"]["gate_no_broker"])
        self.assertIn("Identified as property seller/broker", res["qualification_reason"])

    def test_job_hunter_rejection(self):
        text = "Looking for job in Dubai on visit visa. CV attached. Software developer from Hyderabad."
        geo_info = {
            "location_verification_status": "CURRENT_RESIDENT",
            "state": "Telangana",
            "city": "Hyderabad",
            "city_state": "Hyderabad, Telangana",
            "confidence": "HIGH"
        }
        res = self.classifier.classify_lead(text, geo_info)
        self.assertEqual(res["qualification_status"], "Reject")
        self.assertEqual(res["score"], 0)

    def test_roi_research_alone_never_satisfies_personal_intent(self):
        """General ROI research, Golden Visa queries, or profession alone must score 0 for intent."""
        text = (
            "Software engineer living in Bengaluru. "
            "What is the average rental yield in Downtown Dubai compared to Bangalore? "
            "How does the UAE Golden Visa work through property purchase?"
        )
        geo_info = {
            "location_verification_status": "CURRENT_RESIDENT",
            "state": "Karnataka",
            "city": "Bengaluru",
            "city_state": "Bengaluru, Karnataka",
            "confidence": "HIGH",
            "location_evidence_text": "Living in Bengaluru"
        }
        res = self.classifier.classify_lead(
            text, geo_info,
            signal_date_str=date.today().isoformat(),
            source_link="https://reddit.com/r/bangalore/comments/test"
        )
        # Fails Gate 1: No explicit first-person purchase intent
        self.assertFalse(res["mandatory_gates"]["gate_personal_intent"])
        self.assertEqual(res["scoring_breakdown"]["explicit_personal_purchase_intent"], 0)
        # Cannot be Strong Signal
        self.assertNotEqual(res["qualification_status"], "Strong Signal")
        self.assertEqual(res["qualification_status"], "Needs Validation")
        self.assertIn("Explicit first-person purchase intent not stated", res["unverified_information"])

    def test_missing_purchase_readiness_or_timeline_downgrades_to_needs_validation(self):
        """A plausible buyer with intent and budget but lacking readiness/timeline scores 65 (< 75 threshold)."""
        recent_date = (date.today() - timedelta(days=10)).isoformat()
        text = (
            "Working in Whitefield tech park. Have a budget of 1.8 Cr (~800k AED). "
            "Looking to buy an off-plan 1BHK in JVC Dubai instead of another overpriced flat in Bangalore."
        )
        geo_info = {
            "location_verification_status": "CURRENT_RESIDENT",
            "state": "Karnataka",
            "city": "Bengaluru",
            "city_state": "Bengaluru, Karnataka",
            "confidence": "HIGH",
            "location_evidence_text": "Working in Whitefield tech park"
        }
        res = self.classifier.classify_lead(
            text, geo_info,
            signal_date_str=recent_date,
            source_link="https://reddit.com/r/bangalore/comments/test"
        )
        # Score = Intent (30) + Readiness (0) + Budget (15) + Timeline (0) + Project (10) + Freshness (10) = 65
        self.assertEqual(res["score"], 65)
        self.assertLess(res["score"], 75)
        self.assertEqual(res["qualification_status"], "Needs Validation")
        self.assertFalse(res["is_qualified"])

    def test_freshness_gate_under_and_over_180_days(self):
        geo_info = {
            "location_verification_status": "CURRENT_RESIDENT",
            "state": "Karnataka",
            "city": "Bengaluru",
            "city_state": "Bengaluru, Karnataka",
            "confidence": "HIGH",
            "location_evidence_text": "Living in Bengaluru"
        }
        text = "I am ready to buy an off-plan 1BHK in JVC with Danube. Budget AED 850k, booking next month, remitting down payment."
        source = "https://reddit.com/r/bangalore/comments/test"

        # 45 days old -> Passes gate & scores 100 -> Strong Signal
        recent_date = (date.today() - timedelta(days=45)).isoformat()
        res_fresh = self.classifier.classify_lead(text, geo_info, signal_date_str=recent_date, source_link=source)
        self.assertEqual(res_fresh["qualification_status"], "Strong Signal")
        self.assertTrue(res_fresh["mandatory_gates"]["gate_freshness"])
        self.assertEqual(res_fresh["scoring_breakdown"]["freshness"], 10)

        # 210 days old (> 180 days) -> Fails gate 4 & scores 0 freshness -> Needs Validation
        stale_date = (date.today() - timedelta(days=210)).isoformat()
        res_stale = self.classifier.classify_lead(text, geo_info, signal_date_str=stale_date, source_link=source)
        self.assertEqual(res_stale["qualification_status"], "Needs Validation")
        self.assertFalse(res_stale["mandatory_gates"]["gate_freshness"])
        self.assertEqual(res_stale["scoring_breakdown"]["freshness"], 0)
        self.assertIn("exceeds 180-day freshness limit", res_stale["unverified_information"])

    def test_strong_signal_strictly_requires_current_resident(self):
        """All 4 location statuses must be tested."""
        text = "I am ready to buy an off-plan 1BHK in JVC with Danube. Budget AED 850k, booking next month, remitting down payment."
        source = "https://reddit.com/r/bangalore/comments/test"
        recent = (date.today() - timedelta(days=20)).isoformat()

        # Case 1: CURRENT_RESIDENT -> Passes Gate 3 -> Strong Signal
        geo_resident = {
            "location_verification_status": "CURRENT_RESIDENT",
            "state": "Karnataka",
            "city": "Bengaluru",
            "city_state": "Bengaluru, Karnataka",
            "confidence": "HIGH",
            "location_evidence_text": "Living in HSR Layout Bangalore",
            "location_evidence_url": source
        }
        res_res = self.classifier.classify_lead(text, geo_resident, signal_date_str=recent, source_link=source)
        self.assertEqual(res_res["qualification_status"], "Strong Signal")
        self.assertTrue(res_res["mandatory_gates"]["gate_current_resident"])
        self.assertTrue(res_res["is_qualified"])

        # Case 2: LOCATION_UNVERIFIED -> Fails Gate 3 -> Needs Validation (Never Strong Signal, Never Reject)
        geo_unverified = {
            "location_verification_status": "LOCATION_UNVERIFIED",
            "state": "Unverified",
            "city": "Unverified",
            "city_state": "Unverified",
            "confidence": "NONE",
            "location_evidence_text": "None - unverified",
            "location_evidence_url": source
        }
        res_unver = self.classifier.classify_lead(text, geo_unverified, signal_date_str=recent, source_link=source)
        self.assertEqual(res_unver["qualification_status"], "Needs Validation")
        self.assertFalse(res_unver["mandatory_gates"]["gate_current_resident"])
        self.assertFalse(res_unver["is_qualified"])

        # Case 3: ORIGIN_ONLY -> Fails Gate 3 -> Needs Validation (Never Strong Signal, Never Reject)
        geo_origin = {
            "location_verification_status": "ORIGIN_ONLY",
            "state": "Kerala",
            "city": "Thrissur",
            "city_state": "Thrissur, Kerala (Origin Only)",
            "confidence": "LOW",
            "location_evidence_text": "Thrissur native",
            "location_evidence_url": source
        }
        res_orig = self.classifier.classify_lead(text, geo_origin, signal_date_str=recent, source_link=source)
        self.assertEqual(res_orig["qualification_status"], "Needs Validation")
        self.assertFalse(res_orig["mandatory_gates"]["gate_current_resident"])
        self.assertFalse(res_orig["is_qualified"])

        # Case 4: OUTSIDE_TARGET -> Reject
        geo_outside = {
            "location_verification_status": "OUTSIDE_TARGET",
            "state": "Outside Target",
            "city": "Delhi",
            "city_state": "Delhi (Outside Target)",
            "confidence": "NONE",
            "location_evidence_text": "Living in South Delhi / Gurgaon",
            "location_evidence_url": source
        }
        res_out = self.classifier.classify_lead(text, geo_outside, signal_date_str=recent, source_link=source)
        self.assertEqual(res_out["qualification_status"], "Reject")
        self.assertEqual(res_out["score"], 0)
        self.assertFalse(res_out["is_qualified"])

    def test_verifiable_source_gate(self):
        """Deleted Reddit post or missing source fails Gate 2 and is rejected."""
        text = "I am ready to buy an off-plan 1BHK in JVC with Danube. Budget AED 850k, booking next month."
        geo_info = {
            "location_verification_status": "CURRENT_RESIDENT",
            "state": "Karnataka",
            "city": "Bengaluru",
            "city_state": "Bengaluru, Karnataka",
            "confidence": "HIGH",
            "location_evidence_text": "Living in Bengaluru"
        }
        # Record with deleted post content
        res = self.classifier.classify_lead(
            text="[deleted by user]",
            geo_info=geo_info,
            signal_date_str=date.today().isoformat(),
            source_link="https://reddit.com/r/bangalore/comments/del1",
            public_name_or_handle="[deleted]"
        )
        self.assertEqual(res["qualification_status"], "Reject")
        self.assertEqual(res["score"], 0)
        self.assertFalse(res["mandatory_gates"]["gate_verifiable_source"])

    def test_explainable_evidence_snippets_and_reason_codes(self):
        recent_date = (date.today() - timedelta(days=15)).isoformat()
        text = (
            "Planning to remit funds under LRS to book a 2BHK in Business Bay Dubai with Emaar. "
            "Budget is 2.2M AED. Looking to complete the transaction by Q3 this year. "
            "Recommend a tax advisor for Form 15CA/CB."
        )
        geo_info = {
            "location_verification_status": "CURRENT_RESIDENT",
            "state": "Karnataka",
            "city": "Bengaluru",
            "city_state": "Bengaluru, Karnataka",
            "confidence": "HIGH",
            "location_evidence_text": "Living in HSR Layout Bangalore",
            "location_evidence_url": "https://reddit.com/r/bangalore/comments/test"
        }
        res = self.classifier.classify_lead(
            text, geo_info,
            signal_date_str=recent_date,
            source_link="https://reddit.com/r/bangalore/comments/test"
        )
        # Check evidence snippets
        ev = res["component_evidence"]
        self.assertIn("Planning to", ev["intent_evidence"])
        self.assertIn("remit funds under LRS", ev["readiness_evidence"])
        self.assertIn("2.2M AED", ev["budget_evidence"])
        self.assertIn("Q3", ev["timeline_evidence"])
        self.assertIn("Business Bay", ev["project_evidence"])
        self.assertIn("15 days old", ev["freshness_evidence"])

        # Check reason codes
        rc = res["component_reason_codes"]
        self.assertEqual(rc["intent_reason_code"], "EXPLICIT_PERSONAL_INTENT")
        self.assertEqual(rc["readiness_reason_code"], "PURCHASE_READINESS_CONFIRMED")
        self.assertEqual(rc["budget_reason_code"], "BUDGET_OR_FINANCING_SPECIFIED")
        self.assertEqual(rc["timeline_reason_code"], "TIMELINE_SPECIFIED")
        self.assertEqual(rc["project_reason_code"], "PROJECT_REQUIREMENTS_SPECIFIED")
        self.assertEqual(rc["freshness_reason_code"], "SIGNAL_FRESH_180D")


if __name__ == "__main__":
    unittest.main()
