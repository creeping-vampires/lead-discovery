"""
Base harvester interface for parsing raw candidate records from input CSV files.
"""

import os
import csv
import json
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class BaseHarvester(ABC):
    def __init__(self, name: str, csv_path: str = "input/raw_discovered_candidates.csv"):
        self.name = name
        self.csv_path = csv_path

    def load_all_records(self, custom_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Parses raw candidate records directly from the input CSV or JSON file.
        Returns a list of dictionaries with raw lead attributes.
        """
        path = custom_path or self.csv_path
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"Raw input file not found at: '{path}'. "
                f"Please ensure '{path}' exists before running the harvester."
            )

        records: List[Dict[str, Any]] = []

        # Parse JSON format if extension is .json
        if path.lower().endswith(".json"):
            with open(path, mode="r", encoding="utf-8", errors="replace") as f:
                data = json.load(f)

            if isinstance(data, list):
                raw_items = data
            elif isinstance(data, dict):
                for key in ["leads", "candidates", "records", "data"]:
                    if key in data and isinstance(data[key], list):
                        raw_items = data[key]
                        break
                else:
                    raw_items = [v for v in data.values() if isinstance(v, dict)]
            else:
                raw_items = []

            for item in raw_items:
                if isinstance(item, dict):
                    cleaned = {str(k).strip(): (str(v).strip() if v is not None else "") for k, v in item.items() if k}
                    records.append(cleaned)
            return records

        # Otherwise parse as standard CSV
        with open(path, mode="r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cleaned_row = {k.strip(): (v.strip() if v else "") for k, v in row.items() if k}
                records.append(cleaned_row)

        return records

    def parse_platform_records(self, platform_name: str, custom_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Filters and parses records from the raw input CSV matching a specific platform category.
        Categorization is strictly partitioned:
        - 'Reddit': Reddit subreddits and reddit.com links
        - 'YouTube': YouTube webinars and youtube.com links
        - 'Forums & Expos': Quora, IREF, and South India Property Expos
        """
        all_records = self.load_all_records(custom_path)
        target = platform_name.lower().strip()

        matched = []
        for r in all_records:
            platform = r.get("platform", "").lower()
            link = r.get("source_link", "").lower()

            is_reddit = "reddit" in platform or "reddit.com" in link
            is_youtube = "youtube" in platform or "youtube.com" in link or "youtu.be" in link

            if target == "reddit" and is_reddit:
                matched.append(r)
            elif target == "youtube" and is_youtube:
                matched.append(r)
            elif target in ("forums & expos", "forum", "forums") and not is_reddit and not is_youtube:
                matched.append(r)

        return matched

    @abstractmethod
    def harvest(self, custom_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Parses raw prospect records from the input file for this harvester's platform.
        """
        pass
