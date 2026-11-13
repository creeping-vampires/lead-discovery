"""
Unit tests for CSV-based Harvesters (Reddit, YouTube, Forums/Expos).
Verifies that harvesters parse directly from the raw input CSV without hardcoded data.
"""

import os
import unittest
from workflow.harvesters.base import BaseHarvester
from workflow.harvesters.reddit_harvester import RedditHarvester
from workflow.harvesters.youtube_harvester import YouTubeHarvester
from workflow.harvesters.forum_harvester import ForumHarvester


class TestHarvesters(unittest.TestCase):
    def setUp(self):
        self.csv_path = "input/raw_discovered_candidates.csv"

    def test_reddit_harvester_parses_from_csv(self):
        harvester = RedditHarvester(csv_path=self.csv_path)
        records = harvester.harvest()
        self.assertGreater(len(records), 0)
        self.assertTrue(all("reddit" in r["platform"].lower() or "reddit.com" in r["source_link"].lower() for r in records))
        first = records[0]
        self.assertIn("public_name_or_handle", first)
        self.assertIn("source_link", first)
        self.assertIn("raw_text", first)

    def test_youtube_harvester_parses_from_csv(self):
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as tmp:
            tmp.write("public_name_or_handle,platform,source_link,signal_date,raw_text,platform_context\n@test_yt,YouTube Public Comments,https://youtube.com/watch?v=12345678,2026-10-01,Test raw text,context\n")
            tmp_path = tmp.name
        try:
            harvester = YouTubeHarvester(csv_path=tmp_path)
            records = harvester.harvest()
            self.assertEqual(len(records), 1)
            self.assertTrue(all("youtube" in r["platform"].lower() or "youtube.com" in r["source_link"].lower() for r in records))
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_forum_harvester_parses_from_csv(self):
        harvester = ForumHarvester(csv_path=self.csv_path)
        records = harvester.harvest()
        self.assertGreater(len(records), 0)
        self.assertTrue(all("reddit" not in r["platform"].lower() and "youtube" not in r["platform"].lower() for r in records))

    def test_total_records_partition_cleanly(self):
        r_harv = RedditHarvester(csv_path=self.csv_path)
        r_rec = r_harv.harvest()
        y_rec = YouTubeHarvester(csv_path=self.csv_path).harvest()
        f_rec = ForumHarvester(csv_path=self.csv_path).harvest()
        all_recs = r_harv.load_all_records()
        self.assertEqual(len(r_rec) + len(y_rec) + len(f_rec), len(all_recs))

    def test_missing_csv_file_raises_filenotfound(self):
        harvester = RedditHarvester(csv_path="nonexistent_directory/fake.csv")
        with self.assertRaises(FileNotFoundError):
            harvester.harvest()


if __name__ == "__main__":
    unittest.main()

