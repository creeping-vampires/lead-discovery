"""
YouTube public comment harvester for Dubai Real Estate webinars and investor videos.
Parses raw candidate records directly from the raw input CSV file.
Captures inquiries from public video discussions targeting South Indian investors.
"""

from typing import List, Dict, Any, Optional
from workflow.harvesters.base import BaseHarvester


class YouTubeHarvester(BaseHarvester):
    def __init__(self, csv_path: str = "input/raw_discovered_candidates.csv"):
        super().__init__("YouTube", csv_path=csv_path)

    def harvest(self, custom_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Parses raw YouTube prospect records from the input file.
        Filters comments and Q&A from authorized property video discussions.
        """
        return self.parse_platform_records("youtube", custom_path=custom_path)
