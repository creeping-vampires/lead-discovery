"""
Intent classification and lead qualification engine for Dubai Real Estate prospects.
Implements mandatory evidence gates and a 100-point weighted scoring model:
1. Explicit Personal Purchase Intent (30 pts)
2. Purchase Readiness (20 pts)
3. Budget or Financing Requirements (15 pts)
4. Purchase Timeline (15 pts)
5. Specific Project / Property Requirements (10 pts)
6. Freshness (10 pts)

Mandatory Strong Signal Gates (ALL must pass):
- Explicit first-person purchase/investment interest
- Verifiable source URL and original statement
- Verified current residence in target South Indian states (CURRENT_RESIDENT)
- Buying-intent signal dated within last 180 days (<= 180 days)
- No confirmed broker, agent, spam, or promotional activity
"""

import re
from datetime import datetime, date
from typing import Dict, List, Tuple, Optional, Any
from workflow.processors.source_verifier import SourceVerifier
from workflow.config import (
    DUBAI_LOCALITIES,
    DUBAI_DEVELOPERS,
    BUYING_INTENT_KEYWORDS,
    NEGATIVE_KEYWORDS,
    SCORE_PERSONAL_INTENT,
    SCORE_PURCHASE_READINESS,
    SCORE_BUDGET_FINANCING,
    SCORE_PURCHASE_TIMELINE,
    SCORE_PROJECT_REQUIREMENTS,
    SCORE_FRESHNESS,
    STRONG_SIGNAL_THRESHOLD,
    MAX_FRESHNESS_DAYS,
    ENFORCE_FRESHNESS,
    VERIFY_SOURCE_AVAILABILITY
)


