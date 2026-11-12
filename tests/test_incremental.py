"""
Unit tests for Incremental Pipeline Execution and Processed File Tracking (processed.json).
Verifies that:
1. Processed files are recorded in results/processed.json with filename and PROCESSED status.
2. If no new files exist, the pipeline avoids redundant processing.
3. When a new raw JSON (or CSV) file is added to input/, the pipeline parses ONLY the new file
   and updates existing results.
"""

import os
import json
import shutil
import tempfile
import unittest

from workflow.processors.file_tracker import InputFileTracker
from workflow.harvesters.base import BaseHarvester
from workflow.harvesters.reddit_harvester import RedditHarvester
from workflow.main import run_pipeline, load_existing_candidates


class TestIncrementalPipeline(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.input_dir = os.path.join(self.test_dir, "input")
        self.results_dir = os.path.join(self.test_dir, "results")
        os.makedirs(self.input_dir, exist_ok=True)
        os.makedirs(self.results_dir, exist_ok=True)

        # Create sample base CSV file
        self.base_csv = os.path.join(self.input_dir, "batch_1.csv")
        with open(self.base_csv, "w", encoding="utf-8") as f:
            f.write(
                "public_name_or_handle,platform,source_link,signal_date,raw_text,platform_context\n"
                "u/investor_blr,Reddit (r/bangalore),https://www.reddit.com/r/bangalore/comments/test1/,2026-10-15,"
                "\"Living in Whitefield Bangalore. Planning to buy 2BHK off-plan apartment in Dubai Marina with Danube. Budget is 2M AED. Ready to sign next month.\",r/bangalore thread\n"
            )

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_tracker_records_filename_and_status(self):
        tracker = InputFileTracker(results_dir=self.results_dir)
        self.assertFalse(tracker.is_file_processed(self.base_csv))

        unprocessed = tracker.get_unprocessed_files(self.input_dir)
        self.assertEqual(len(unprocessed), 1)
        self.assertEqual(os.path.basename(unprocessed[0]), "batch_1.csv")

        # Mark processed
        entry = tracker.mark_processed(self.base_csv, records_count=1, status="PROCESSED")
        self.assertEqual(entry["filename"], "batch_1.csv")
        self.assertEqual(entry["status"], "PROCESSED")
        self.assertTrue(tracker.is_file_processed(self.base_csv))

        # Check persistence in processed.json
        tracker_reloaded = InputFileTracker(results_dir=self.results_dir)
        self.assertTrue(tracker_reloaded.is_file_processed(self.base_csv))
        self.assertEqual(tracker_reloaded.processed_data["batch_1.csv"]["status"], "PROCESSED")

    def test_harvester_parses_raw_json(self):
        json_file = os.path.join(self.input_dir, "new_batch.json")
        data = [
            {
                "public_name_or_handle": "u/new_buyer_hyd",
                "platform": "Reddit (r/hyderabad)",
                "source_link": "https://www.reddit.com/r/hyderabad/comments/dubai_test/",
                "signal_date": "2026-10-20",
                "raw_text": "Tech VP based in Gachibowli Hyderabad. Looking to invest AED 2.5M in Sobha Hartland Dubai.",
                "platform_context": "r/hyderabad investment"
            }
        ]
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(data, f)

        harvester = RedditHarvester(csv_path=json_file)
        records = harvester.harvest(custom_path=json_file)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["public_name_or_handle"], "u/new_buyer_hyd")
        self.assertIn("Gachibowli Hyderabad", records[0]["raw_text"])

    def test_incremental_execution_when_new_json_file_added(self):
        # 1. Run 1: Process initial batch_1.csv
        res1 = run_pipeline(
            input_dir=self.input_dir,
            output_dir=self.results_dir,
            discovery_date="2026-11-12"
        )
        self.assertEqual(res1["status"], "PROCESSED")
        self.assertEqual(res1["new_files_processed"], ["batch_1.csv"])
        self.assertEqual(res1["unique_candidates"], 1)

        # Verify processed.json was created
        processed_file = os.path.join(self.results_dir, "processed.json")
        self.assertTrue(os.path.exists(processed_file))
        with open(processed_file, "r", encoding="utf-8") as f:
            state = json.load(f)
        self.assertIn("batch_1.csv", state)
        self.assertEqual(state["batch_1.csv"]["status"], "PROCESSED")

        # 2. Run 2 without adding new files -> should skip processing
        res2 = run_pipeline(
            input_dir=self.input_dir,
            output_dir=self.results_dir,
            discovery_date="2026-11-12"
        )
        self.assertEqual(res2["status"], "UP_TO_DATE")
        self.assertEqual(res2["new_files_processed"], [])

        # 3. Add new raw JSON file with new leads
        new_json = os.path.join(self.input_dir, "batch_2.json")
        new_leads = [
            {
                "public_name_or_handle": "u/founder_chennai",
                "platform": "Reddit (r/chennai)",
                "source_link": "https://www.reddit.com/r/chennai/comments/dubai_prop/",
                "signal_date": "2026-10-18",
                "raw_text": "Surgeon living in Anna Nagar Chennai. Planning to buy luxury 2BHK in Downtown Dubai with Emaar. Budget is 3M AED. Ready to sign booking next week.",
                "platform_context": "r/chennai"
            }
        ]
        with open(new_json, "w", encoding="utf-8") as f:
            json.dump(new_leads, f)

        # 4. Run 3 -> should ONLY process the new batch_2.json and update existing results
        res3 = run_pipeline(
            input_dir=self.input_dir,
            output_dir=self.results_dir,
            discovery_date="2026-11-12"
        )
        self.assertEqual(res3["status"], "PROCESSED")
        self.assertEqual(res3["new_files_processed"], ["batch_2.json"])
        # Should now have 2 unique candidates
        self.assertEqual(res3["unique_candidates"], 2)

        # Verify processed.json now records both files
        with open(processed_file, "r", encoding="utf-8") as f:
            updated_state = json.load(f)
        self.assertIn("batch_1.csv", updated_state)
        self.assertIn("batch_2.json", updated_state)
        self.assertEqual(updated_state["batch_2.json"]["status"], "PROCESSED")

        # Verify existing results files are updated
        existing = load_existing_candidates(os.path.join(self.results_dir, "all_candidates.csv"))
        self.assertEqual(len(existing), 2)
        handles = set(r["public_name_or_handle"] for r in existing)
        self.assertEqual(handles, {"u/investor_blr", "u/founder_chennai"})

        # Verify top_5_leads.csv and qualified_dubai_leads.xlsx are updated
        self.assertTrue(os.path.exists(os.path.join(self.results_dir, "top_5_leads.csv")))
        self.assertTrue(os.path.exists(os.path.join(self.results_dir, "qualified_dubai_leads.xlsx")))


if __name__ == "__main__":
    unittest.main()

