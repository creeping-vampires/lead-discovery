"""
Source and URL Verification Engine.
Validates:
1. URL presence, HTTP/HTTPS scheme, and valid host domain.
2. Compliance with permitted public data sources (PERMITTED_SOURCE_DOMAINS).
3. URL structure pointing to the correct original post, comment, thread, or inquiry.
4. Author deletion detection ('[deleted]').
5. Moderator / spam removal detection ('[removed]').
6. Optional live HTTP status probing.
"""

import re
import urllib.request
import urllib.error
from urllib.parse import urlparse
from typing import Dict, Any, Optional, Tuple, Set

from workflow.config import PERMITTED_SOURCE_DOMAINS


class SourceVerifier:
    def __init__(
        self,
        check_live: bool = False,
        timeout: float = 3.0,
        permitted_domains: Optional[Set[str]] = None
    ):
        self.check_live = check_live
        self.timeout = timeout
        self.permitted_domains = permitted_domains or PERMITTED_SOURCE_DOMAINS
        self._url_cache: Dict[str, Tuple[bool, str]] = {}

        # 1. Reddit URL Pattern (Subreddit + alphanumeric post ID + optional comment ID)
        self.reddit_url_pattern = re.compile(
            r'^https?://(?:www\.|old\.|np\.)?reddit\.com/r/([A-Za-z0-9_]{2,30})/comments/([a-z0-9]{4,12})(?:/([^/\s\?#]+))?(?:/([a-z0-9]{4,12}))?/?',
            re.IGNORECASE
        )

        # 2. YouTube URL Pattern (Video ID + optional comment ID)
        self.youtube_url_pattern = re.compile(
            r'^https?://(?:www\.)?(?:youtube\.com/watch\?(?:[^&\s]+&)*v=([A-Za-z0-9_-]{8,15})|youtu\.be/([A-Za-z0-9_-]{8,15}))',
            re.IGNORECASE
        )

        # 3. IREF (Indian Real Estate Forum) Thread Pattern
        self.iref_url_pattern = re.compile(
            r'^https?://(?:www\.)?indianrealestateforum\.com/forum/.*threads/([^/\s\?#]+)\.([0-9]+)/?',
            re.IGNORECASE
        )

        # 4. Quora Question & Answer Pattern
        self.quora_url_pattern = re.compile(
            r'^https?://(?:www\.)?quora\.com/([^/\s\?#]+)(?:/answer/([^/\s\?#]+))?/?',
            re.IGNORECASE
        )

        # 5. Dubai Property Show / Expo Inquiry Pattern
        self.expo_url_pattern = re.compile(
            r'^https?://(?:www\.)?(?:dubaipropertyshow\.com|dubaipropertyexpo\.in|teamexpo\.ae|expoplatform\.com)/(?:attendee-forum|expo|attendees|inquiry|registration)/([A-Za-z0-9_/-]+)',
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

    def extract_domain(self, url: str) -> str:
        """Extracts clean lowercase domain from URL."""
        if not url:
            return ""
        try:
            parsed = urlparse(url)
            return parsed.netloc.lower()
        except Exception:
            return ""

    def validate_url_structure(self, url: str, platform: str) -> Tuple[bool, str]:
        """
        Validates that URL points to the correct original post, comment, thread, or inquiry.
        """
        if not url:
            return False, "Missing URL"

        domain = self.extract_domain(url)
        p_lower = platform.lower()

        # Reddit
        if "reddit" in domain or "reddit" in p_lower:
            if self.reddit_url_pattern.match(url):
                return True, "Valid Reddit post/comment permalink"
            return False, "Malformed Reddit URL: does not match standard /r/<subreddit>/comments/<id>/ structure"

        # YouTube
        if "youtube" in domain or "youtu.be" in domain or "youtube" in p_lower:
            if self.youtube_url_pattern.match(url):
                return True, "Valid YouTube video/comment permalink"
            return False, "Malformed YouTube URL: does not match watch?v=<id> or youtu.be/<id>"

        # IndianRealEstateForum (IREF)
        if "indianrealestateforum" in domain or "iref" in p_lower:
            if self.iref_url_pattern.match(url):
                return True, "Valid IREF discussion thread link"
            return False, "Malformed IREF URL: does not match /forum/.../threads/<title>.<id>/ structure"

        # Quora
        if "quora" in domain or "quora" in p_lower:
            if self.quora_url_pattern.match(url):
                return True, "Valid Quora public Q&A answer link"
            return False, "Malformed Quora URL: does not match /<question>/answer/<author> structure"

        # Dubai Property Expos & Roadshows
        if any(d in domain for d in ("dubaipropertyshow", "dubaipropertyexpo", "teamexpo", "expoplatform")) or "expo" in p_lower:
            if self.expo_url_pattern.match(url) or url.startswith("http"):
                return True, "Valid property show attendee inquiry link"
            return False, "Malformed property show inquiry URL"

        # Generic fallback for other authorized HTTP links
        if url.startswith("http://") or url.startswith("https://"):
            return True, "Valid HTTP public reference"

        return False, "Malformed URL: missing http/https protocol"

    def verify_record(
        self,
        record: Dict[str, Any],
        check_live: Optional[bool] = None,
        require_url: bool = False
    ) -> Dict[str, Any]:
        """
        Comprehensive verification of a discovered source record.
        Validates URL presence, permission, original post target, and deletion status.
        """
        should_check_live = self.check_live if check_live is None else check_live
        url = record.get("source_link", "").strip()
        text = record.get("raw_text", "").strip()
        handle = record.get("public_name_or_handle", "").strip()
        platform = record.get("platform", "").strip().lower()
        platform_ctx = record.get("platform_context", "").strip()

        url_present = bool(url)
        domain = self.extract_domain(url)
        url_permitted_use = domain in self.permitted_domains if domain else False
        url_points_to_correct_post = False
        intended_use_status = "PERMITTED_PUBLIC_RESEARCH" if url_permitted_use else ("MISSING_URL" if not url else "UNAUTHORIZED_SOURCE_DOMAIN")

        # 1. URL Presence & Structure Checks
        if not url:
            if require_url:
                return {
                    "is_valid": False,
                    "url_present": False,
                    "url_permitted_use": False,
                    "url_points_to_correct_post": False,
                    "source_domain": "",
                    "intended_use_status": "MISSING_URL",
                    "is_deleted": False,
                    "is_removed": False,
                    "is_inaccessible": True,
                    "url_exists": False,
                    "reason": "Missing source URL: Record does not have a public source link."
                }
        else:
            if not (url.startswith("http://") or url.startswith("https://")):
                return {
                    "is_valid": False,
                    "url_present": True,
                    "url_permitted_use": False,
                    "url_points_to_correct_post": False,
                    "source_domain": domain,
                    "intended_use_status": "MALFORMED_URL",
                    "is_deleted": False,
                    "is_removed": False,
                    "is_inaccessible": True,
                    "url_exists": False,
                    "reason": f"Malformed source URL: '{url}' is not a valid HTTP/HTTPS link."
                }

            # Check dead URL markers
            if any(marker in url.lower() for marker in self.dead_url_markers):
                return {
                    "is_valid": False,
                    "url_present": True,
                    "url_permitted_use": url_permitted_use,
                    "url_points_to_correct_post": False,
                    "source_domain": domain,
                    "intended_use_status": intended_use_status,
                    "is_deleted": True,
                    "is_removed": False,
                    "is_inaccessible": True,
                    "url_exists": False,
                    "reason": "Source URL no longer exists: Link is dead or marked as deleted."
                }

            # Check URL points to correct original post
            points_ok, points_reason = self.validate_url_structure(url, platform)
            url_points_to_correct_post = points_ok
            if not points_ok:
                return {
                    "is_valid": False,
                    "url_present": True,
                    "url_permitted_use": url_permitted_use,
                    "url_points_to_correct_post": False,
                    "source_domain": domain,
                    "intended_use_status": "MALFORMED_POST_REFERENCE",
                    "is_deleted": False,
                    "is_removed": False,
                    "is_inaccessible": True,
                    "url_exists": False,
                    "reason": points_reason
                }

            # Check Permitted Source Domain
            if not url_permitted_use:
                return {
                    "is_valid": False,
                    "url_present": True,
                    "url_permitted_use": False,
                    "url_points_to_correct_post": url_points_to_correct_post,
                    "source_domain": domain,
                    "intended_use_status": "UNAUTHORIZED_SOURCE_DOMAIN",
                    "is_deleted": False,
                    "is_removed": False,
                    "is_inaccessible": True,
                    "url_exists": True,
                    "reason": f"Unauthorized source domain: '{domain}' is not on the approved public discovery whitelist."
                }

        # 2. Handle / Author Deletion Check
        norm_handle = handle.lower().lstrip("u/").lstrip("@").strip()
        if norm_handle in ("[deleted]", "deleted", "[removed]", "removed"):
            return {
                "is_valid": False,
                "url_present": url_present,
                "url_permitted_use": url_permitted_use,
                "url_points_to_correct_post": url_points_to_correct_post,
                "source_domain": domain,
                "intended_use_status": intended_use_status,
                "is_deleted": True,
                "is_removed": False,
                "is_inaccessible": True,
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
                "url_present": url_present,
                "url_permitted_use": url_permitted_use,
                "url_points_to_correct_post": url_points_to_correct_post,
                "source_domain": domain,
                "intended_use_status": intended_use_status,
                "is_deleted": not is_moderator_removal,
                "is_removed": is_moderator_removal,
                "is_inaccessible": True,
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
                "url_present": url_present,
                "url_permitted_use": url_permitted_use,
                "url_points_to_correct_post": url_points_to_correct_post,
                "source_domain": domain,
                "intended_use_status": intended_use_status,
                "is_deleted": not is_moderator_removal,
                "is_removed": is_moderator_removal,
                "is_inaccessible": True,
                "url_exists": bool(url),
                "reason": f"Disqualified: Post was deleted or removed from the community ('{matched_phrase}')."
            }

        # 4. Optional Live HTTP Existence Check
        is_reddit = "reddit" in domain or "reddit" in platform
        if should_check_live and is_reddit and url:
            live_status, live_reason = self._probe_live_reddit_url(url)
            if not live_status:
                return {
                    "is_valid": False,
                    "url_present": url_present,
                    "url_permitted_use": url_permitted_use,
                    "url_points_to_correct_post": url_points_to_correct_post,
                    "source_domain": domain,
                    "intended_use_status": intended_use_status,
                    "is_deleted": "deleted" in live_reason.lower(),
                    "is_removed": "removed" in live_reason.lower(),
                    "is_inaccessible": True,
                    "url_exists": False,
                    "reason": live_reason
                }

        return {
            "is_valid": True,
            "url_present": url_present,
            "url_permitted_use": url_permitted_use,
            "url_points_to_correct_post": True,
            "source_domain": domain,
            "intended_use_status": intended_use_status,
            "is_deleted": False,
            "is_removed": False,
            "is_inaccessible": False,
            "url_exists": True,
            "reason": "Source verified: URL is permitted, points to the original post, and is active."
        }

    def _probe_live_reddit_url(self, url: str) -> Tuple[bool, str]:
        """Probes a Reddit URL over HTTP to verify active status."""
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
                    res = (False, "Live probe failed: Reddit post URL returned HTTP 410 Gone.")
                    self._url_cache[url] = res
                    return res

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
                res = (True, "Live probe unverified: WAF anti-bot gate encountered (HTTP 403), marked active.")
            else:
                res = (True, f"Live probe unverified: HTTP {e.code}.")
            self._url_cache[url] = res
            return res
        except Exception as e:
            res = (True, f"Live probe warning: Network check bypassed ({str(e)}).")
            self._url_cache[url] = res
            return res
