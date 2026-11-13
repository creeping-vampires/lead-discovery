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
# WEIGHTED SCORING CONFIGURATION (100 Points Scale)
# ==============================================================================
SCORE_PERSONAL_INTENT: int = 30              # Explicit first-person purchase/investment intent
SCORE_PURCHASE_READINESS: int = 20           # Transactional readiness (token, down payment, LRS 15CA, SPA, travel)
SCORE_BUDGET_FINANCING: int = 15             # Stated financial budget (AED/INR/USD) or explicit payment plan
SCORE_PURCHASE_TIMELINE: int = 15            # Concrete purchase timeline horizon (immediate, next month, Q3, etc.)
SCORE_PROJECT_REQUIREMENTS: int = 10         # Specific Dubai micro-market, developer, or unit type
SCORE_FRESHNESS: int = 10                    # Buying-intent signal within last 180 days (<= 180 days)

# Total theoretical maximum = 30 + 20 + 15 + 15 + 10 + 10 = 100 points.

# Strong Signal Score Threshold (0 to 100 scale)
# Strong Signal requires all 5 mandatory gates to pass AND score >= STRONG_SIGNAL_THRESHOLD
STRONG_SIGNAL_THRESHOLD: int = 75

# Backward compatibility alias for results export filtering
QUALIFIED_SCORE_THRESHOLD: int = STRONG_SIGNAL_THRESHOLD

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

# Score penalty for signals older than MAX_FRESHNESS_DAYS (prevents stale leads from scoring > 70)
PENALTY_STALE_SIGNAL: int = 30

# ==============================================================================
# SOURCE URL & REDDIT AVAILABILITY VERIFICATION CONSTANTS
# ==============================================================================
# Master toggle to enforce source URL existence & deletion filtering
VERIFY_SOURCE_AVAILABILITY: bool = True

# Enforce Reddit posts & comments are not deleted by author or removed by moderators
VERIFY_REDDIT_COMMUNITY: bool = True

# Optional live network HTTP probe of URLs (can be enabled via CLI flag --check-live)
CHECK_LIVE_URLS: bool = False

# Timeout for live HTTP requests in seconds
LIVE_PROBE_TIMEOUT: float = 3.0

# ==============================================================================
# EVIDENCE AUDITING, PERMITTED SOURCES & REPRODUCIBILITY CONSTANTS
# ==============================================================================
# Permitted public source domains authorized for non-invasive market research
PERMITTED_SOURCE_DOMAINS: Set[str] = {
    "reddit.com",
    "www.reddit.com",
    "old.reddit.com",
    "youtube.com",
    "www.youtube.com",
    "youtu.be",
    "indianrealestateforum.com",
    "www.indianrealestateforum.com",
    "quora.com",
    "www.quora.com",
    "dubaipropertyshow.com",
    "www.dubaipropertyshow.com",
    "dubaipropertyexpo.in",
    "www.dubaipropertyexpo.in",
    "teamexpo.ae",
    "www.teamexpo.ae",
    "expoplatform.com",
    "www.expoplatform.com",
    "economictimes.indiatimes.com",
    "m.economictimes.com",
    "thehindu.com",
    "www.thehindu.com",
    "timesofindia.indiatimes.com",
    "gulfnews.com",
    "www.gulfnews.com",
    "linkedin.com",
    "www.linkedin.com"
}

# Manual review sampling targets
SAMPLE_STRONG_COUNT: int = 30
SAMPLE_NEEDS_VAL_COUNT: int = 20
SAMPLE_REJECT_COUNT: int = 10

# Default discovery run date
DEFAULT_DISCOVERY_DATE: str = "2026-11-12"





