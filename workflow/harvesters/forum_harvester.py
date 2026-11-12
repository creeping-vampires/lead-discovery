"""
Harvester for South India Real Estate Forums, Quora threads, and Property Expos.
Parses raw candidate records directly from the raw input CSV file.
Covers IREF, Quora public discussions, and Dubai Property Show attendee records.
"""

from typing import List, Dict, Any
from workflow.harvesters.base import BaseHarvester


class ForumHarvester(BaseHarvester):
    def __init__(self, csv_path: str = "input/raw_discovered_candidates.csv"):
        super().__init__("Forums & Expos", csv_path=csv_path)

    def harvest(self) -> List[Dict[str, Any]]:
        """
        Parses raw Forum and Property Expo records from the input CSV file.
        Filters IREF discussions, Quora inquiries, and South India roadshow threads.
        """
        return self.parse_platform_records("forums & expos")
