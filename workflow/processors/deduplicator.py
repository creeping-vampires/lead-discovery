"""
Deduplication and Entity Consolidation Engine.
Enforces:
1. Deduplication of repeated URLs within the same platform.
2. Deduplication of canonical public handles within the same platform.
3. Zero cross-platform speculative merging (preserves distinct platform identities).
"""

from typing import List, Dict, Set, Tuple
import hashlib


class Deduplicator:
    def __init__(self):
        # Platform-scoped handle and URL tracking: (canonical_platform, canonical_identifier)
        self.seen_platform_handles: Set[Tuple[str, str]] = set()
        self.seen_platform_urls: Set[Tuple[str, str]] = set()
        self.seen_content_hashes: Set[str] = set()

    def canonical_platform(self, platform: str) -> str:
        """Normalizes platform string to a canonical identifier."""
        p = (platform or "").lower().strip()
        if "reddit" in p:
            return "reddit"
        elif "youtube" in p or "youtu.be" in p:
            return "youtube"
        elif "iref" in p or "indianrealestateforum" in p:
            return "iref"
        elif "quora" in p:
            return "quora"
        elif "linkedin" in p:
            return "linkedin"
        elif "expo" in p or "roadshow" in p or "propertyshow" in p:
            return "expo"
        return p or "unknown"

    def normalize_handle(self, handle: str) -> str:
        """Normalizes public handle removing leading u/ or @ prefixes."""
        clean = (handle or "").strip().lower()
        clean = clean.replace("@", "").replace("u/", "")
        return clean.strip()

    def normalize_url(self, url: str) -> str:
        """Canonicalizes URL for comparison (removes session query params, tracking, trailing slashes)."""
        if not url:
            return ""
        # Strip query parameters and trailing slashes for base canonical URL
        clean = url.strip().split("?")[0].rstrip("/")
        return clean.lower()

    def _content_hash(self, text: str) -> str:
        simplified = "".join((text or "").lower().split())[:100]
        return hashlib.md5(simplified.encode('utf-8')).hexdigest()

    def process(self, records: List[Dict[str, any]]) -> List[Dict[str, any]]:
        """
        Deduplicates candidate records strictly within the same platform.
        Does NOT merge unrelated accounts across platforms based on speculative identity matching.
        """
        unique_records = []
        platform_handle_to_idx: Dict[Tuple[str, str], int] = {}
        duplicates_pruned_count = 0

        for rec in records:
            platform = rec.get("platform", "").strip()
            c_platform = self.canonical_platform(platform)
            rec["canonical_platform"] = c_platform

            handle = rec.get("public_name_or_handle", "").strip()
            norm_handle = self.normalize_handle(handle)

            url = rec.get("source_link", "").strip()
            norm_url = self.normalize_url(url)

            text = rec.get("dubai_property_evidence") or rec.get("raw_text") or ""
            c_hash = self._content_hash(text)

            is_generic_handle = norm_handle in ("", "anonymous", "deleted", "[deleted]", "user")
            handle_key = (c_platform, norm_handle)
            url_key = (c_platform, norm_url)

            # 1. Intra-Platform Handle Deduplication
            if not is_generic_handle and handle_key in platform_handle_to_idx:
                existing_idx = platform_handle_to_idx[handle_key]
                existing = unique_records[existing_idx]

                # Upgrade if current record has higher score or Strong Signal
                curr_status = rec.get("qualification_status")
                exist_status = existing.get("qualification_status")
                curr_score = rec.get("score", 0)
                exist_score = existing.get("score", 0)

                if (curr_status == "Strong Signal" and exist_status != "Strong Signal") or (curr_score > exist_score):
                    unique_records[existing_idx] = rec

                duplicates_pruned_count += 1
                continue

            # 2. Intra-Platform URL + Content Hash Deduplication
            if norm_url and url_key in self.seen_platform_urls and c_hash in self.seen_content_hashes:
                duplicates_pruned_count += 1
                continue

            # Register as seen within this platform
            if not is_generic_handle:
                self.seen_platform_handles.add(handle_key)
                platform_handle_to_idx[handle_key] = len(unique_records)

            if norm_url:
                self.seen_platform_urls.add(url_key)
            self.seen_content_hashes.add(c_hash)

            unique_records.append(rec)

        return unique_records
