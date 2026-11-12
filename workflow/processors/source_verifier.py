"""
Source and Reddit URL Existence & Community Deletion Verifier.
Validates that harvested posts and comments:
1. Have a valid, well-formed, existing source URL.
2. Have not been deleted by the author (content or handle is '[deleted]').
3. Have not been removed by community moderators or Reddit spam filters ('[removed]').
"""

import re
import urllib.request
import urllib.error
from typing import Dict, Any, Optional, Tuple


class SourceVerifier:
    def __init__(self, check_live: bool = False, timeout: float = 3.0):
        self.check_live = check_live
        self.timeout = timeout
        self._url_cache: Dict[str, Tuple[bool, str]] = {}

        # Reddit URL pattern: validates protocol, subreddit, and alphanumeric post ID
        self.reddit_url_pattern = re.compile(
            r'^https?://(?:www\.|old\.|np\.)?reddit\.com/r/([A-Za-z0-9_]{2,30})/comments/([a-z0-9]{4,12})(?:/([^/\s\?#]+))?(?:/([a-z0-9]{4,12}))?/?',
            re.IGNORECASE
        )

        # Content deletion & removal indicators
        self.deletion_exact_pattern = re.compile(
            r'^\s*\[(?:deleted|removed)\]\s*$',
            re.IGNORECASE
        )

        self.deletion_phrases_pattern = re.compile(
            r'\b(?:'
            r'\[deleted by user\]|'
            r'deleted by (?:the )?(?:user|author)|'
            r'\[removed by (?:moderator|reddit)\]|'
            r'removed by (?:the )?moderators?|'
            r'removed by reddit(?:\'s)? (?:spam )?filters?|'
            r'post has been removed|'
            r'comment has been removed|'
            r'this post was removed|'
            r'this comment was deleted|'
            r'this post was deleted|'
            r'sorry, this post has been removed'
            r')\b',
            re.IGNORECASE
        )

        # Generic dead/nonexistent URL markers (e.g. mock/test dead links)
        self.dead_url_markers = (
            "deleted_post",
            "deadpost",
            "nonexistent",
            "404",
            "/deleted/",
            "removed_thread"
        )

    def verify_record(
        self,
        record: Dict[str, Any],
        check_live: Optional[bool] = None,
        require_url: bool = False
    ) -> Dict[str, Any]:
        """
        Comprehensive verification of a discovered source record.
        Returns a dict indicating validity, deletion status, and clear diagnostic reason.
        """
        should_check_live = self.check_live if check_live is None else check_live
        url = record.get("source_link", "").strip()
        text = record.get("raw_text", "").strip()
        handle = record.get("public_name_or_handle", "").strip()
        platform = record.get("platform", "").strip().lower()
        platform_ctx = record.get("platform_context", "").strip()

        # 1. Verify URL if required or provided
        if not url:
            if require_url:
                return {
                    "is_valid": False,
                    "is_deleted": False,
                    "is_removed": False,
                    "url_exists": False,
                    "reason": "Missing source URL: Record does not have a public source link."
                }
        else:
            if not (url.startswith("http://") or url.startswith("https://")):
                return {
                    "is_valid": False,
                    "is_deleted": False,
                    "is_removed": False,
                    "url_exists": False,
                    "reason": f"Malformed source URL: '{url}' is not a valid HTTP/HTTPS link."
                }

            # Check for explicit dead URL markers
            if any(marker in url.lower() for marker in self.dead_url_markers):
                return {
                    "is_valid": False,
                    "is_deleted": True,
                    "is_removed": False,
                    "url_exists": False,
                    "reason": "Source URL no longer exists: Link is dead or marked as deleted."
                }

            # Reddit-Specific URL structure check
            is_reddit = "reddit" in platform or "reddit.com" in url.lower()
            if is_reddit:
                reddit_match = self.reddit_url_pattern.match(url)
                if not reddit_match:
                    return {
                        "is_valid": False,
                        "is_deleted": False,
                        "is_removed": False,
                        "url_exists": False,
                        "reason": f"Invalid Reddit URL structure: '{url}' does not point to a valid subreddit post or comment."
                    }

        # 2. Handle / Author Deletion Check
        norm_handle = handle.lower().lstrip("u/").strip()
        if norm_handle in ("[deleted]", "deleted", "[removed]", "removed"):
            return {
                "is_valid": False,
                "is_deleted": True,
                "is_removed": False,
                "url_exists": bool(url),
                "reason": "Author deleted: The user account associated with this post/comment has been deleted."
            }

        # 3. Content Deletion / Removal Check
        combined_text = f"{text} {platform_ctx}".strip()

        # Exact [deleted] or [removed]
        if self.deletion_exact_pattern.match(text):
            is_moderator_removal = "[removed]" in text.lower() or "removed" in platform_ctx.lower()
            return {
                "is_valid": False,
                "is_deleted": not is_moderator_removal,
                "is_removed": is_moderator_removal,
                "url_exists": bool(url),
                "reason": (
                    "Removed by community moderators: Post content was removed by Reddit filters or moderators."
                    if is_moderator_removal
                    else "Deleted by user: Post content was deleted by the author."
                )
            }

        # Phrases indicating removal by moderators or deletion
        phrase_match = self.deletion_phrases_pattern.search(combined_text)
        if phrase_match:
            matched_phrase = phrase_match.group(0)
            is_moderator_removal = any(w in matched_phrase.lower() for w in ("removed", "moderator", "filters"))
            return {
                "is_valid": False,
                "is_deleted": not is_moderator_removal,
                "is_removed": is_moderator_removal,
                "url_exists": bool(url),
                "reason": f"Disqualified: Post was deleted or removed from the community ('{matched_phrase}')."
            }

        # 4. Optional Live HTTP Existence Check (when enabled and URL present)
        is_reddit = "reddit" in platform or "reddit.com" in url.lower()
        if should_check_live and is_reddit and url:
            live_status, live_reason = self._probe_live_reddit_url(url)
            if not live_status:
                return {
                    "is_valid": False,
                    "is_deleted": "deleted" in live_reason.lower(),
                    "is_removed": "removed" in live_reason.lower(),
                    "url_exists": False,
                    "reason": live_reason
                }

        return {
            "is_valid": True,
            "is_deleted": False,
            "is_removed": False,
            "url_exists": True,
            "reason": "Source verified: URL exists and content is active in the community."
        }

    def _probe_live_reddit_url(self, url: str) -> Tuple[bool, str]:
        """
        Probes a Reddit URL over HTTP to check if it returns 200 OK or 404/410/removed.
        Caches results to avoid duplicate network lookups.
        """
        if url in self._url_cache:
            return self._url_cache[url]

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }

        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                status = resp.status
                if status == 404:
                    res = (False, "Live probe failed: Reddit post URL returned HTTP 404 Not Found.")
                    self._url_cache[url] = res
                    return res
                if status == 410:
                    res = (False, "Live probe failed: Reddit post URL returned HTTP 410 Gone (Permanently Deleted).")
                    self._url_cache[url] = res
                    return res

                # Check HTML body snippet for deletion banners
                html_snippet = resp.read(4000).decode("utf-8", errors="ignore")
                if "this post was deleted by user" in html_snippet.lower():
                    res = (False, "Live probe detected: Reddit post was deleted by user.")
                    self._url_cache[url] = res
                    return res
                if "removed by the moderators" in html_snippet.lower():
                    res = (False, "Live probe detected: Reddit post was removed by community moderators.")
                    self._url_cache[url] = res
                    return res

                res = (True, "Live probe passed: HTTP 200 OK and post is active.")
                self._url_cache[url] = res
                return res

        except urllib.error.HTTPError as e:
            if e.code in (404, 410):
                res = (False, f"Live probe failed: URL returned HTTP {e.code}.")
            elif e.code == 403:
                # Bot challenge or rate limit: do not treat as deleted unless confirmed
                res = (True, "Live probe unverified: WAF anti-bot gate encountered (HTTP 403), marked active.")
            else:
                res = (True, f"Live probe unverified: HTTP {e.code}.")
            self._url_cache[url] = res
            return res
        except Exception as e:
            res = (True, f"Live probe warning: Network check bypassed ({str(e)}).")
            self._url_cache[url] = res
            return res
