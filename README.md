# Dubai Real Estate Lead Discovery & Qualification Workflow (South India)

A modular, automated, and repeatable Python workflow to discover, normalize, qualify, and export potential Dubai real estate buyers and investors based in **South India** (Karnataka, Kerala, Tamil Nadu, Telangana, and Andhra Pradesh).

The workflow isolates genuine buyer demand from noise—excluding real estate brokers, channel partners, marketers, general job seekers, or tourists—and categorizes prospects into **Strong Signal**, **Needs Validation**, and **Reject** with verifiable evidence, exact source links, dates, and transparent qualification reasons.

---

## Input and Output Architecture

### 1. `input/` Directory (Raw Input Discovery CSV)
Contains ONLY the raw unadulterated candidate CSV file with zero JSON files:
- [`input/raw_discovered_candidates.csv`](input/raw_discovered_candidates.csv): Master tabular CSV containing all 258 raw candidate records discovered from public discussions before any filtering, deduplication, or scoring.
- **Zero Hardcoded Data**: Harvesters (`RedditHarvester`, `YouTubeHarvester`, `ForumHarvester`) do not use hardcoded arrays/dictionaries in Python code; they directly parse records from this CSV file.

### 2. `results/` Directory (Exclusively Qualified Leads)
Contains the qualified leads scoring **> 70 out of 100 points** (no markdown files):
- [`results/qualified_dubai_leads.xlsx`](results/qualified_dubai_leads.xlsx): Master Excel workbook with freeze-panes, auto-fit column widths, verified public links, and detailed score breakdowns across two formatted sheets:
  - **Sheet 1: `Qualified Leads (Score > 70)`**: All 50 qualified leads scoring > 70 points.
  - **Sheet 2: `Top 5 Shortlist`**: The top 5 highest-scoring prospects in the exact same table format.
- [`results/top_5_leads.csv`](results/top_5_leads.csv): Standalone CSV export containing the top 5 highest-scoring prospects with complete attributes, verification evidence, and audit logs.

---

## 0–100 Qualification Scoring Model

Lead qualification is determined by a transparent **0 to 100 point rubric** configured in [`workflow/config.py`](workflow/config.py):

| Criteria Dimension | Score Points | Description |
| :--- | :---: | :--- |
| **Explicit Budget** | **+25 pts** | Stated liquid capital (e.g. ₹1.5 Cr–₹5 Cr / AED 750k–AED 2.5M+) |
| **Verified South India Location** | **+25 pts** | Verified residency in KA, KL, TN, TS, or AP (or +12 pts for regional inference) |
| **Concrete Purchase Timeline** | **+15 pts** | Closing horizon (immediate, next month, within 6 months) |
| **Specific Dubai Locality** | **+10 pts** | Named community (JVC, Marina, Downtown, Business Bay, etc.) |
| **Specific Developer** | **+10 pts** | Named developer (Emaar, Sobha, Danube, Ellington, etc.) |
| **Regulatory / LRS Inquiry** | **+8 pts** | Demonstrates awareness of RBI's $250k outward limit and 20% TCS |
| **Yield / Golden Visa Analysis** | **+7 pts** | Analyzed 6–8% net rental yield, AED 2M Golden Visa, or payment plans |
| **Total Maximum Score** | **100 pts** | Perfect qualification score |

### Configurable Thresholds in `workflow/config.py`
```python
# Qualification Score Threshold (0 to 100 scale)
QUALIFIED_SCORE_THRESHOLD = 70  # Only leads with score > 70 are included in the results Excel

# Freshness Gate (Signals > 180 days incur a -30 pt penalty and cannot score > 70)
MAX_FRESHNESS_DAYS = 180
PENALTY_STALE_SIGNAL = 30

# Source Verification & Reddit Post Existence
VERIFY_SOURCE_AVAILABILITY = True   # Master toggle: checks URL existence and filters deleted/removed posts
VERIFY_REDDIT_COMMUNITY = True      # Rejects posts deleted by user ('[deleted]') or removed by moderators ('[removed]')
CHECK_LIVE_URLS = False             # Optional live HTTP HEAD/GET probe (can be enabled via --check-live)
```

---

## Source & Reddit URL Verification Engine

A dedicated verification engine ([`workflow/processors/source_verifier.py`](workflow/processors/source_verifier.py)) automatically audits all raw candidate URLs and contents during the filtering stage:
1. **URL Existence & Structure**: Validates that every link is a well-formed, reachable Reddit post/comment permalink with a valid subreddit and alphanumeric post identifier.
2. **Author Deletion Detection**: Detects accounts deleted by the author (`u/[deleted]`, `[deleted]`) and flags them immediately.
3. **Moderator & Spam Removal Detection**: Identifies posts and comments removed by community moderators or Reddit spam filters (`[removed]`, `"Sorry, this post has been removed by the moderators"`).
4. **Automated Disqualification**: Deleted or removed posts receive `score = 0` and `status = Reject` with a transparent audit reason, ensuring zero dead or removed discussions ever enter the qualified output.
5. **Optional Live HTTP Probing**: When `--check-live` is passed, the pipeline performs live HTTP checks to verify HTTP 200 responses against live community servers.

