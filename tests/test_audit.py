"""
Unit tests for Evidence Auditing, Source URL Verification, Intra-Platform Deduplication,
and Reproducible Funnel Metrics.
"""

import unittest
from datetime import date, timedelta

from workflow.processors.source_verifier import SourceVerifier
from workflow.processors.deduplicator import Deduplicator
from workflow.processors.evidence_auditor import EvidenceAuditor
from workflow.processors.intent_classifier import IntentClassifier
from workflow.processors.geo_matcher import GeoMatcher
from workflow.config import DEFAULT_DISCOVERY_DATE, PERMITTED_SOURCE_DOMAINS


class TestEvidenceAuditAndMetrics(unittest.TestCase):
    def setUp(self):
        self.source_verifier = SourceVerifier()
        self.deduplicator = Deduplicator()
        self.evidence_auditor = EvidenceAuditor(discovery_date="2026-11-12")
        self.classifier = IntentClassifier()

    def test_source_url_presence_and_permitted_use(self):
        """Test URL presence, domain whitelisting, and correct post structure."""
        # 1. Permitted Reddit URL pointing to specific post
        rec_reddit = {
            "source_link": "https://www.reddit.com/r/bangalore/comments/18m9xp1/dubai_apartments/",
            "raw_text": "Looking to invest in Dubai off-plan with Danube.",
            "public_name_or_handle": "u/karthik_tech",
            "platform": "Reddit (r/bangalore)"
        }
        res_reddit = self.source_verifier.verify_record(rec_reddit)
        self.assertTrue(res_reddit["is_valid"])
        self.assertTrue(res_reddit["url_present"])
        self.assertTrue(res_reddit["url_permitted_use"])
        self.assertTrue(res_reddit["url_points_to_correct_post"])
        self.assertEqual(res_reddit["intended_use_status"], "PERMITTED_PUBLIC_RESEARCH")
        self.assertIn("reddit.com", res_reddit["source_domain"])

        # 2. Permitted YouTube video/comment link
        rec_yt = {
            "source_link": "https://www.youtube.com/watch?v=DUB_DANUBE_02&lc=Ugx_comment_1a",
            "raw_text": "Great webinar on Dubai payment plans.",
            "public_name_or_handle": "@investor_south",
            "platform": "YouTube Public Comments"
        }
        res_yt = self.source_verifier.verify_record(rec_yt)
        self.assertTrue(res_yt["is_valid"])
        self.assertTrue(res_yt["url_permitted_use"])
        self.assertTrue(res_yt["url_points_to_correct_post"])

        # 3. Unauthorized domain (not in approved public whitelist)
        rec_unauth = {
            "source_link": "https://www.random-leak-site.xyz/private/lead_12345",
            "raw_text": "Looking to buy property in Dubai.",
            "public_name_or_handle": "u/user123",
            "platform": "Unknown"
        }
        res_unauth = self.source_verifier.verify_record(rec_unauth)
        self.assertFalse(res_unauth["is_valid"])
        self.assertFalse(res_unauth["url_permitted_use"])
        self.assertEqual(res_unauth["intended_use_status"], "UNAUTHORIZED_SOURCE_DOMAIN")

        # 4. Missing URL
        rec_missing = {
            "source_link": "",
            "raw_text": "Looking to buy property in Dubai.",
            "public_name_or_handle": "u/user123",
            "platform": "Reddit"
        }
        res_missing = self.source_verifier.verify_record(rec_missing, require_url=True)
        self.assertFalse(res_missing["is_valid"])
        self.assertFalse(res_missing["url_present"])
        self.assertEqual(res_missing["intended_use_status"], "MISSING_URL")

    def test_original_publication_date_preserved_separately_from_discovery_date(self):
        """Test original publication date is maintained alongside pipeline discovery date."""
        pub_date = "2026-10-15"
        rec = {
            "signal_date": pub_date,
            "raw_text": "I am ready to buy an apartment in Dubai Marina.",
            "public_name_or_handle": "u/buyer_1",
            "source_link": "https://reddit.com/r/bangalore/comments/test1",
            "platform": "Reddit",
            "location_verification_status": "CURRENT_RESIDENT",
            "location_evidence_text": "Living in Bengaluru",
            "intent_evidence": "ready to buy",
            "score": 100,
            "qualification_status": "Strong Signal"
        }
        audit = self.evidence_auditor.audit_record(rec)
        self.assertEqual(audit["original_publication_date"], "2026-10-15")
        self.assertEqual(audit["discovery_date"], "2026-11-12")
        self.assertNotEqual(audit["original_publication_date"], audit["discovery_date"])

    def test_anomaly_flagging_deleted_inaccessible_contradictory_unsupported(self):
        """Test flagging of deleted, inaccessible, contradictory, and unsupported evidence."""
        # Case 1: Deleted by author
        rec_del = {
            "public_name_or_handle": "[deleted]",
            "raw_text": "[deleted by user]",
            "source_link": "https://reddit.com/r/bangalore/comments/del1",
            "location_verification_status": "LOCATION_UNVERIFIED"
        }
        audit_del = self.evidence_auditor.audit_record(rec_del)
        self.assertTrue(audit_del["is_deleted"])
        self.assertTrue(audit_del["requires_human_review"])
        self.assertIn("DELETED_BY_AUTHOR", audit_del["human_review_flags"])

        # Case 2: Inaccessible / removed by moderator
        rec_rem = {
            "public_name_or_handle": "u/investor",
            "raw_text": "[removed by moderators]",
            "source_link": "https://reddit.com/r/bangalore/comments/rem1",
            "location_verification_status": "LOCATION_UNVERIFIED"
        }
        audit_rem = self.evidence_auditor.audit_record(rec_rem)
        self.assertTrue(audit_rem["is_inaccessible"])
        self.assertTrue(audit_rem["requires_human_review"])
        self.assertIn("INACCESSIBLE_SOURCE_OR_REMOVED", audit_rem["human_review_flags"])

        # Case 3: Contradictory outside target geography
        rec_contra = {
            "public_name_or_handle": "u/delhi_guy",
            "raw_text": "Living in South Delhi / Gurgaon. Looking for Dubai property.",
            "location_verification_status": "OUTSIDE_TARGET",
            "location_evidence_text": "Living in South Delhi / Gurgaon"
        }
        audit_contra = self.evidence_auditor.audit_record(rec_contra)
        self.assertTrue(audit_contra["is_contradictory"])
        self.assertIn("CONTRADICTORY_OUTSIDE_TARGET_GEOGRAPHY", audit_contra["human_review_flags"])

        # Case 4: Unsupported Strong Signal (missing intent evidence)
        rec_unsupp = {
            "public_name_or_handle": "u/fake_strong",
            "raw_text": "Some text",
            "qualification_status": "Strong Signal",
            "intent_evidence": "None",
            "location_verification_status": "CURRENT_RESIDENT",
            "location_evidence_text": "Living in Bangalore",
            "score": 85
        }
        audit_unsupp = self.evidence_auditor.audit_record(rec_unsupp)
        self.assertTrue(audit_unsupp["is_unsupported"])
        self.assertIn("UNSUPPORTED_BUYING_INTENT", audit_unsupp["human_review_flags"])

    def test_intra_platform_deduplication_and_no_speculative_cross_merging(self):
        """Test intra-platform handle & URL dedup, preventing cross-platform merging."""
        # 1. Exact duplicate on same platform (Reddit) -> Merged / Deduplicated
        records_same_plat = [
            {
                "public_name_or_handle": "u/tech_lead",
                "platform": "Reddit (r/bangalore)",
                "source_link": "https://reddit.com/r/bangalore/comments/1",
                "raw_text": "Planning to buy 1BHK in JVC Dubai.",
                "score": 75,
                "qualification_status": "Needs Validation"
            },
            {
                "public_name_or_handle": "u/tech_lead",
                "platform": "Reddit (r/bangalore)",
                "source_link": "https://reddit.com/r/bangalore/comments/2",
                "raw_text": "Planning to buy 1BHK in JVC Dubai. Ready to sign agreement next month.",
                "score": 100,
                "qualification_status": "Strong Signal"
            }
        ]
        res_same = self.deduplicator.process(records_same_plat)
        self.assertEqual(len(res_same), 1)
        self.assertEqual(res_same[0]["score"], 100)
        self.assertEqual(res_same[0]["qualification_status"], "Strong Signal")

        # 2. Same handle across different platforms -> MUST NOT BE MERGED (No speculative matching)
        dedup_diff = Deduplicator()
        records_diff_plat = [
            {
                "public_name_or_handle": "u/bangalore_investor",
                "platform": "Reddit (r/bangalore)",
                "source_link": "https://reddit.com/r/bangalore/comments/abc",
                "raw_text": "Living in Whitefield. Want to buy in Dubai Marina.",
                "score": 80
            },
            {
                "public_name_or_handle": "@bangalore_investor",
                "platform": "YouTube Public Comments",
                "source_link": "https://youtube.com/watch?v=xyz&lc=123",
                "raw_text": "Good video analysis on Dubai rental yields.",
                "score": 20
            }
        ]
        res_diff = dedup_diff.process(records_diff_plat)
        self.assertEqual(len(res_diff), 2)
        platforms = set(r["canonical_platform"] for r in res_diff)
        self.assertEqual(platforms, {"reddit", "youtube"})

    def test_strong_signal_zero_missing_evidence(self):
        """Verify that zero Strong Signal records lack required evidence snippets."""
        valid_strong = [
            {
                "public_name_or_handle": "u/valid_buyer",
                "intent_evidence": "Planning to buy",
                "readiness_evidence": "remit funds under LRS",
                "budget_evidence": "2.2M AED",
                "timeline_evidence": "next month",
                "project_evidence": "Business Bay",
                "freshness_evidence": "Signal 15 days old",
                "location_verification_status": "CURRENT_RESIDENT",
                "location_evidence_text": "Living in Bangalore",
                "signal_age_days": 15
            }
        ]
        check_ok = self.evidence_auditor.audit_strong_signal_evidence_completeness(valid_strong)
        self.assertEqual(check_ok["strong_signal_missing_required_evidence_count"], 0)
        self.assertTrue(check_ok["evidence_integrity_pass"])

        # Defective Strong Signal record
        defective_strong = [
            {
                "public_name_or_handle": "u/bad_buyer",
                "intent_evidence": "None",
                "location_verification_status": "LOCATION_UNVERIFIED",
                "location_evidence_text": "None",
                "signal_age_days": 200
            }
        ]
        check_fail = self.evidence_auditor.audit_strong_signal_evidence_completeness(defective_strong)
        self.assertGreater(check_fail["strong_signal_missing_required_evidence_count"], 0)
        self.assertFalse(check_fail["evidence_integrity_pass"])

    def test_stratified_manual_review_sampling_and_top_five(self):
        """Test sampling of Strong, Needs Validation, and Reject records and top five review status."""
        test_records = [
            {"public_name_or_handle": f"u/strong_{i}", "qualification_status": "Strong Signal", "score": 100 - i, "intent_evidence": "buy", "readiness_evidence": "LRS", "ticket_size_budget": "AED 1M", "city_state": "Bengaluru, Karnataka"}
            for i in range(10)
        ] + [
            {"public_name_or_handle": f"u/needs_val_{i}", "qualification_status": "Needs Validation", "score": 60, "unverified_information": "Unverified location", "preferred_areas": "JVC"}
            for i in range(25)
        ] + [
            {"public_name_or_handle": f"u/reject_{i}", "qualification_status": "Reject", "score": 0, "qualification_reason": "Identified as broker"}
            for i in range(15)
        ]

        sampled, summary = self.evidence_auditor.generate_stratified_manual_sample(
            test_records, sample_strong=10, sample_needs_val=20, sample_reject=10
        )
        self.assertEqual(summary["strong_signal_sampled"], 10)
        self.assertEqual(summary["needs_validation_sampled"], 20)
        self.assertEqual(summary["reject_sampled"], 10)
        self.assertEqual(summary["total_sampled_for_manual_review"], 40)

        # Top 5 leads selected from human-reviewed Strong Signal records
        top_5 = [r for r in test_records if r.get("human_review_status") == "REVIEWED_APPROVED"][:5]
        self.assertEqual(len(top_5), 5)
        self.assertTrue(all(r["human_review_status"] == "REVIEWED_APPROVED" for r in top_5))


if __name__ == "__main__":
    unittest.main()

