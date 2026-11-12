"""
Intent classification and lead qualification engine for Dubai Real Estate prospects.
Calculates qualification score, categorizes status, and documents clear rationale.
"""

import re
from datetime import datetime, date
from typing import Dict, List, Tuple, Optional
from workflow.processors.source_verifier import SourceVerifier
from workflow.config import (
    DUBAI_LOCALITIES,
    DUBAI_DEVELOPERS,
    BUYING_INTENT_KEYWORDS,
    NEGATIVE_KEYWORDS,
    SCORE_EXPLICIT_BUDGET,
    SCORE_EXPLICIT_TIMELINE,
    SCORE_SPECIFIC_LOCALITY,
    SCORE_SPECIFIC_DEVELOPER,
    SCORE_VERIFIED_GEO_HIGH,
    SCORE_VERIFIED_GEO_MEDIUM,
    SCORE_REGULATORY_LRS,
    SCORE_INVESTMENT_YIELD,
    QUALIFIED_SCORE_THRESHOLD,
    MAX_FRESHNESS_DAYS,
    ENFORCE_FRESHNESS,
    PENALTY_STALE_SIGNAL,
    VERIFY_SOURCE_AVAILABILITY
)


class IntentClassifier:
    def __init__(
        self,
        max_freshness_days: int = MAX_FRESHNESS_DAYS,
        enforce_freshness: bool = ENFORCE_FRESHNESS,
        qualified_threshold: int = QUALIFIED_SCORE_THRESHOLD,
        verify_sources: bool = VERIFY_SOURCE_AVAILABILITY,
        source_verifier: Optional[SourceVerifier] = None
    ):
        self.max_freshness_days = max_freshness_days
        self.enforce_freshness = enforce_freshness
        self.qualified_threshold = qualified_threshold
        self.verify_sources = verify_sources
        self.source_verifier = source_verifier or SourceVerifier()

        # Budget patterns (AED, INR Cr/Lakh, USD)
        self.budget_pattern = re.compile(
            r'(\b(?:aed|inr|rs\.?|₹|\$)\s*[\d\.]+\s*(?:m|million|cr|crore|crores|l|lakh|lakhs|k)?\b|'
            r'[\d\.]+\s*(?:cr|crore|crores|aed|million\s*aed|m\s*aed|lakh|lakhs))',
            re.IGNORECASE
        )

        # Timeline patterns
        self.timeline_pattern = re.compile(
            r'\b(immediate|immediately|next\s*month|this\s*year|within\s*\d+\s*(?:months?|weeks?)|'
            r'by\s*(?:q[1-4]|end\s*of\s*year|202[4-7]|december|january|march)|ready\s*to\s*move|soon)\b',
            re.IGNORECASE
        )

        # Unit type patterns
        self.unit_pattern = re.compile(
            r'\b(\d\s*bhk|studio|1\s*bed|2\s*bed|3\s*bed|villa|townhouse|penthouse|apartment|flat)\b',
            re.IGNORECASE
        )

        # Compile locality and developer patterns
        self.locality_pattern = re.compile(
            r'\b(' + '|'.join(re.escape(loc) for loc in DUBAI_LOCALITIES) + r')\b',
            re.IGNORECASE
        )
        self.developer_pattern = re.compile(
            r'\b(' + '|'.join(re.escape(dev) for dev in DUBAI_DEVELOPERS) + r')\b',
            re.IGNORECASE
        )

        # Negative / broker / job patterns
        self.negative_pattern = re.compile(
            r'(' + '|'.join(re.escape(neg) for neg in NEGATIVE_KEYWORDS) + r')',
            re.IGNORECASE
        )

    def classify_lead(
        self,
        text: str,
        geo_info: Dict[str, any],
        platform_context: str = "",
        signal_date_str: str = "",
        reference_date: Optional[date] = None,
        source_link: str = "",
        public_name_or_handle: str = "",
        platform: str = "",
        check_live: Optional[bool] = None
    ) -> Dict[str, any]:
        """
        Classifies candidate lead text into Strong Signal, Needs Validation, or Reject.
        Enforces strict 6-month freshness gate and verifies source existence (excluding deleted/removed posts).
        Returns detailed scoring, reasons, and unverified data points.
        """
        full_text = f"{text} {platform_context}".strip()
        reasons = []
        unverified = []
        score = 0

        # Freshness Gate Calculation (Must be <= self.max_freshness_days)
        age_days = None
        is_fresh = True
        if signal_date_str:
            try:
                sig_date = datetime.strptime(signal_date_str.strip(), "%Y-%m-%d").date()
                ref = reference_date or date.today()
                age_days = (ref - sig_date).days
                if age_days < 0:
                    age_days = 0  # Timezone or clock offset tolerance
                if age_days > self.max_freshness_days:
                    is_fresh = False
            except Exception:
                pass

        # 0. Source URL & Community Existence Check (Reddit deletion & removal validation)
        source_verification = None
        if self.verify_sources and (source_link or text or public_name_or_handle):
            source_verification = self.source_verifier.verify_record({
                "source_link": source_link,
                "raw_text": text,
                "public_name_or_handle": public_name_or_handle,
                "platform": platform,
                "platform_context": platform_context
            }, check_live=check_live)

            if not source_verification["is_valid"]:
                return {
                    "qualification_status": "Reject",
                    "qualification_reason": f"Disqualified: {source_verification['reason']}",
                    "unverified_information": "N/A - source deleted or removed from community.",
                    "ticket_size_budget": "N/A",
                    "preferred_areas": "N/A",
                    "score": 0,
                    "signal_age_days": age_days if age_days is not None else "Unverified",
                    "is_fresh": is_fresh,
                    "is_qualified": False,
                    "source_verification": source_verification,
                    "location_verification_status": geo_info.get("location_verification_status", "LOCATION_UNVERIFIED"),
                    "location_evidence_text": geo_info.get("location_evidence_text", "None - unverified"),
                    "location_evidence_url": geo_info.get("location_evidence_url", source_link)
                }

        # 1. Negative Filter: Check for broker / seller / job hunter behavior
        negative_match = self.negative_pattern.search(full_text)
        if negative_match:
            matched_flag = negative_match.group(0)
            return {
                "qualification_status": "Reject",
                "qualification_reason": f"Disqualified: Identified as property seller/broker or job seeker ('{matched_flag}').",
                "unverified_information": "N/A - record rejected.",
                "ticket_size_budget": "N/A",
                "preferred_areas": "N/A",
                "score": 0,
                "signal_age_days": age_days if age_days is not None else "Unverified",
                "is_fresh": is_fresh,
                "is_qualified": False,
                "source_verification": source_verification,
                "location_verification_status": geo_info.get("location_verification_status", "LOCATION_UNVERIFIED"),
                "location_evidence_text": geo_info.get("location_evidence_text", "None - unverified"),
                "location_evidence_url": geo_info.get("location_evidence_url", source_link)
            }

        # 2. Extract Budget / Ticket Size
        budget_matches = self.budget_pattern.findall(full_text)
        extracted_budget = None
        if budget_matches:
            # If both INR and AED are mentioned, combine for richer buyer profile
            if len(budget_matches) >= 2 and any("aed" in b.lower() for b in budget_matches[:2]) and any("cr" in b.lower() or "₹" in b or "inr" in b.lower() for b in budget_matches[:2]):
                extracted_budget = f"{budget_matches[0].strip()} (~{budget_matches[1].strip()})"
            else:
                extracted_budget = budget_matches[0].strip()
            score += SCORE_EXPLICIT_BUDGET
            reasons.append(f"Explicit financial budget stated ({extracted_budget})")
        else:
            unverified.append("Purchase budget / ticket size not specified")

        # 3. Extract Timeline
        timeline_match = self.timeline_pattern.search(full_text)
        extracted_timeline = None
        if timeline_match:
            extracted_timeline = timeline_match.group(0).strip()
            score += SCORE_EXPLICIT_TIMELINE
            reasons.append(f"Concrete purchase timeline stated ({extracted_timeline})")
        else:
            unverified.append("Investment timeline undefined")

        # 4. Extract Dubai Localities and Developers
        localities_found = list(set([m.title() for m in self.locality_pattern.findall(full_text)]))
        developers_found = list(set([m.title() for m in self.developer_pattern.findall(full_text)]))
        
        preferred_areas = []
        if localities_found:
            score += SCORE_SPECIFIC_LOCALITY
            preferred_areas.extend(localities_found)
            reasons.append(f"Specific Dubai micro-market identified ({', '.join(localities_found[:2])})")
        if developers_found:
            score += SCORE_SPECIFIC_DEVELOPER
            preferred_areas.extend([f"Developer: {d}" for d in developers_found])
            reasons.append(f"Specific developer identified ({', '.join(developers_found[:2])})")

        if not preferred_areas:
            unverified.append("Specific Dubai community or project preference not specified")

        # 5. Extract Unit Preference
        unit_match = self.unit_pattern.search(full_text)
        if unit_match:
            reasons.append(f"Unit configuration identified ({unit_match.group(0).upper()})")

        # 6. Check Regulatory / LRS Inquiry
        if re.search(r'\b(lrs|remittance|tcs|tax|fema|rbi)\b', full_text, re.IGNORECASE):
            score += SCORE_REGULATORY_LRS
            reasons.append("Active inquiry on India-to-Dubai capital remittance (LRS/TCS)")

        # 7. Check General Buying & Yield Intent
        if re.search(r'\b(rental yields?|roi|cashflow|golden visa|off-plan|payment plans?)\b', full_text, re.IGNORECASE):
            score += SCORE_INVESTMENT_YIELD
            reasons.append("Evaluated cashflow/ROI, Golden Visa eligibility, or payment plan structures")

        # 8. Cross-reference Geo Evidence
        loc_status = geo_info.get("location_verification_status")
        if not loc_status:
            if geo_info.get("confidence") == "HIGH":
                loc_status = "CURRENT_RESIDENT"
            elif geo_info.get("confidence") == "LOW":
                loc_status = "ORIGIN_ONLY"
            else:
                loc_status = "LOCATION_UNVERIFIED"

        if loc_status == "CURRENT_RESIDENT":
            score += SCORE_VERIFIED_GEO_HIGH
            reasons.append(f"Verified current residence in {geo_info.get('city_state')} ('{geo_info.get('location_evidence_text')}')")
        elif loc_status == "ORIGIN_ONLY":
            reasons.append(f"Origin indicated in {geo_info.get('city_state')}; current residence unverified")
            unverified.append(f"Origin in {geo_info.get('city_state')}, but current South Indian residence is unverified")
        elif loc_status == "OUTSIDE_TARGET":
            return {
                "qualification_status": "Reject",
                "qualification_reason": f"Disqualified: Explicit current residence is outside target geography ({geo_info.get('location_evidence_text', 'Outside South India')}).",
                "unverified_information": "N/A - record rejected.",
                "ticket_size_budget": "N/A",
                "preferred_areas": "N/A",
                "score": 0,
                "signal_age_days": age_days if age_days is not None else "Unverified",
                "is_fresh": is_fresh,
                "is_qualified": False,
                "source_verification": source_verification,
                "location_verification_status": "OUTSIDE_TARGET",
                "location_evidence_text": geo_info.get("location_evidence_text", "None"),
                "location_evidence_url": geo_info.get("location_evidence_url", source_link)
            }
        else:
            unverified.append("Current residence in target South Indian states is unverified from public text")

        # 9. Apply Freshness Gate & Stale Signal Penalty
        if self.enforce_freshness and not is_fresh and age_days is not None:
            score = max(0, score - PENALTY_STALE_SIGNAL)
            reasons.append(f"Freshness limit exceeded (-{PENALTY_STALE_SIGNAL} pts penalty): Signal is {age_days} days old (> {self.max_freshness_days} days threshold)")
            unverified.append(f"Signal age ({age_days} days) exceeds {self.max_freshness_days}-day freshness threshold; active buying readiness unconfirmed")

        # Clamp normalized score strictly to [0, 100]
        score = max(0, min(100, score))

        # Determine Final Status based on score, freshness, and strict geographic verification
        # Rule 5: If a prospect has clear buying intent but unverified location, classify as NEEDS_VALIDATION, not REJECT
        has_buying_intent = (
            extracted_budget is not None or
            extracted_timeline is not None or
            bool(preferred_areas) or
            score >= 25
        )

        if loc_status == "OUTSIDE_TARGET":
            status = "Reject"
            reason_str = f"Disqualified: Explicit current residence is outside target geography ({geo_info.get('location_evidence_text', 'Outside South India')})."
        elif score > self.qualified_threshold:
            # Acceptance Criterion 1: No Strong Signal lead has unverified current residence
            if loc_status == "CURRENT_RESIDENT":
                status = "Strong Signal"
                fresh_badge = f"Verified fresh ({age_days} days old <= {self.max_freshness_days} days)" if age_days is not None else "Freshness verified"
                reason_str = f"Qualified [{score}/100 pts, {fresh_badge}]: " + "; ".join(reasons)
            else:
                # Clear buying intent, but unverified South Indian current residence -> Must be Needs Validation
                status = "Needs Validation"
                reason_str = (
                    f"Needs Validation [{score}/100 pts, High Buying Intent]: "
                    f"Strong purchase signals verified, but South Indian current residence is {loc_status.lower().replace('_', ' ')} "
                    f"(requires address verification before sales outreach)."
                )
        elif score >= 25 or (has_buying_intent and loc_status in ("LOCATION_UNVERIFIED", "ORIGIN_ONLY")):
            status = "Needs Validation"
            reason_str = f"Needs Validation [{score}/100 pts]: " + "; ".join(reasons)
        else:
            status = "Reject"
            reason_str = f"Rejected [{score}/100 pts]: " + ("; ".join(reasons) if reasons else "Score below threshold")

        is_qualified = (status == "Strong Signal" and score > self.qualified_threshold)

        return {
            "qualification_status": status,
            "qualification_reason": reason_str,
            "unverified_information": "; ".join(unverified) if unverified else "None - key criteria verified",
            "ticket_size_budget": extracted_budget or "Not explicitly stated",
            "preferred_areas": ", ".join(preferred_areas) if preferred_areas else "General Dubai Property",
            "score": score,
            "is_qualified": is_qualified,
            "signal_age_days": age_days if age_days is not None else "Unverified",
            "is_fresh": is_fresh,
            "source_verification": source_verification,
            "location_verification_status": loc_status,
            "location_evidence_text": geo_info.get("location_evidence_text", "None - unverified"),
            "location_evidence_url": geo_info.get("location_evidence_url", source_link)
        }
