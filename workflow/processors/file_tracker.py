"""
Input File Tracking and State Management for Incremental Pipeline Execution.
Maintains results/processed.json to ensure that:
1. Already processed input files are recorded with filename and processed status.
2. When new input files (e.g. raw JSON or CSV) are added, the pipeline runs ONLY
   for the new files and updates existing results without duplicate re-processing.
"""

import os
import json
import hashlib
from typing import Dict, List, Any, Optional
from datetime import datetime


class InputFileTracker:
    def __init__(self, results_dir: str = "results", processed_filename: str = "processed.json"):
        self.results_dir = results_dir
        self.processed_path = os.path.join(results_dir, processed_filename)
        self.processed_data: Dict[str, Dict[str, Any]] = self._load()

    def _compute_checksum(self, filepath: str) -> str:
        """Computes MD5 hash of file content."""
        hasher = hashlib.md5()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def _load(self) -> Dict[str, Dict[str, Any]]:
        """
        Loads processed files registry from results/processed.json.
        Supports both dict-of-entries and list-of-entries formats.
        """
        if not os.path.exists(self.processed_path):
            return {}

        try:
            with open(self.processed_path, mode="r", encoding="utf-8") as f:
                data = json.load(f)

            registry = {}
            if isinstance(data, dict):
                items = data.get("processed_files", data)
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, dict) and "filename" in item:
                            registry[item["filename"]] = item
                elif isinstance(items, dict):
                    for k, v in items.items():
                        if isinstance(v, dict):
                            registry[v.get("filename", k)] = v
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and "filename" in item:
                        registry[item["filename"]] = item

            return registry
        except Exception:
            return {}

    def is_file_processed(self, filepath: str, check_checksum: bool = True) -> bool:
        """
        Checks whether a file has already been processed with status == 'PROCESSED'.
        Optionally verifies that the file content hasn't been modified since processing.
        """
        filename = os.path.basename(filepath)
        entry = self.processed_data.get(filename)
        if not entry:
            return False

        if entry.get("status") != "PROCESSED":
            return False

        if check_checksum and os.path.exists(filepath):
            cached_checksum = entry.get("checksum_md5")
            if cached_checksum:
                current_checksum = self._compute_checksum(filepath)
                if current_checksum != cached_checksum:
                    # Content changed; needs re-processing
                    return False

        return True

    def get_unprocessed_files(self, input_dir: str, check_checksum: bool = True) -> List[str]:
        """
        Discovers all supported input files (.csv, .json) in input_dir
        that have NOT yet been marked as PROCESSED in processed.json.
        """
        if not os.path.exists(input_dir):
            return []

        all_files = sorted(os.listdir(input_dir))
        unprocessed = []

        for fname in all_files:
            if fname.startswith("."):
                continue
            lower = fname.lower()
            if not (lower.endswith(".csv") or lower.endswith(".json")):
                continue

            full_path = os.path.join(input_dir, fname)
            if not os.path.isfile(full_path):
                continue

            if not self.is_file_processed(full_path, check_checksum=check_checksum):
                unprocessed.append(full_path)

        return unprocessed

    def mark_processed(
        self,
        filepath: str,
        records_count: int,
        status: str = "PROCESSED"
    ) -> Dict[str, Any]:
        """
        Records a file in processed.json with its filename, status, timestamp,
        records count, and checksum.
        """
        filename = os.path.basename(filepath)
        checksum = self._compute_checksum(filepath) if os.path.exists(filepath) else ""

        entry = {
            "filename": filename,
            "status": status,
            "file_path": filepath,
            "processed_at": datetime.now().isoformat(),
            "records_count": records_count,
            "checksum_md5": checksum
        }
        self.processed_data[filename] = entry
        self.save()
        return entry

    def save(self):
        """Persists the processed files state into results/processed.json."""
        os.makedirs(self.results_dir, exist_ok=True)
        with open(self.processed_path, mode="w", encoding="utf-8") as f:
            json.dump(self.processed_data, f, indent=2)

    def get_processed_summary(self) -> Dict[str, Any]:
        """Returns summary dictionary of processed files."""
        return {
            "total_processed_files": len(self.processed_data),
            "files": list(self.processed_data.values())
        }

