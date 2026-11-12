"""
Unit tests for CSV-based Harvesters (Reddit, YouTube, Forums/Expos).
Verifies that harvesters parse directly from the raw input CSV without hardcoded data.
"""

import os
import unittest
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
        harvester = YouTubeHarvester(csv_path=self.csv_path)
        records = harvester.harvest()
        self.assertGreater(len(records), 0)
        self.assertTrue(all("youtube" in r["platform"].lower() or "youtube.com" in r["source_link"].lower() for r in records))

    def test_forum_harvester_parses_from_csv(self):
        harvester = ForumHarvester(csv_path=self.csv_path)
        records = harvester.harvest()
        self.assertGreater(len(records), 0)
        self.assertTrue(all("reddit" not in r["platform"].lower() and "youtube" not in r["platform"].lower() for r in records))

    def test_total_records_partition_cleanly(self):
        r_rec = RedditHarvester(csv_path=self.csv_path).harvest()
        y_rec = YouTubeHarvester(csv_path=self.csv_path).harvest()
        f_rec = ForumHarvester(csv_path=self.csv_path).harvest()
        self.assertEqual(len(r_rec) + len(y_rec) + len(f_rec), 258)

    def test_missing_csv_file_raises_filenotfound(self):
        harvester = RedditHarvester(csv_path="nonexistent_directory/fake.csv")
        with self.assertRaises(FileNotFoundError):
            harvester.harvest()


if __name__ == "__main__":
    unittest.main()

