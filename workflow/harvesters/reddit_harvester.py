"""
Reddit harvester for South India & Dubai real estate buying signals.
Parses raw candidate records directly from the raw input CSV file.
Covers r/bangalore, r/hyderabad, r/kerala, r/chennai, r/IndiaInvestments, r/personalfinanceindia, r/nri, r/dubairealestate.
"""

from typing import List, Dict, Any
from workflow.harvesters.base import BaseHarvester


class RedditHarvester(BaseHarvester):
    def __init__(self, csv_path: str = "input/raw_discovered_candidates.csv"):
        super().__init__("Reddit", csv_path=csv_path)

    def harvest(self) -> List[Dict[str, Any]]:
        """
        Parses raw Reddit prospect records from the input CSV file.
        Filters discussions from South Indian regional and investment subreddits.
        """
        return self.parse_platform_records("reddit")