class IntentClassifier:
    def __init__(
        self,
        max_freshness_days: int = MAX_FRESHNESS_DAYS,
        enforce_freshness: bool = ENFORCE_FRESHNESS,
        strong_threshold: int = STRONG_SIGNAL_THRESHOLD,
        verify_sources: bool = VERIFY_SOURCE_AVAILABILITY,
        source_verifier: Optional[SourceVerifier] = None,
        qualified_threshold: Optional[int] = None
    ):
        self.max_freshness_days = max_freshness_days
        self.enforce_freshness = enforce_freshness
        self.strong_threshold = strong_threshold if qualified_threshold is None else qualified_threshold
        self.verify_sources = verify_sources
        self.source_verifier = source_verifier or SourceVerifier()

        # 1. Component 1: Explicit First-Person Purchase Intent Pattern
        # Must be personal commitment / buying statement; general questions or profession alone do NOT match
        self.personal_intent_pattern = re.compile(
            r'\b(?:'
            r'(?:i(?:(?:\s*am|\'m))?|we(?:(?:\s*are|\'re))?|myself)\s+'
            r'(?:(?:actively|seriously|currently|now|definitely|personally)\s+)?'
            r'(?:'
            r'(?:looking|planning|want|hoping|aiming|ready|decided|preparing|in\s+process|shortlisting|scheduled)\s+to\s+(?:buy|purchase|invest|acquire|book|close|reinvest|deploy)|'
            r'(?:buying|purchasing|investing|acquiring|booking|closing|reinvesting|deploying)|'
            r'(?:will\s+(?:buy|purchase|invest|acquire|book))'
            r')|'
            r'(?:actively|seriously)\s+(?:looking|planning)\s+to\s+(?:buy|purchase|invest|acquire|book)|'
            r'ready\s+to\s+(?:buy|purchase|invest|book|sign)|'
            r'planning\s+to\s+(?:buy|purchase|invest|acquire|book|remit|finalize)|'
            r'looking\s+to\s+(?:buy|purchase|invest|acquire|book|reinvest)|'
            r'looking\s+into\s+purchasing|'
            r'in\s+process\s+of\s+buying|'
            r'booked\s+a\s+token|'
            r'initiated\s+(?:20%|\d+%)?\s*down\s*payment|'
            r'total\s+investment\s+planned\s+is|'
            r'want\s+to\s+(?:buy|purchase|invest|reinvest|acquire|book)|'
            r'want\s+something\s+ready\s+to\s+move|'
            r'seriously\s+considering\s+shifting\s+my\s+capital'
            r')\b',
            re.IGNORECASE
        )

        # 2. Component 2: Purchase Readiness (Concrete transactional steps)
        self.readiness_pattern = re.compile(
            r'\b(?:'
            r'token|down\s*payment|booking\s*amount|deposit|booking\s*fee|'
            r'remit(?:ting|tance)?(?:\s+funds)?\s+under\s+lrs|form\s*15ca/?cb|lrs\s+(?:transfer|clearance)|'
            r'tcs\s+deducted|rbi\s+permission|escrow\s+(?:verification|remittance)|fema\s+compliance|'
            r'ready\s+to\s+sign|sign(?:ing)?\s+(?:agreement|contract|spa)|issue\s+spa|sales\s+contract|'
            r'travel(?:ing)?\s+to\s+dubai(?:\s+next|\s+this)?\s+(?:week|month)\s+to\s+inspect|inspect\s+ready\s+units|'
            r'selling(?:\s+an?)?\s+(?:inherited\s+)?(?:plot|property|flat|asset)|'
            r'liquid\s+capital\s+of|liquid\s+surplus\s+of|funds\s+ready\s+in\s+nre|finalize\s+booking\s+next\s+month'
            r')\b',
            re.IGNORECASE
        )

        # 3. Component 3: Budget or Financing Requirements
        self.budget_pattern = re.compile(
            r'(\b(?:aed|inr|rs\.?|₹|\$)\s*[\d\.]+\s*(?:m|million|cr|crore|crores|l|lakh|lakhs|k)?\b|'
            r'[\d\.]+\s*(?:cr|crore|crores|aed|million\s*aed|m\s*aed|lakh|lakhs)|'
            r'\b\d+%\s*(?:monthly|down\s*payment|post[- ]handover)\b|'
            r'\b(?:\d+[-/]\d+)?\s*payment\s*plan\b|'
            r'\bpost[- ]handover\b)',
            re.IGNORECASE
        )

        # 4. Component 4: Purchase Timeline Horizon
        self.timeline_pattern = re.compile(
            r'\b(immediate|immediately|next\s*month|this\s*month|this\s*quarter|this\s*year|within\s*\d+\s*(?:months?|weeks?|days?)|'
            r'by\s*(?:q[1-4]|end\s*of\s*(?:the\s*)?year|202[4-7]|december|january|february|march|april|may|june|july|august|september|october|november)|'
            r'ready\s*to\s*move)\b',
            re.IGNORECASE
        )

        # 5. Component 5: Specific Project / Property Requirements
        self.locality_pattern = re.compile(
            r'\b(' + '|'.join(re.escape(loc) for loc in DUBAI_LOCALITIES) + r')\b',
            re.IGNORECASE
        )
        self.developer_pattern = re.compile(
            r'\b(' + '|'.join(re.escape(dev) for dev in DUBAI_DEVELOPERS) + r')\b',
            re.IGNORECASE
        )
        self.unit_pattern = re.compile(
            r'\b(\d\s*bhk|studio|1\s*bed|2\s*bed|3\s*bed|villa|townhouse|penthouse|apartment|flat|off-plan|ready\s+unit)\b',
            re.IGNORECASE
        )

        # General exploratory / investment research patterns (used for plausible buyer classification)
        self.exploratory_intent_pattern = re.compile(
            r'\b(rental\s*yields?|rental\s*returns?|roi|cashflow|golden\s*visa|off-plan|payment\s*plans?|'
            r'lrs|remittance|tcs|tax|dld|escrow|dubai\s*property|dubai\s*real\s*estate)\b',
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
        geo_info: Dict[str, Any],
        platform_context: str = "",
        signal_date_str: str = "",
        reference_date: Optional[date] = None,
        source_link: str = "",
        public_name_or_handle: str = "",
        platform: str = "",
        check_live: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Classifies lead using mandatory evidence gates and 100-point weighted scoring model.
        Returns explainable component scores, evidence snippets, reason codes, and gates.
        """
        full_text = f"{text} {platform_context}".strip()
        ref = reference_date or date.today()

        # Extract Geographic Status
        loc_status = geo_info.get("location_verification_status")
        if not loc_status:
            conf = geo_info.get("confidence")
            if conf == "HIGH":
                loc_status = "CURRENT_RESIDENT"
            elif conf == "LOW":
                loc_status = "ORIGIN_ONLY"
            else:
                loc_status = "LOCATION_UNVERIFIED"

        # Calculate Signal Age & Freshness
        age_days = None
        is_fresh = False
        if signal_date_str:
            try:
                sig_date = datetime.strptime(signal_date_str.strip(), "%Y-%m-%d").date()
                age_days = (ref - sig_date).days
                if age_days < 0:
                    age_days = 0
                if age_days <= self.max_freshness_days:
                    is_fresh = True
            except Exception:
                pass

        # ----------------------------------------------------------------------
        # Mandatory Gate Checks
        # ----------------------------------------------------------------------

        # Gate 2: Verifiable Source URL & Community Existence Check
        source_verification = None
        gate_verifiable_source = False
        if self.verify_sources and (source_link or text or public_name_or_handle):
            source_verification = self.source_verifier.verify_record({
                "source_link": source_link,
                "raw_text": text,
                "public_name_or_handle": public_name_or_handle,
                "platform": platform,
                "platform_context": platform_context
            }, check_live=check_live)

            gate_verifiable_source = bool(source_verification["is_valid"] and source_link and text.strip())

            if not source_verification["is_valid"]:
                return self._build_rejected_response(
                    reason=f"Disqualified: {source_verification['reason']}",
                    reason_code="DISQUALIFIED_SOURCE_DELETED_OR_INVALID",
                    unverified="N/A - source post or comment was deleted or removed from community.",
                    geo_info=geo_info,
                    source_link=source_link,
                    source_verification=source_verification,
                    age_days=age_days,
                    is_fresh=is_fresh,
                    loc_status=loc_status
                )
        else:
            gate_verifiable_source = bool(source_link and text.strip())

        # Gate 5: No Confirmed Broker, Agent, Spam, or Job Hunter
        negative_match = self.negative_pattern.search(full_text)
        gate_no_broker = (negative_match is None)
        if not gate_no_broker:
            matched_flag = negative_match.group(0)
            return self._build_rejected_response(
                reason=f"Disqualified: Identified as property seller/broker or job seeker ('{matched_flag}').",
                reason_code="DISQUALIFIED_BROKER_PROMOTER_SPAM",
                unverified="N/A - record rejected.",
                geo_info=geo_info,
                source_link=source_link,
                source_verification=source_verification,
                age_days=age_days,
                is_fresh=is_fresh,
                loc_status=loc_status
            )

        # Gate 3: Verified Current Resident in Target Geography
        gate_current_resident = (loc_status == "CURRENT_RESIDENT")
        if loc_status == "OUTSIDE_TARGET":
            return self._build_rejected_response(
                reason=f"Disqualified: Explicit current residence is outside target geography ({geo_info.get('location_evidence_text', 'Outside South India')}).",
                reason_code="DISQUALIFIED_OUTSIDE_TARGET",
                unverified="N/A - record rejected.",
                geo_info=geo_info,
                source_link=source_link,
                source_verification=source_verification,
                age_days=age_days,
                is_fresh=is_fresh,
                loc_status="OUTSIDE_TARGET"
            )

        # Gate 4: Buying-intent Signal Dated Within 180 Days
        gate_freshness = (is_fresh is True and age_days is not None and age_days <= self.max_freshness_days)

        # ----------------------------------------------------------------------
        # 6-Component Weighted Scoring (100 Points Scale)
        # ----------------------------------------------------------------------
        unverified_items = []
        positive_reasons = []

        # Component 1: Explicit Personal Purchase Intent (30 pts)
        intent_match = self.personal_intent_pattern.search(full_text)
        if intent_match:
            score_intent = SCORE_PERSONAL_INTENT
            intent_evidence = intent_match.group(0).strip()
            intent_reason_code = "EXPLICIT_PERSONAL_INTENT"
            positive_reasons.append(f"Explicit personal purchase intent stated ('{intent_evidence}')")
            gate_personal_intent = True
        else:
            score_intent = 0
            intent_evidence = "None - general inquiry, ROI research, or visa question only"
            intent_reason_code = "NO_EXPLICIT_PERSONAL_INTENT"
            unverified_items.append("Explicit first-person purchase intent not stated")
            gate_personal_intent = False

        # Component 2: Purchase Readiness (20 pts)
        readiness_match = self.readiness_pattern.search(full_text)
        if readiness_match:
            score_readiness = SCORE_PURCHASE_READINESS
            readiness_evidence = readiness_match.group(0).strip()
            readiness_reason_code = "PURCHASE_READINESS_CONFIRMED"
            positive_reasons.append(f"Concrete purchase readiness step verified ('{readiness_evidence}')")
        else:
            score_readiness = 0
            readiness_evidence = "None - no transactional readiness action"
            readiness_reason_code = "NO_READINESS_EVIDENCE"
            unverified_items.append("Concrete purchase readiness step (token/remittance/SPA) unconfirmed")

        # Component 3: Budget or Financing Requirements (15 pts)
        budget_matches = self.budget_pattern.findall(full_text)
        if budget_matches:
            score_budget = SCORE_BUDGET_FINANCING
            # Distinct budget terms
            extracted_budget = ", ".join(list(dict.fromkeys([b.strip() for b in budget_matches]))[:2])
            budget_evidence = extracted_budget
            budget_reason_code = "BUDGET_OR_FINANCING_SPECIFIED"
            positive_reasons.append(f"Explicit financial budget or payment plan stated ({extracted_budget})")
        else:
            score_budget = 0
            extracted_budget = "Not explicitly stated"
            budget_evidence = "None - budget not specified"
            budget_reason_code = "BUDGET_MISSING"
            unverified_items.append("Purchase budget / financing requirements not specified")

        # Component 4: Purchase Timeline (15 pts)
        timeline_match = self.timeline_pattern.search(full_text)
        if timeline_match:
            score_timeline = SCORE_PURCHASE_TIMELINE
            extracted_timeline = timeline_match.group(0).strip()
            timeline_evidence = extracted_timeline
            timeline_reason_code = "TIMELINE_SPECIFIED"
            positive_reasons.append(f"Concrete purchase timeline stated ({extracted_timeline})")
        else:
            score_timeline = 0
            extracted_timeline = "Not explicitly stated"
            timeline_evidence = "None - timeline undefined"
            timeline_reason_code = "TIMELINE_MISSING"
            unverified_items.append("Purchase timeline horizon undefined")

        # Component 5: Specific Project / Property Requirements (10 pts)
        localities_found = list(dict.fromkeys([m.title() for m in self.locality_pattern.findall(full_text)]))
        developers_found = list(dict.fromkeys([m.title() for m in self.developer_pattern.findall(full_text)]))
        units_found = list(dict.fromkeys([m.upper() for m in self.unit_pattern.findall(full_text)]))

        preferred_areas = []
        if localities_found:
            preferred_areas.extend(localities_found)
        if developers_found:
            preferred_areas.extend([f"Developer: {d}" for d in developers_found])
        if units_found:
            preferred_areas.extend([f"Unit: {u}" for u in units_found])

        if preferred_areas:
            score_project = SCORE_PROJECT_REQUIREMENTS
            project_evidence = "; ".join(preferred_areas[:3])
            project_reason_code = "PROJECT_REQUIREMENTS_SPECIFIED"
            positive_reasons.append(f"Specific project/property requirements identified ({project_evidence})")
        else:
            score_project = 0
            project_evidence = "None - general Dubai property"
            project_reason_code = "PROJECT_REQUIREMENTS_UNSPECIFIED"
            unverified_items.append("Specific Dubai community or developer preference not specified")

        # Component 6: Freshness (10 pts)
        if gate_freshness:
            score_freshness = SCORE_FRESHNESS
            freshness_evidence = f"Signal date {signal_date_str} ({age_days} days old <= {self.max_freshness_days} days)"
            freshness_reason_code = "SIGNAL_FRESH_180D"
            positive_reasons.append(f"Recent buying signal ({age_days} days old <= 180 days)")
        else:
            score_freshness = 0
            if age_days is not None:
                freshness_evidence = f"Signal age ({age_days} days) exceeds {self.max_freshness_days}-day limit"
                freshness_reason_code = "SIGNAL_STALE_EXCEEDS_180D"
                unverified_items.append(f"Signal age ({age_days} days) exceeds 180-day freshness limit")
            else:
                freshness_evidence = "Signal date unverified or missing"
                freshness_reason_code = "SIGNAL_DATE_MISSING"
                unverified_items.append("Signal date unverified")

        # Location verification check notes
        if loc_status == "CURRENT_RESIDENT":
            positive_reasons.append(f"Verified current residence in {geo_info.get('city_state')} ('{geo_info.get('location_evidence_text')}')")
        elif loc_status == "ORIGIN_ONLY":
            unverified_items.append(f"Origin indicated in {geo_info.get('city_state')}, but current South Indian residence is unverified")
        else:
            unverified_items.append("Current residence in target South Indian states is unverified from public text")

        # Compute Total Weighted Score
        total_score = (
            score_intent +
            score_readiness +
            score_budget +
            score_timeline +
            score_project +
            score_freshness
        )
        total_score = max(0, min(100, total_score))

        # Check All 5 Mandatory Gates
        all_mandatory_gates_pass = all([
            gate_personal_intent,
            gate_verifiable_source,
            gate_current_resident,
            gate_freshness,
            gate_no_broker
        ])

        # ----------------------------------------------------------------------
        # Classification Decision
        # ----------------------------------------------------------------------
        has_exploratory_interest = bool(self.exploratory_intent_pattern.search(full_text))
        is_plausible_buyer = (
            gate_personal_intent or
            score_readiness > 0 or
            score_budget > 0 or
            (has_exploratory_interest and total_score >= 20) or
            total_score >= 25
        )

        if all_mandatory_gates_pass and total_score >= self.strong_threshold:
            status = "Strong Signal"
            status_code = "STRONG_SIGNAL"
            reason_str = (
                f"Qualified Strong Signal [{total_score}/100 pts, All 5 Mandatory Gates Passed]: " +
                "; ".join(positive_reasons)
            )
        elif is_plausible_buyer:
            status = "Needs Validation"
            status_code = "NEEDS_VALIDATION"
            unverified_str = "; ".join(unverified_items) if unverified_items else "Score below 75 threshold"
            reason_str = (
                f"Needs Validation [{total_score}/100 pts, Plausible Buyer]: "
                f"Requires verification ({unverified_str}). "
                f"Verified signals: " + ("; ".join(positive_reasons) if positive_reasons else "Initial enquiry")
            )
        else:
            status = "Reject"
            status_code = "REJECT"
            reason_str = (
                f"Rejected [{total_score}/100 pts]: No meaningful buying intent or irrelevant enquiry. " +
                ("; ".join(positive_reasons) if positive_reasons else "Score below qualification baseline")
            )

        is_qualified = (status == "Strong Signal" and total_score >= self.strong_threshold)

        return {
            "qualification_status": status,
            "qualification_status_code": status_code,
            "qualification_reason": reason_str,
            "unverified_information": "; ".join(unverified_items) if unverified_items else "None - all key requirements verified",
            "score": total_score,
            "is_qualified": is_qualified,
            "ticket_size_budget": extracted_budget,
            "preferred_areas": ", ".join(preferred_areas) if preferred_areas else "General Dubai Property",
            "signal_age_days": age_days if age_days is not None else "Unverified",
            "is_fresh": is_fresh,
            "source_verification": source_verification,
            "location_verification_status": loc_status,
            "location_evidence_text": geo_info.get("location_evidence_text", "None - unverified"),
            "location_evidence_url": geo_info.get("location_evidence_url", source_link),
            "mandatory_gates": {
                "gate_personal_intent": gate_personal_intent,
                "gate_verifiable_source": gate_verifiable_source,
                "gate_current_resident": gate_current_resident,
                "gate_freshness": gate_freshness,
                "gate_no_broker": gate_no_broker,
                "all_mandatory_gates_pass": all_mandatory_gates_pass
            },
            "scoring_breakdown": {
                "explicit_personal_purchase_intent": score_intent,
                "purchase_readiness": score_readiness,
                "budget_or_financing_requirements": score_budget,
                "purchase_timeline": score_timeline,
                "specific_project_property_requirements": score_project,
                "freshness": score_freshness
            },
            "component_evidence": {
                "intent_evidence": intent_evidence,
                "readiness_evidence": readiness_evidence,
                "budget_evidence": budget_evidence,
                "timeline_evidence": timeline_evidence,
                "project_evidence": project_evidence,
                "freshness_evidence": freshness_evidence
            },
            "component_reason_codes": {
                "intent_reason_code": intent_reason_code,
                "readiness_reason_code": readiness_reason_code,
                "budget_reason_code": budget_reason_code,
                "timeline_reason_code": timeline_reason_code,
                "project_reason_code": project_reason_code,
                "freshness_reason_code": freshness_reason_code
            }
        }

    def _build_rejected_response(
        self,
        reason: str,
        reason_code: str,
        unverified: str,
        geo_info: Dict[str, Any],
        source_link: str,
        source_verification: Optional[Dict[str, Any]],
        age_days: Optional[int],
        is_fresh: bool,
        loc_status: str
    ) -> Dict[str, Any]:
        """Helper to return a standardized rejection payload."""
        return {
            "qualification_status": "Reject",
            "qualification_status_code": "REJECT",
            "qualification_reason": reason,
            "unverified_information": unverified,
            "score": 0,
            "is_qualified": False,
            "ticket_size_budget": "N/A",
            "preferred_areas": "N/A",
            "signal_age_days": age_days if age_days is not None else "Unverified",
            "is_fresh": is_fresh,
            "source_verification": source_verification,
            "location_verification_status": loc_status,
            "location_evidence_text": geo_info.get("location_evidence_text", "None - unverified"),
            "location_evidence_url": geo_info.get("location_evidence_url", source_link),
            "mandatory_gates": {
                "gate_personal_intent": False,
                "gate_verifiable_source": False if "DELETED" in reason_code else True,
                "gate_current_resident": loc_status == "CURRENT_RESIDENT",
                "gate_freshness": is_fresh,
                "gate_no_broker": False if "BROKER" in reason_code else True,
                "all_mandatory_gates_pass": False
            },
            "scoring_breakdown": {
                "explicit_personal_purchase_intent": 0,
                "purchase_readiness": 0,
                "budget_or_financing_requirements": 0,
                "purchase_timeline": 0,
                "specific_project_property_requirements": 0,
                "freshness": 0
            },
            "component_evidence": {
                "intent_evidence": "None - record disqualified",
                "readiness_evidence": "None - record disqualified",
                "budget_evidence": "None - record disqualified",
                "timeline_evidence": "None - record disqualified",
                "project_evidence": "None - record disqualified",
                "freshness_evidence": "None - record disqualified"
            },
            "component_reason_codes": {
                "intent_reason_code": reason_code,
                "readiness_reason_code": reason_code,
                "budget_reason_code": reason_code,
                "timeline_reason_code": reason_code,
                "project_reason_code": reason_code,
                "freshness_reason_code": reason_code
            }
        }
