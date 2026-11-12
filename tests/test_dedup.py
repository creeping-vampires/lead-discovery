"""
Unit tests for Deduplication processor.
"""

import unittest
from workflow.processors.deduplicator import Deduplicator


class TestDeduplicator(unittest.TestCase):
    def setUp(self):
        self.dedup = Deduplicator()

    def test_handle_deduplication(self):
        records = [
            {
                "public_name_or_handle": "u/karthik_tech_blr",
                "source_link": "https://reddit.com/r/bangalore/comments/1",
                "dubai_property_evidence": "Investing in JVC Dubai with 1.8 Cr",
                "qualification_status": "Needs Validation"
            },
            {
                "public_name_or_handle": "u/karthik_tech_blr",
                "source_link": "https://reddit.com/r/bangalore/comments/2",
                "dubai_property_evidence": "Finalized budget 1.8 Cr for offplan",
                "qualification_status": "Strong Signal"
            }
        ]
        result = self.dedup.process(records)
        self.assertEqual(len(result), 1)
        # Should upgrade to Strong Signal
        self.assertEqual(result[0]["qualification_status"], "Strong Signal")

    def test_exact_url_and_content_deduplication(self):
        records = [
            {
                "public_name_or_handle": "user_a",
                "source_link": "https://youtube.com/watch?v=123",
                "dubai_property_evidence": "Great video on Sobha Hartland",
                "qualification_status": "Needs Validation"
            },
            {
                "public_name_or_handle": "user_b",
                "source_link": "https://youtube.com/watch?v=123?utm_source=share",
                "dubai_property_evidence": "Great video on Sobha Hartland",
                "qualification_status": "Needs Validation"
            }
        ]
        result = self.dedup.process(records)
        self.assertEqual(len(result), 1)

    def test_distinct_records_preserved(self):
        records = [
            {
                "public_name_or_handle": "user_1",
                "source_link": "https://reddit.com/r/bangalore/comments/10",
                "dubai_property_evidence": "Looking for 1BHK in Marina",
                "qualification_status": "Strong Signal"
            },
            {
                "public_name_or_handle": "user_2",
                "source_link": "https://reddit.com/r/hyderabad/comments/20",
                "dubai_property_evidence": "Looking for 2BHK in Business Bay",
                "qualification_status": "Strong Signal"
            }
        ]
        result = self.dedup.process(records)
        self.assertEqual(len(result), 2)


if __name__ == "__main__":
    unittest.main()

