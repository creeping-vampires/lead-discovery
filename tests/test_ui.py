"""
Unit tests for Flask UI Dashboard Application.
Tests:
1. Index route renders HTML dashboard.
2. /api/stats returns reconciled funnel and file tracking statistics.
3. /api/leads supports tab filtering, state filtering, and pagination.
4. /api/leads/<id> retrieves full details of a specific candidate.
5. /api/leads/<id>/review allows approving, rejecting, or updating candidates and synchronizes deliverables.
6. /api/pipeline/run triggers execution with and without reset flag.
7. /api/processed-files returns tracking information.
8. /api/download/<type> sends deliverable files.
"""

import os
import io
import json
import shutil
import tempfile
import unittest

from ui.app import create_app
from workflow.main import run_pipeline


class TestUIDashboard(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.input_dir = os.path.join(self.test_dir, "input")
        self.results_dir = os.path.join(self.test_dir, "results")
        os.makedirs(self.input_dir, exist_ok=True)
        os.makedirs(self.results_dir, exist_ok=True)

        # Create two sample input records
        # 1. Strong candidate
        # 2. Needs validation candidate (missing readiness/timeline)
        self.sample_csv = os.path.join(self.input_dir, "test_leads.csv")
        with open(self.sample_csv, "w", encoding="utf-8") as f:
            f.write(
                "public_name_or_handle,platform,source_link,signal_date,raw_text,platform_context\n"
                "u/strong_buyer,Reddit (r/bangalore),https://www.reddit.com/r/bangalore/comments/test1/,2026-10-15,"
                "\"Living in Whitefield Bangalore. Planning to remit funds to buy 2BHK off-plan apartment in Dubai Marina with Danube. Budget is 2M AED. Ready to sign next month.\",r/bangalore thread\n"
                "u/plausible_buyer,Reddit (r/bangalore),https://www.reddit.com/r/bangalore/comments/test2/,2026-10-20,"
                "\"Working in Whitefield tech park Bangalore. Looking to buy property in Dubai instead of Bangalore. Budget is 1.5 Cr.\",r/bangalore thread\n"
            )

        # Run pipeline once to populate results_dir
        run_pipeline(
            input_dir=self.input_dir,
            output_dir=self.results_dir,
            reprocess_all=True
        )

        self.app = create_app(results_dir=self.results_dir, input_dir=self.input_dir)
        self.client = self.app.test_client()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_index_route(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Dubai Real Estate Leads Qualification Dashboard", res.data)
        self.assertIn(b"Run Pipeline", res.data)

    def test_get_stats(self):
        res = self.client.get("/api/stats")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()

        self.assertIn("funnel", data)
        self.assertIn("geographic", data)
        self.assertIn("files", data)
        self.assertTrue(data["funnel"]["is_reconciled"])
        self.assertEqual(data["funnel"]["unique_candidates"], 2)
        self.assertEqual(data["files"]["processed_count"], 1)

    def test_get_leads_pagination_and_tabs(self):
        # Tab: qualified
        res_qual = self.client.get("/api/leads?tab=qualified")
        self.assertEqual(res_qual.status_code, 200)
        data_qual = res_qual.get_json()
        self.assertGreaterEqual(data_qual["total"], 1)
        for lead in data_qual["leads"]:
            self.assertEqual(lead["qualification_status"], "Strong Signal")

        # Tab: needs_review
        res_nv = self.client.get("/api/leads?tab=needs_review")
        self.assertEqual(res_nv.status_code, 200)
        data_nv = res_nv.get_json()
        self.assertGreaterEqual(data_nv["total"], 1)
        for lead in data_nv["leads"]:
            self.assertEqual(lead["qualification_status"], "Needs Validation")

        # Tab: all
        res_all = self.client.get("/api/leads?tab=all")
        self.assertEqual(res_all.status_code, 200)
        data_all = res_all.get_json()
        self.assertEqual(data_all["total"], 2)

    def test_get_lead_detail(self):
        res_all = self.client.get("/api/leads?tab=all")
        lead_id = res_all.get_json()["leads"][0]["candidate_id"]

        res = self.client.get(f"/api/leads/{lead_id}")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["lead"]["candidate_id"], lead_id)

    def test_manual_review_approve_promotes_lead_and_updates_artifacts(self):
        # Find the Needs Validation candidate
        res_nv = self.client.get("/api/leads?tab=needs_review")
        leads = res_nv.get_json()["leads"]
        self.assertGreater(len(leads), 0)
        target = leads[0]
        cid = target["candidate_id"]

        # Approve this candidate via review endpoint
        payload = {
            "action": "approve",
            "location_verification_status": "CURRENT_RESIDENT",
            "location_evidence_text": "Confirmed current resident in Whitefield Bangalore",
            "score": 85,
            "notes": "Verified booking token paid via Dubai broker in Bangalore branch.",
            "reviewer": "Test Lead Auditor"
        }
        res_review = self.client.post(f"/api/leads/{cid}/review", json=payload)
        self.assertEqual(res_review.status_code, 200)
        data = res_review.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["lead"]["qualification_status"], "Strong Signal")
        self.assertTrue(data["lead"]["is_qualified"])
        self.assertEqual(data["lead"]["location_verification_status"], "CURRENT_RESIDENT")
        self.assertEqual(data["lead"]["score"], 85)

        # Verify that qualified leads count increased and audit report is updated
        res_stats = self.client.get("/api/stats")
        stats = res_stats.get_json()
        self.assertEqual(stats["funnel"]["strong_signal_count"], 2)
        self.assertEqual(stats["funnel"]["needs_validation_count"], 0)

        # Verify artifacts exist on disk and are synchronized
        self.assertTrue(os.path.exists(os.path.join(self.results_dir, "qualified_dubai_leads.xlsx")))
        self.assertTrue(os.path.exists(os.path.join(self.results_dir, "top_5_leads.csv")))
        self.assertTrue(os.path.exists(os.path.join(self.results_dir, "audit_report.json")))

    def test_manual_review_reject_candidate(self):
        res_all = self.client.get("/api/leads?tab=all")
        leads = res_all.get_json()["leads"]
        cid = leads[0]["candidate_id"]

        payload = {
            "action": "reject",
            "notes": "Irrelevant query; broker self-promotion detected.",
            "reviewer": "Test Auditor"
        }
        res_reject = self.client.post(f"/api/leads/{cid}/review", json=payload)
        self.assertEqual(res_reject.status_code, 200)
        data = res_reject.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["lead"]["qualification_status"], "Reject")
        self.assertFalse(data["lead"]["is_qualified"])
        self.assertIn(data["lead"]["human_review_status"], ["REVIEWED_REJECTED", "REVIEWED_CONFIRMED_REJECT"])

    def test_trigger_pipeline_execution(self):
        # Trigger incremental run
        res = self.client.post("/api/pipeline/run", json={"reset": False})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertIn("logs", data)

        # Trigger reset run
        res_reset = self.client.post("/api/pipeline/run", json={"reset": True})
        self.assertEqual(res_reset.status_code, 200)
        data_reset = res_reset.get_json()
        self.assertTrue(data_reset["success"])
        self.assertTrue(data_reset["reset"])

    def test_check_file_endpoint(self):
        # 1. Check already processed file
        res = self.client.post("/api/pipeline/check-file", json={"filename": "test_leads.csv"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["already_processed"])
        self.assertEqual(data["status"], "PROCESSED")

        # 2. Check brand new file
        res_new = self.client.post("/api/pipeline/check-file", json={"filename": "brand_new_batch.csv"})
        self.assertEqual(res_new.status_code, 200)
        data_new = res_new.get_json()
        self.assertFalse(data_new["already_processed"])

    def test_pipeline_run_with_uploaded_file(self):
        # 1. Uploading already processed file without reset -> should not run
        csv_data = b"record_id,platform,author,title,content,post_url,publication_date\nC1,reddit,user1,title1,text1,https://reddit.com/r/dubai/comments/1,2026-10-01\n"
        data = {
            "file": (io.BytesIO(csv_data), "test_leads.csv"),
            "reset": "false"
        }
        res = self.client.post("/api/pipeline/run", data=data, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 200)
        resp_data = res.get_json()
        self.assertTrue(resp_data["success"])
        self.assertTrue(resp_data["already_processed"])
        self.assertIn("already processed", resp_data["message"].lower())

        # 2. Uploading a brand new file -> should save to input/ and process
        new_csv_data = (
            b"record_id,platform,author,title,content,post_url,publication_date\n"
            b"UPLOAD-01,reddit,u_bangalore_investor,Bangalore to Dubai,Living in Bangalore looking to buy 2BHK in Dubai Downtown budget 1.8M AED,https://reddit.com/r/dubai/comments/upload01,2026-10-15\n"
        )
        new_data = {
            "file": (io.BytesIO(new_csv_data), "raw_upload_batch_test.csv"),
            "reset": "false"
        }
        res_new = self.client.post("/api/pipeline/run", data=new_data, content_type="multipart/form-data")
        self.assertEqual(res_new.status_code, 200)
        resp_new = res_new.get_json()
        self.assertTrue(resp_new["success"])
        self.assertFalse(resp_new["already_processed"])
        # Verify file was moved/saved into input folder
        target_path = os.path.join(self.input_dir, "raw_upload_batch_test.csv")
        self.assertTrue(os.path.exists(target_path))

    def test_processed_files_endpoint(self):
        res = self.client.get("/api/processed-files")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["total_tracked"], 1)
        self.assertEqual(len(data["files"]), 1)
        self.assertEqual(data["files"][0]["filename"], "test_leads.csv")
        self.assertTrue(data["files"][0]["is_processed"])

    def test_standalone_browser_view(self):
        # Fetch first lead ID from leads list
        res_leads = self.client.get("/api/leads")
        data = res_leads.get_json()
        lead = data["leads"][0]
        cid = lead["candidate_id"]

        res = self.client.get(f"/leads/{cid}/browser-view")
        self.assertEqual(res.status_code, 302)
        self.assertTrue(res.headers.get("Location").startswith("https://www.reddit.com/r/"))

        # 404 for unknown lead
        res_404 = self.client.get("/leads/NON_EXISTENT_ID/browser-view")
        self.assertEqual(res_404.status_code, 404)

    def test_download_artifacts(self):
        for ftype in ["excel", "top5", "all", "audit", "processed"]:
            res = self.client.get(f"/api/download/{ftype}")
            self.assertEqual(res.status_code, 200, f"Failed downloading {ftype}")
            res.close()


if __name__ == "__main__":
    unittest.main()
