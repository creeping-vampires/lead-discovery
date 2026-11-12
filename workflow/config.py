"""
Configuration module for Dubai Real Estate Lead Discovery & Qualification Workflow.
Defines geographic entities, intent keywords, micro-markets, developers, and scoring weights.
"""

from typing import Dict, List, Set

# Target South Indian Geographies
TARGET_STATES: Dict[str, List[str]] = {
    "Karnataka": [
        "bangalore", "bengaluru", "mysore", "mysuru", "mangalore", "mangaluru",
        "hubli", "hubballi", "belgaum", "belagavi", "udupi", "manipal",
        "whitefield", "koramangala", "indiranagar", "hsr layout", "electronic city",
        "bellandur", "sarjapur", "marathahalli", "hebbal", "yelahanka", "manyata"
    ],
    "Kerala": [
        "kochi", "cochin", "trivandrum", "thiruvananthapuram", "calicut", "kozhikode",
        "thrissur", "kannur", "kottayam", "malappuram", "kollam", "palakkad",
        "alappuzha", "ernakulam", "kerala", "malayali", "pravasi"
    ],
    "Tamil Nadu": [
        "chennai", "madras", "coimbatore", "madurai", "trichy", "tiruchirappalli",
        "salem", "tiruppur", "erode", "vellore", "omr", "ecr", "anna nagar",
        "t nagar", "velachery", "adyar"
    ],
    "Telangana": [
        "hyderabad", "secunderabad", "warangal", "nizamabad", "karimnagar",
        "khammam", "gachibowli", "hitec city", "madhapur", "kondapur",
        "kokapet", "financial district", "jubilee hills", "banjara hills", "tellapur"
    ],
    "Andhra Pradesh": [
        "visakhapatnam", "vizag", "vijayawada", "guntur", "tirupati", "nellore",
        "rajahmundry", "kakinada", "kurnool", "amaravati", "anantapur"
    ]
}

# State to Abbreviation / Clean Name mapping
STATE_DISPLAY_NAMES = {
    "Karnataka": "Karnataka",
    "Kerala": "Kerala",
    "Tamil Nadu": "Tamil Nadu",
    "Telangana": "Telangana",
    "Andhra Pradesh": "Andhra Pradesh"
}

# Dubai Micro-Markets / Communities
DUBAI_LOCALITIES: List[str] = [
    "jvc", "jumeirah village circle", "business bay", "downtown dubai", "downtown",
    "dubai marina", "marina", "dubai hills estate", "dubai hills", "creek harbour",
    "dubai creek", "palm jumeirah", "arjan", "al furjan", "meydan", "mbr city",
    "dubai south", "emaar south", "sobha hartland", "town square", "damac hills",
    "jlt", "jumeirah lakes towers", "dubai silicon oasis", "dso", "city walk",
    "al barsha", "motor city", "sports city", "dubai island"
]

# Major Dubai Real Estate Developers
DUBAI_DEVELOPERS: List[str] = [
    "emaar", "sobha", "sobha realty", "danube", "binghatti", "damac",
    "ellington", "aldar", "nakheel", "omniyat", "select group", "meraas",
    "azizi", "samana", "deyaar"
]

# High-Intent Buying Signal Keywords
BUYING_INTENT_KEYWORDS: List[str] = [
    "buy", "buying", "purchase", "invest", "investing", "investment", "book", "booking",
    "off-plan", "off plan", "ready to move", "handover", "payment plan", "rental yield",
    "rental return", "roi", "capital appreciation", "golden visa", "aed 2m", "2 million dirhams",
    "1bhk", "2bhk", "3bhk", "studio", "villa", "townhouse", "apartment", "unit",
    "lrs", "remittance", "remit", "tcs", "tax implication", "fema", "nre", "nro",
    "dld waiver", "escrow", "cashflow", "down payment", "sqft", "yield"
]

# Negative Keywords (Brokers, Channel Partners, Sellers, Job Seekers, Spammers)
NEGATIVE_KEYWORDS: List[str] = [
    "dm me for", "inbox me for", "dm for details", "contact our team", "i am an agent",
    "i am a broker", "licensed realtor", "exclusive inventory", "book on whatsapp",
    "contact my agency", "we are authorized channel partners", "brokerage fee",
    "looking for job in dubai", "cv attached", "seeking software developer job in dubai",
    "visit visa job search", "hiring", "apply now", "dm me to buy"
]

# ==============================================================================
# SCORING CONFIGURATION (0 to 100 Scale)
# ==============================================================================
SCORE_EXPLICIT_BUDGET: int = 25              # Stated financial budget (INR / AED)
SCORE_EXPLICIT_TIMELINE: int = 15            # Concrete timeline (immediate / next month / within 6 mos)
SCORE_SPECIFIC_LOCALITY: int = 10            # Specific Dubai community (JVC, Marina, Downtown, etc.)
SCORE_SPECIFIC_DEVELOPER: int = 10           # Specific developer (Emaar, Sobha, Danube, Ellington, etc.)
SCORE_VERIFIED_GEO_HIGH: int = 25            # Verified South Indian residency/origin in text
SCORE_VERIFIED_GEO_MEDIUM: int = 12          # Regional South India connection inferred from community
SCORE_REGULATORY_LRS: int = 8                # Inquiring about LRS $250k / TCS / remittance rules
SCORE_INVESTMENT_YIELD: int = 7              # Yield / Golden Visa / payment plan analysis

# Total theoretical maximum = 25 + 15 + 10 + 10 + 25 + 8 + 7 = 100 points.

# Qualification Score Threshold (0 to 100 scale)
# Only candidates with score > QUALIFIED_SCORE_THRESHOLD are included in the results Excel
QUALIFIED_SCORE_THRESHOLD: int = 70

# ==============================================================================
# FRESHNESS CONFIGURATION CONSTANTS
# ==============================================================================
# Number of months a buying intent signal remains valid for qualification
FRESHNESS_WINDOW_MONTHS: int = 6

# Average days per month calculation
DAYS_PER_MONTH: int = 30

# Maximum age in days for a signal to qualify as 'Strong Signal'
MAX_FRESHNESS_DAYS: int = FRESHNESS_WINDOW_MONTHS * DAYS_PER_MONTH  # Default: 180 days (6 months)

# Master toggle to enable or disable freshness gating
ENFORCE_FRESHNESS: bool = True

# Score penalty for signals older than MAX_FRESHNESS_DAYS (prevents stale leads from scoring > 70)
PENALTY_STALE_SIGNAL: int = 30




# ==============================================================================
# FRESHNESS CONFIGURATION CONSTANTS
# ==============================================================================
# Number of months a buying intent signal remains valid for qualification
FRESHNESS_WINDOW_MONTHS: int = 6

# Average days per month calculation
DAYS_PER_MONTH: int = 30

# Maximum age in days for a signal to qualify as 'Strong Signal'
# Configurable constant: change this single value to adjust the freshness window across the entire pipeline
MAX_FRESHNESS_DAYS: int = FRESHNESS_WINDOW_MONTHS * DAYS_PER_MONTH  # Default: 180 days (6 months)

# Master toggle to enable or disable freshness gating
ENFORCE_FRESHNESS: bool = True



