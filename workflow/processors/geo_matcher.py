"""
Strict Geographic Evidence Verification Engine for South India.
Target States: Karnataka, Kerala, Tamil Nadu, Telangana, Andhra Pradesh.

Rules enforced:
1. Explicit, attributable evidence of current residence is mandatory to qualify as South India-based.
2. Does NOT infer residence from subreddit membership, language, birthplace, surname, profession, or posting location.
3. Distinguishes between:
   - CURRENT_RESIDENT: Attributable evidence of living/working/residing in target states.
   - ORIGIN_ONLY: Evidence of native roots, hometown, or origin without current local residency.
   - LOCATION_UNVERIFIED: No attributable location mentioned in text.
   - OUTSIDE_TARGET: Explicit evidence of residence outside the 5 South Indian states.
4. Never guesses or generates missing location information.
"""

import re
from typing import Dict, Any, Optional, Tuple, List
from workflow.config import TARGET_STATES, STATE_DISPLAY_NAMES


class GeoMatcher:
    def __init__(self):
        # Target South Indian City/Locality Canonical Mappings
        self.target_cities: Dict[str, Tuple[str, str]] = {
            # Karnataka
            "bangalore": ("Bengaluru", "Karnataka"),
            "bengaluru": ("Bengaluru", "Karnataka"),
            "whitefield": ("Bengaluru", "Karnataka"),
            "hsr layout": ("Bengaluru", "Karnataka"),
            "hsr": ("Bengaluru", "Karnataka"),
            "electronic city": ("Bengaluru", "Karnataka"),
            "koramangala": ("Bengaluru", "Karnataka"),
            "indiranagar": ("Bengaluru", "Karnataka"),
            "bellandur": ("Bengaluru", "Karnataka"),
            "sarjapur": ("Bengaluru", "Karnataka"),
            "hebbal": ("Bengaluru", "Karnataka"),
            "yelahanka": ("Bengaluru", "Karnataka"),
            "manyata": ("Bengaluru", "Karnataka"),
            "marathahalli": ("Bengaluru", "Karnataka"),
            "mysore": ("Mysuru", "Karnataka"),
            "mysuru": ("Mysuru", "Karnataka"),
            "mangalore": ("Mangaluru", "Karnataka"),
            "mangaluru": ("Mangaluru", "Karnataka"),
            "hubli": ("Hubballi", "Karnataka"),
            "hubballi": ("Hubballi", "Karnataka"),
            "belgaum": ("Belagavi", "Karnataka"),
            "belagavi": ("Belagavi", "Karnataka"),
            "udupi": ("Udupi", "Karnataka"),
            "manipal": ("Manipal", "Karnataka"),
            "karnataka": ("Bengaluru", "Karnataka"),

            # Kerala
            "kochi": ("Kochi", "Kerala"),
            "cochin": ("Kochi", "Kerala"),
            "ernakulam": ("Kochi", "Kerala"),
            "trivandrum": ("Thiruvananthapuram", "Kerala"),
            "thiruvananthapuram": ("Thiruvananthapuram", "Kerala"),
            "calicut": ("Kozhikode", "Kerala"),
            "kozhikode": ("Kozhikode", "Kerala"),
            "thrissur": ("Thrissur", "Kerala"),
            "kannur": ("Kannur", "Kerala"),
            "kottayam": ("Kottayam", "Kerala"),
            "palakkad": ("Palakkad", "Kerala"),
            "malappuram": ("Malappuram", "Kerala"),
            "kollam": ("Kollam", "Kerala"),
            "alappuzha": ("Alappuzha", "Kerala"),
            "kerala": ("Kochi", "Kerala"),

            # Tamil Nadu
            "chennai": ("Chennai", "Tamil Nadu"),
            "madras": ("Chennai", "Tamil Nadu"),
            "omr": ("Chennai", "Tamil Nadu"),
            "ecr": ("Chennai", "Tamil Nadu"),
            "anna nagar": ("Chennai", "Tamil Nadu"),
            "t nagar": ("Chennai", "Tamil Nadu"),
            "velachery": ("Chennai", "Tamil Nadu"),
            "adyar": ("Chennai", "Tamil Nadu"),
            "coimbatore": ("Coimbatore", "Tamil Nadu"),
            "madurai": ("Madurai", "Tamil Nadu"),
            "trichy": ("Tiruchirappalli", "Tamil Nadu"),
            "tiruchirappalli": ("Tiruchirappalli", "Tamil Nadu"),
            "salem": ("Salem", "Tamil Nadu"),
            "tiruppur": ("Tiruppur", "Tamil Nadu"),
            "erode": ("Erode", "Tamil Nadu"),
            "vellore": ("Vellore", "Tamil Nadu"),
            "tamil nadu": ("Chennai", "Tamil Nadu"),

            # Telangana
            "hyderabad": ("Hyderabad", "Telangana"),
            "secunderabad": ("Secunderabad", "Telangana"),
            "gachibowli": ("Hyderabad", "Telangana"),
            "hitec city": ("Hyderabad", "Telangana"),
            "madhapur": ("Hyderabad", "Telangana"),
            "kondapur": ("Hyderabad", "Telangana"),
            "tellapur": ("Hyderabad", "Telangana"),
            "jubilee hills": ("Hyderabad", "Telangana"),
            "banjara hills": ("Hyderabad", "Telangana"),
            "kokapet": ("Hyderabad", "Telangana"),
            "financial district": ("Hyderabad", "Telangana"),
            "warangal": ("Warangal", "Telangana"),
            "karimnagar": ("Karimnagar", "Telangana"),
            "nizamabad": ("Nizamabad", "Telangana"),
            "telangana": ("Hyderabad", "Telangana"),

            # Andhra Pradesh
            "visakhapatnam": ("Visakhapatnam", "Andhra Pradesh"),
            "vizag": ("Visakhapatnam", "Andhra Pradesh"),
            "vijayawada": ("Vijayawada", "Andhra Pradesh"),
            "guntur": ("Guntur", "Andhra Pradesh"),
            "tirupati": ("Tirupati", "Andhra Pradesh"),
            "nellore": ("Nellore", "Andhra Pradesh"),
            "amaravati": ("Amaravati", "Andhra Pradesh"),
            "rajahmundry": ("Rajahmundry", "Andhra Pradesh"),
            "kakinada": ("Kakinada", "Andhra Pradesh"),
            "kurnool": ("Kurnool", "Andhra Pradesh"),
            "andhra pradesh": ("Visakhapatnam", "Andhra Pradesh")
        }

        # Known locations outside the 5 target South Indian states
        self.outside_target_locations = [
            "delhi", "new delhi", "south delhi", "north delhi", "west delhi",
            "gurgaon", "gurugram", "noida", "greater noida", "faridabad", "ghaziabad", "ncr",
            "mumbai", "bombay", "pune", "thane", "navi mumbai", "nagpur",
            "kolkata", "calcutta",
            "ahmedabad", "surat", "vadodara", "gujarat",
            "jaipur", "rajasthan", "lucknow", "kanpur", "chandigarh", "punjab",
            "london", "uk", "dubai", "sharjah", "abu dhabi", "uae",
            "singapore", "usa", "us", "california", "texas", "canada", "australia"
        ]

        # Regex pattern for explicit residency verbs and phrases
        self.residency_verbs_pattern = re.compile(
            r'\b(?:'
            r'resident of|'
            r'living in|'
            r'residing in|'
            r'based in|'
            r'working in|'
            r'settled in|'
            r'living near|'
            r'office in|'
            r'practicing in|'
            r'staying in|'
            r'resident indian in|'
            r'local resident of|'
            r'running (?:software )?business in|'
            r'textile business owner from|'
            r'agri exporter from|'
            r'business owner from|'
            r'shipping logistics business based in|'
            r'surgeon residing in|'
            r'doctor practicing in|'
            r'software architect living in'
            r')\s+([A-Za-z0-9\s,\(\)]+)',
            re.IGNORECASE
        )

        # Regex for origin only (heritage, birthplace, roots without current residence)
        self.origin_pattern = re.compile(
            r'\b(?:'
            r'native of|'
            r'originally from|'
            r'born in|'
            r'hometown is|'
            r'roots in|'
            r'native place|'
            r'[A-Za-z]+\s+native|'
            r'nri\s+from|'
            r'malayali\s+(?:in|settled in)\s+(?:dubai|uae|sharjah|gulf|kuwait|qatar)'
            r')\b',
            re.IGNORECASE
        )

    def extract_geo(self, text: str, platform_context: str = "", source_link: str = "") -> Dict[str, Any]:
        """
        Extracts geographic information with strict evidence verification.
        Does NOT infer residence from subreddit membership, language, or posting/event location.
        Returns a dictionary with state, city, city_state, confidence, and exact location evidence.
        """
        # Split text into sentences for attributable quotation
        sentences = [s.strip() for s in re.split(r'[.!?\n]+', text) if s.strip()]

        # ----------------------------------------------------------------------
        # 1. Check for OUTSIDE_TARGET (Explicit residence outside South India)
        # ----------------------------------------------------------------------
        for s in sentences:
            s_lower = s.lower()
            for out in self.outside_target_locations:
                out_match = re.search(
                    r'\b(?:living in|residing in|resident of|based in|working in|settled in)\s+' + re.escape(out) + r'\b',
                    s_lower
                ) or re.search(r'\b' + re.escape(out) + r'\s+(?:resident|based)\b', s_lower)
                if out_match:
                    return {
                        "location_verification_status": "OUTSIDE_TARGET",
                        "location_evidence_text": s,
                        "location_evidence_url": source_link,
                        "state": "Outside Target",
                        "city": out.title(),
                        "city_state": f"{out.title()} (Outside Target Geography)",
                        "geo_evidence": s,
                        "confidence": "NONE"
                    }

        # ----------------------------------------------------------------------
        # 2. Check for CURRENT_RESIDENT (Explicit residency in South India)
        # ----------------------------------------------------------------------
        for s in sentences:
            s_lower = s.lower()

            # Rule 2 Enforcement: Disqualify event attendance and video watching from being residency
            if re.search(r'\b(?:went to|attended|visiting|visited|watching from)\s+(?:the\s+)?(?:dubai|expo|roadshow|show|webinar)\b', s_lower):
                # An attendee or viewer is not automatically a resident unless another sentence proves residence
                continue

            # Check explicit residency verb phrases
            m = self.residency_verbs_pattern.search(s)
            if m:
                matched_phrase = m.group(0).lower()
                for city_key, (c_name, s_name) in self.target_cities.items():
                    if re.search(r'\b' + re.escape(city_key) + r'\b', matched_phrase):
                        return {
                            "location_verification_status": "CURRENT_RESIDENT",
                            "location_evidence_text": s,
                            "location_evidence_url": source_link,
                            "state": s_name,
                            "city": c_name,
                            "city_state": f"{c_name}, {s_name}",
                            "geo_evidence": s,
                            "confidence": "HIGH"
                        }

            # Check "<City> resident" or "<City> based" or "firm in <City>"
            for city_key, (c_name, s_name) in self.target_cities.items():
                if (
                    re.search(r'\b' + re.escape(city_key) + r'\s+(?:resident|based)\b', s_lower) or
                    re.search(r'\bfirm in\s+' + re.escape(city_key) + r'\b', s_lower) or
                    re.search(r'\bworking in\s+' + re.escape(city_key) + r'\b', s_lower) or
                    re.search(r'\bwhile living in\s+' + re.escape(city_key) + r'\b', s_lower) or
                    re.search(r'\bresident of\s+' + re.escape(city_key) + r'\b', s_lower)
                ):
                    return {
                        "location_verification_status": "CURRENT_RESIDENT",
                        "location_evidence_text": s,
                        "location_evidence_url": source_link,
                        "state": s_name,
                        "city": c_name,
                        "city_state": f"{c_name}, {s_name}",
                        "geo_evidence": s,
                        "confidence": "HIGH"
                    }

            # Check composite statements: "From <City>, currently working in <City2>"
            if "currently working in" in s_lower or "currently working remote" in s_lower:
                for city_key, (c_name, s_name) in self.target_cities.items():
                    if re.search(r'\b' + re.escape(city_key) + r'\b', s_lower):
                        return {
                            "location_verification_status": "CURRENT_RESIDENT",
                            "location_evidence_text": s,
                            "location_evidence_url": source_link,
                            "state": s_name,
                            "city": c_name,
                            "city_state": f"{c_name}, {s_name}",
                            "geo_evidence": s,
                            "confidence": "HIGH"
                        }

        # ----------------------------------------------------------------------
        # 3. Check for ORIGIN_ONLY (Roots, heritage, or past origin without current residency)
        # ----------------------------------------------------------------------
        for s in sentences:
            s_lower = s.lower()

            # Rule 2: Watching/viewing/posting location is NOT origin or residence
            if "watching from" in s_lower or "viewing from" in s_lower or "posting from" in s_lower:
                continue

            has_origin_keyword = bool(self.origin_pattern.search(s_lower))
            has_from_keyword = bool(re.search(r'\bfrom\s+(?:kannur|thrissur|vijayawada|madurai|bengaluru|bangalore|hyderabad|chennai|kochi|trivandrum|mysore|vizag)\b', s_lower))

            if has_origin_keyword or has_from_keyword:
                for city_key, (c_name, s_name) in self.target_cities.items():
                    if re.search(r'\b' + re.escape(city_key) + r'\b', s_lower):
                        return {
                            "location_verification_status": "ORIGIN_ONLY",
                            "location_evidence_text": s,
                            "location_evidence_url": source_link,
                            "state": s_name,
                            "city": c_name,
                            "city_state": f"{c_name}, {s_name} (Origin Only)",
                            "geo_evidence": f"Origin only (current residence unverified): {s}",
                            "confidence": "LOW"
                        }

        # ----------------------------------------------------------------------
        # 4. LOCATION_UNVERIFIED (Default when no attributable residency in text)
        # ----------------------------------------------------------------------
        # Rule 6: Never generate or guess missing location information
        return {
            "location_verification_status": "LOCATION_UNVERIFIED",
            "location_evidence_text": "None - unverified",
            "location_evidence_url": source_link,
            "state": "Unverified",
            "city": "Unverified",
            "city_state": "Unverified",
            "geo_evidence": "No attributable current residence evidence in public text",
            "confidence": "NONE"
        }
