"""
Unit tests for SourceVerifier and Reddit post/comment deletion filtering.
"""

import unittest
from workflow.processors.source_verifier import SourceVerifier
from workflow.processors.intent_classifier import IntentClassifier


class TestSourceVerifier(unittest.TestCase):
    def setUp(self):
        self.verifier = SourceVerifier(check_live=False)
        self.classifier = IntentClassifier(verify_sources=True, source_verifier=self.verifier)

    def test_valid_reddit_post_passes(self):
        record = {
            "public_name_or_handle": "u/bengaluru_techie",
            "platform": "Reddit (r/bangalore)",
            "source_link": "https://www.reddit.com/r/bangalore/comments/18m9xp1/dubai_real_estate_vs_bangalore/",
            "raw_text": "Working in Whitefield. Looking to buy an off-plan 1BHK in JVC Dubai. Budget AED 850k.",
            "platform_context": "r/bangalore real estate"
        }
        res = self.verifier.verify_record(record)
        self.assertTrue(res["is_valid"])
        self.assertFalse(res["is_deleted"])
        self.assertFalse(res["is_removed"])
        self.assertTrue(res["url_exists"])

    def test_deleted_by_author_content(self):
        record = {
            "public_name_or_handle": "u/karthik_tech",
            "platform": "Reddit (r/bangalore)",
            "source_link": "https://www.reddit.com/r/bangalore/comments/18m9xp1/dubai_real_estate/",
            "raw_text": "[deleted]",
            "platform_context": "r/bangalore thread"
        }
        res = self.verifier.verify_record(record)
        self.assertFalse(res["is_valid"])
        self.assertTrue(res["is_deleted"])
        self.assertIn("deleted by the author", res["reason"].lower())

    def test_removed_by_moderators_content(self):
        record = {
            "public_name_or_handle": "u/hyderabad_guy",
            "platform": "Reddit (r/hyderabad)",
            "source_link": "https://www.reddit.com/r/hyderabad/comments/18x9812/kokapet_prices/",
            "raw_text": "[removed]",
            "platform_context": "r/hyderabad real estate"
        }
        res = self.verifier.verify_record(record)
        self.assertFalse(res["is_valid"])
        self.assertTrue(res["is_removed"])
        self.assertIn("removed", res["reason"].lower())

    def test_deleted_author_handle(self):
        record = {
            "public_name_or_handle": "u/[deleted]",
            "platform": "Reddit (r/kerala)",
            "source_link": "https://www.reddit.com/r/kerala/comments/18t9182/investing_in_dubai/",
            "raw_text": "I had budget of 2 Cr for Dubai property.",
            "platform_context": "r/kerala thread"
        }
        res = self.verifier.verify_record(record)
        self.assertFalse(res["is_valid"])
        self.assertTrue(res["is_deleted"])
        self.assertIn("author deleted", res["reason"].lower())

    def test_moderator_removal_phrase(self):
        record = {
            "public_name_or_handle": "u/chennai_investor",
            "platform": "Reddit (r/chennai)",
            "source_link": "https://www.reddit.com/r/chennai/comments/18z0192/dubai_flats/",
            "raw_text": "Sorry, this post has been removed by the moderators of r/chennai.",
            "platform_context": "r/chennai property"
        }
        res = self.verifier.verify_record(record)
        self.assertFalse(res["is_valid"])
        self.assertTrue(res["is_removed"])
        self.assertIn("removed", res["reason"].lower())

    def test_deleted_by_user_phrase(self):
        record = {
            "public_name_or_handle": "u/vizag_prop",
            "platform": "Reddit (r/IndiaInvestments)",
            "source_link": "https://www.reddit.com/r/IndiaInvestments/comments/18v9102/dubai_remittance/",
            "raw_text": "[deleted by user] I decided to withdraw my Dubai property inquiry.",
            "platform_context": "r/IndiaInvestments comment"
        }
        res = self.verifier.verify_record(record)
        self.assertFalse(res["is_valid"])
        self.assertTrue(res["is_deleted"])
        self.assertIn("deleted", res["reason"].lower())

    def test_invalid_or_dead_url(self):
        record = {
            "public_name_or_handle": "u/some_user",
            "platform": "Reddit (r/bangalore)",
            "source_link": "https://www.reddit.com/r/bangalore/comments/deadpost_123/deleted_post/",
            "raw_text": "Valid text but dead link.",
            "platform_context": "r/bangalore thread"
        }
        res = self.verifier.verify_record(record)
        self.assertFalse(res["is_valid"])
        self.assertFalse(res["url_exists"])

    def test_classifier_rejects_deleted_post_even_with_high_intent_content(self):
        geo_info = {
            "state": "Karnataka",
            "city": "Bengaluru",
            "city_state": "Bengaluru, Karnataka",
            "confidence": "HIGH"
        }
        # Record with high budget and locality but marked deleted
        res = self.classifier.classify_lead(
            text="[deleted]",
            geo_info=geo_info,
            source_link="https://www.reddit.com/r/bangalore/comments/18m9xp1/dubai_property/",
            public_name_or_handle="u/[deleted]",
            platform="Reddit (r/bangalore)"
        )
        self.assertEqual(res["qualification_status"], "Reject")
        self.assertEqual(res["score"], 0)
        self.assertFalse(res["is_qualified"])
        self.assertIn("Disqualified", res["qualification_reason"])

    def test_classifier_rejects_moderator_removed_post(self):
        geo_info = {
            "state": "Telangana",
            "city": "Hyderabad",
            "city_state": "Hyderabad, Telangana",
            "confidence": "HIGH"
        }
        res = self.classifier.classify_lead(
            text="Sorry, this post has been removed by the moderators of r/hyderabad.",
            geo_info=geo_info,
            source_link="https://www.reddit.com/r/hyderabad/comments/18x9812/dubai_flats/",
            public_name_or_handle="u/hyd_user_1",
            platform="Reddit (r/hyderabad)"
        )
        self.assertEqual(res["qualification_status"], "Reject")
        self.assertEqual(res["score"], 0)
        self.assertFalse(res["is_qualified"])
        self.assertIn("removed from the community", res["qualification_reason"])


if __name__ == "__main__":
    unittest.main()

