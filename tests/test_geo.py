"""
Unit tests for Geographic entity matcher.
"""

import unittest
from workflow.processors.geo_matcher import GeoMatcher


class TestGeoMatcher(unittest.TestCase):
    def setUp(self):
        self.matcher = GeoMatcher()

    def test_karnataka_bangalore_match(self):
        text = "Living in Whitefield Bangalore for 8 years, working at IT tech park."
        res = self.matcher.extract_geo(text)
        self.assertEqual(res["state"], "Karnataka")
        self.assertIn("Whitefield", res["city_state"])
        self.assertEqual(res["confidence"], "HIGH")

    def test_telangana_hyderabad_match(self):
        text = "I am a resident of Gachibowli, Hyderabad looking at international property."
        res = self.matcher.extract_geo(text)
        self.assertEqual(res["state"], "Telangana")
        self.assertIn("Gachibowli", res["city_state"])
        self.assertEqual(res["confidence"], "HIGH")

    def test_kerala_kochi_match(self):
        text = "Malayali settled in Kochi (Ernakulam) looking for Dubai apartments."
        res = self.matcher.extract_geo(text)
        self.assertEqual(res["state"], "Kerala")
        self.assertEqual(res["confidence"], "HIGH")

    def test_tamil_nadu_chennai_match(self):
        text = "Based in OMR Chennai, evaluating rental yield options abroad."
        res = self.matcher.extract_geo(text)
        self.assertEqual(res["state"], "Tamil Nadu")
        self.assertEqual(res["confidence"], "HIGH")

    def test_andhra_pradesh_vizag_match(self):
        text = "Shipping business owner from Visakhapatnam (Vizag) looking to invest."
        res = self.matcher.extract_geo(text)
        self.assertEqual(res["state"], "Andhra Pradesh")
        self.assertEqual(res["confidence"], "HIGH")

    def test_unverified_location(self):
        text = "Looking for an apartment in Dubai Marina with 1% monthly plan."
        res = self.matcher.extract_geo(text)
        self.assertEqual(res["state"], "Unverified")
        self.assertEqual(res["confidence"], "NONE")


if __name__ == "__main__":
    unittest.main()