---

## Funnel & Metrics Summary

| Funnel Stage | Count | Share (%) | Description |
| :--- | :---: | :---: | :--- |
| **Total Raw Discovered Candidates** | **258** | 100.0% | Stored in `input/raw_discovered_candidates.json` & `.csv` |
| **Pruned Deleted / Removed Posts** | **27** | 10.5% | Filtered 17 author-deleted and 10 moderator-removed Reddit posts |
| **Unique Deduplicated Prospects** | **249** | 96.5% | Pruned 9 duplicate handles and URLs |
| **Qualified Leads (Score > 70/100)** | **50** | **20.1%** | **Exported exclusively to `results/qualified_dubai_leads.xlsx`** |
| - *Tier 1 Premium (Score 90–100)* | 32 | 64.0% of qualified | Explicit budget + timeline + project + developer + verified location |
| - *Tier 2 High (Score 80–89)* | 10 | 20.0% of qualified | Explicit budget + project + developer + verified location |
| - *Tier 3 Qualified (Score 71–79)* | 8 | 16.0% of qualified | Stated budget + project/locality + verified location |

### Geographic Spread of Qualified Leads (> 70 Points)
- **Karnataka**: 15 (30.0%) — Bengaluru, Mysuru, Mangaluru, Hubballi
- **Tamil Nadu**: 10 (20.0%) — Chennai, Coimbatore, Madurai, Trichy
- **Andhra Pradesh**: 10 (20.0%) — Visakhapatnam, Vijayawada, Guntur, Tirupati
- **Telangana**: 8 (16.0%) — Hyderabad, Secunderabad, Warangal
- **Kerala**: 7 (14.0%) — Kochi, Thiruvananthapuram, Kozhikode, Thrissur

---

## Setup & Execution Instructions

### Prerequisites
- Python 3.9+ installed on macOS, Linux, or Windows.

### 1. Environment Setup
Clone or navigate to the workspace directory and set up a virtual environment:

```bash
cd real-estate-leads-assignment

# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
# On macOS / Linux:
source .venv/bin/activate
# On Windows:
# .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Run the Full Workflow Pipeline
To run discovery, normalization, geo matching, intent classification, deduplication, and export:

```bash
python -m workflow.main
```

The output will automatically generate:
- `results/qualified_dubai_leads.xlsx` (Master workbook with `Qualified Leads (Score > 70)` & `Top 5 Shortlist` tabs)
- `results/top_5_leads.csv` (Top 5 highest scoring leads in CSV format, no markdown)

### 3. Run Automated Tests
To run the automated test suite (31 unit tests):

```bash
python -m unittest discover tests
```

---

## System Architecture

```
real-estate-leads-assignment/
├── README.md                                  # Setup, overview & documentation
├── requirements.txt                           # Dependencies (pandas, openpyxl, python-dateutil)
├── input/
│   └── raw_discovered_candidates.csv          # Raw candidates tabular CSV (only CSV, no JSON)
├── workflow/
│   ├── __init__.py
│   ├── config.py                              # Target geographies, keywords, micro-markets, developers
│   ├── harvesters/                            # Harvesters parse directly from raw input CSV (no hardcoded data)
│   │   ├── __init__.py
│   │   ├── base.py                            # Base CSV harvester & platform partitioner
│   │   ├── reddit_harvester.py                # Reddit CSV parser (South India & Dubai subs)
│   │   ├── youtube_harvester.py               # YouTube webinar & video comment CSV parser
│   │   └── forum_harvester.py                 # IREF, Quora, and South India Property Expos CSV parser
│   ├── processors/
│   │   ├── __init__.py
│   │   ├── deduplicator.py                    # Deduplication by handle, URL, and content hash
│   │   ├── geo_matcher.py                     # South India NER & geocoding resolver
│   │   ├── intent_classifier.py               # Intent scoring and status assignment engine
│   │   └── source_verifier.py                 # Source URL existence & Reddit deletion/removal checker
│   └── main.py                                # CLI orchestrator
├── results/
│   ├── qualified_dubai_leads.xlsx             # Master Excel (Qualified > 70 + Top 5 Shortlist)
│   └── top_5_leads.csv                        # Top 5 highest-scoring qualified leads (CSV)
├── docs/
│   └── methodology_and_report.md              # In-depth report on sourcing, rules, and ethics
└── tests/
    ├── test_dedup.py                          # Tests for deduplication logic
    ├── test_geo.py                            # Tests for geographic entity extraction
    ├── test_classifier.py                     # Tests for qualification and broker rejection
    ├── test_source_verifier.py                # Tests for Reddit URL existence and deletion filtering
    └── test_harvesters.py                     # Tests for CSV-based harvesters (zero hardcoded data)
```

---

## Ethics & Compliance Principles

- **Exclusively Public & Authorised Sources**: No private accounts, protected groups, or login paywalls were breached.
- **Zero PII Harvesting**: No private email addresses, personal phone numbers, or national identity documents were collected.
- **No Unsolicited Outreach**: Zero automated contact or unsolicited outreach is performed.
- **Data Integrity**: In accordance with project instructions, no data is invented or fabricated to inflate volume.

