"""
Geographic entity matcher for South India (Karnataka, Kerala, Tamil Nadu, Telangana, Andhra Pradesh).
Identifies city, state, confidence score, and supporting evidence.
"""

import re
from typing import Dict, Optional, Tuple
from workflow.config import TARGET_STATES, STATE_DISPLAY_NAMES


class GeoMatcher:
    def __init__(self):
        self.state_patterns = {}
        for state, terms in TARGET_STATES.items():
            pattern = r'\b(' + '|'.join(re.escape(term) for term in terms) + r')\b'
            self.state_patterns[state] = re.compile(pattern, re.IGNORECASE)

        # Context indicators for South India
        self.south_india_general = re.compile(
            r'\b(south india|south indian|deccan|kannada|telugu|tamil|malayalam)\b',
            re.IGNORECASE
        )

    def extract_geo(self, text: str, platform_context: str = "") -> Dict[str, any]:
        """
        Extracts geographic information from text (primary) and platform context (secondary).
        Returns a dictionary with state, city, confidence, and geo_evidence.
        """
        matched_state = None
        matched_city = None
        geo_evidence = []
        confidence = "NONE"

        # 1. Primary search in raw text
        for state, pattern in self.state_patterns.items():
            matches = list(pattern.finditer(text))
            if matches:
                matched_state = state
                candidate = matches[0].group(0).strip()
                matched_city = candidate.capitalize()
                for m in matches:
                    start = max(0, m.start() - 25)
                    end = min(len(text), m.end() + 25)
                    geo_evidence.append(text[start:end].strip())
                confidence = "HIGH"
                break

        # 2. Secondary fallback to platform context if text has no explicit city/state
        if not matched_state and platform_context:
            for state, pattern in self.state_patterns.items():
                matches = list(pattern.finditer(platform_context))
                if matches:
                    matched_state = state
                    candidate = matches[0].group(0).strip()
                    matched_city = candidate.capitalize()
                    geo_evidence.append(f"Inferred from community: {platform_context}")
                    confidence = "MEDIUM"
                    break

        # 3. Fallback to general South India indicators
        if not matched_state:
            combined = f"{text} {platform_context}"
            general_match = self.south_india_general.search(combined)
            if general_match:
                matched_state = "South India (Unspecified State)"
                matched_city = "Unspecified City"
                start = max(0, general_match.start() - 25)
                end = min(len(combined), general_match.end() + 25)
                geo_evidence.append(combined[start:end].strip())
                confidence = "MEDIUM"

        # Standardize city/state representation
        if matched_state and matched_state in STATE_DISPLAY_NAMES:
            if matched_city and matched_city.lower() != matched_state.lower():
                city_state_str = f"{matched_city}, {STATE_DISPLAY_NAMES[matched_state]}"
            else:
                city_state_str = STATE_DISPLAY_NAMES[matched_state]
        elif matched_state:
            city_state_str = matched_state
        else:
            city_state_str = "Unverified"
            confidence = "NONE"

        evidence_str = " | ".join(geo_evidence[:2]) if geo_evidence else "No explicit regional marker found in text"

        return {
            "state": matched_state or "Unverified",
            "city": matched_city or "Unverified",
            "city_state": city_state_str,
            "geo_evidence": evidence_str,
            "confidence": confidence
        }
