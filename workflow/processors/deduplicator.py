"""
Deduplication and entity consolidation processor.
Ensures zero duplicate prospects and merges multiple interactions from the same public handle.
"""

from typing import List, Dict, Set
import hashlib


class Deduplicator:
    def __init__(self):
        self.seen_handles: Set[str] = set()
        self.seen_urls: Set[str] = set()
        self.seen_content_hashes: Set[str] = set()

    def _normalize_handle(self, handle: str) -> str:
        return handle.strip().lower().replace("@", "").replace("u/", "")

    def _normalize_url(self, url: str) -> str:
        # Strip query parameters and trailing slashes for canonical comparison
        clean = url.split("?")[0].rstrip("/")
        return clean.lower()

    def _content_hash(self, text: str) -> str:
        simplified = "".join(text.lower().split())[:80]
        return hashlib.md5(simplified.encode('utf-8')).hexdigest()

    def process(self, records: List[Dict[str, any]]) -> List[Dict[str, any]]:
        """
        Deduplicates candidate records, pruning duplicates and preserving unique prospects.
        """
        unique_records = []
        handle_to_record_idx: Dict[str, int] = {}

        for rec in records:
            handle = rec.get("public_name_or_handle", "").strip()
            norm_handle = self._normalize_handle(handle)
            url = rec.get("source_link", "").strip()
            norm_url = self._normalize_url(url)
            text = rec.get("dubai_property_evidence", "").strip()
            c_hash = self._content_hash(text)

            # Skip anonymous or generic handles from strict handle dedup, but check content hash
            is_generic_handle = norm_handle in ("", "anonymous", "deleted", "[deleted]", "user")

            if not is_generic_handle and norm_handle in handle_to_record_idx:
                # Merge information into existing record if new record has stronger intent or more data
                existing_idx = handle_to_record_idx[norm_handle]
                existing = unique_records[existing_idx]
                
                # If current has higher score or Strong Signal, upgrade
                if rec.get("qualification_status") == "Strong Signal" and existing.get("qualification_status") != "Strong Signal":
                    unique_records[existing_idx] = rec
                continue

            if norm_url and norm_url in self.seen_urls and c_hash in self.seen_content_hashes:
                # Exact same post and text
                continue

            # Register as seen
            if not is_generic_handle:
                self.seen_handles.add(norm_handle)
                handle_to_record_idx[norm_handle] = len(unique_records)

            if norm_url:
                self.seen_urls.add(norm_url)
            self.seen_content_hashes.add(c_hash)

            unique_records.append(rec)

        return unique_records

