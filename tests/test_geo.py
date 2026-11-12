"""
Unit tests for Strict Geographic Evidence Verification Engine.
Tests all four location statuses:
- CURRENT_RESIDENT
- ORIGIN_ONLY
- LOCATION_UNVERIFIED
- OUTSIDE_TARGET
"""

import unittest
from workflow.processors.geo_matcher import GeoMatcher


class TestGeoMatcher(unittest.TestCase):
    def setUp(self):
        self.matcher = GeoMatcher()

    def test_current_resident_karnataka(self):
        text = "Living in HSR Layout Bangalore for 8 years, working at IT tech park."
        res = self.matcher.extract_geo(text, source_link="https://reddit.com/r/bangalore/comments/1")
        self.assertEqual(res["location_verification_status"], "CURRENT_RESIDENT")
        self.assertEqual(res["state"], "Karnataka")
        self.assertEqual(res["city"], "Bengaluru")
        self.assertEqual(res["confidence"], "HIGH")
        self.assertIn("Living in HSR Layout Bangalore", res["location_evidence_text"])
        self.assertEqual(res["location_evidence_url"], "https://reddit.com/r/bangalore/comments/1")

    def test_current_resident_telangana(self):
        text = "Based in Jubilee Hills, Hyderabad looking at international property."
        res = self.matcher.extract_geo(text)
        self.assertEqual(res["location_verification_status"], "CURRENT_RESIDENT")
        self.assertEqual(res["state"], "Telangana")
        self.assertEqual(res["city"], "Hyderabad")
        self.assertEqual(res["confidence"], "HIGH")

    def test_current_resident_kerala(self):
        text = "Malayali settled in Kochi (Ernakulam) looking for Dubai apartments."
        res = self.matcher.extract_geo(text)
        self.assertEqual(res["location_verification_status"], "CURRENT_RESIDENT")
        self.assertEqual(res["state"], "Kerala")
        self.assertEqual(res["city"], "Kochi")
        self.assertEqual(res["confidence"], "HIGH")

    def test_current_resident_tamil_nadu(self):
        text = "Working in OMR IT corridor, Chennai. Deciding between local flats vs Dubai Marina."
        res = self.matcher.extract_geo(text)
        self.assertEqual(res["location_verification_status"], "CURRENT_RESIDENT")
        self.assertEqual(res["state"], "Tamil Nadu")
        self.assertEqual(res["city"], "Chennai")
        self.assertEqual(res["confidence"], "HIGH")

    def test_current_resident_andhra_pradesh(self):
        text = "Tech consultant living in Tirupati Andhra Pradesh. Planning to buy 2BHK in JVC."
        res = self.matcher.extract_geo(text)
        self.assertEqual(res["location_verification_status"], "CURRENT_RESIDENT")
        self.assertEqual(res["state"], "Andhra Pradesh")
        self.assertEqual(res["city"], "Tirupati")
        self.assertEqual(res["confidence"], "HIGH")

    def test_origin_only_distinction(self):
        # Thrissur native without residence statement
        text1 = "Thrissur native, currently managing family enterprise. Looking at Dubai South."
        res1 = self.matcher.extract_geo(text1)
        self.assertEqual(res1["location_verification_status"], "ORIGIN_ONLY")
        self.assertEqual(res1["confidence"], "LOW")
        self.assertEqual(res1["state"], "Kerala")

        # Kannur origin with NRE funds (living abroad)
        text2 = "From Kannur Kerala. Holding funds in NRE fixed deposits in Federal Bank."
        res2 = self.matcher.extract_geo(text2)
        self.assertEqual(res2["location_verification_status"], "ORIGIN_ONLY")
        self.assertEqual(res2["state"], "Kerala")

        # Vijayawada origin
        text3 = "From Vijayawada AP. Real estate in Amaravati is too speculative."
        res3 = self.matcher.extract_geo(text3)
        self.assertEqual(res3["location_verification_status"], "ORIGIN_ONLY")
        self.assertEqual(res3["state"], "Andhra Pradesh")

    def test_location_unverified_no_subreddit_inference(self):
        # Rule 2: Do NOT infer residence from subreddit membership
        text = "Looking for an apartment in Dubai Marina with 1% monthly plan. What are the handover risks?"
        res = self.matcher.extract_geo(text, platform_context="Reddit (r/bangalore)")
        self.assertEqual(res["location_verification_status"], "LOCATION_UNVERIFIED")
        self.assertEqual(res["state"], "Unverified")
        self.assertEqual(res["city"], "Unverified")
        self.assertEqual(res["city_state"], "Unverified")
        self.assertEqual(res["confidence"], "NONE")

    def test_location_unverified_event_attendance_and_language(self):
        # Attending an expo does not prove residence
        text1 = "Went to the Dubai Property Roadshow at The Lalit Bengaluru today. Danube sales reps were pitching 1% plans."
        res1 = self.matcher.extract_geo(text1, platform_context="r/bangalore events")
        self.assertEqual(res1["location_verification_status"], "LOCATION_UNVERIFIED")

        # Viewing location does not prove residence
        text2 = "Watching from Bengaluru, Karnataka. Great video on Golden Visa!"
        res2 = self.matcher.extract_geo(text2)
        self.assertEqual(res2["location_verification_status"], "LOCATION_UNVERIFIED")

    def test_outside_target_detection(self):
        text1 = "Living in South Delhi / Gurgaon. Looking to buy 2BHK in Downtown Dubai. Budget 3M AED."
        res1 = self.matcher.extract_geo(text1)
        self.assertEqual(res1["location_verification_status"], "OUTSIDE_TARGET")
        self.assertEqual(res1["state"], "Outside Target")
        self.assertEqual(res1["confidence"], "NONE")

        text2 = "Resident of Mumbai looking for off-plan luxury villa in Dubai Hills."
        res2 = self.matcher.extract_geo(text2)
        self.assertEqual(res2["location_verification_status"], "OUTSIDE_TARGET")

    def test_no_guessing_missing_fields(self):
        text = "What is the net rental yield in Business Bay Dubai after property management fees?"
        res = self.matcher.extract_geo(text)
        self.assertEqual(res["location_verification_status"], "LOCATION_UNVERIFIED")
        self.assertEqual(res["state"], "Unverified")
        self.assertEqual(res["city"], "Unverified")
        self.assertEqual(res["city_state"], "Unverified")
        self.assertEqual(res["location_evidence_text"], "None - unverified")


if __name__ == "__main__":
    unittest.main()
