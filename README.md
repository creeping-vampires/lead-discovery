# Dubai Real Estate Lead Discovery & Qualification Workflow (South India)

A modular, automated, and repeatable Python workflow to discover, normalize, qualify, and export potential Dubai real estate buyers and investors based in **South India** (Karnataka, Kerala, Tamil Nadu, Telangana, and Andhra Pradesh).

The workflow isolates genuine buyer demand from noise—excluding real estate brokers, channel partners, marketers, general job seekers, or tourists—and categorizes prospects into **Strong Signal**, **Needs Validation**, and **Reject** with verifiable evidence, exact source links, dates, and transparent qualification reasons.

---

## Input and Output Architecture

### 1. `input/` Directory (Raw Discovery Data)
Stores all 231 raw candidate records discovered from public community sources before filtering, deduplication, or scoring:
- [`input/raw_discovered_candidates.json`](input/raw_discovered_candidates.json): Structured JSON array of raw posts/comments with verbatim text, handles, dates, and source URLs.
- [`input/raw_discovered_candidates.csv`](input/raw_discovered_candidates.csv): Tabular CSV format of the raw discovery data.

### 2. `results/` Directory (Exclusively Qualified Leads)
Contains **ONLY ONE master Excel file** containing qualified leads scoring **> 70 out of 100 points**:
- [`results/qualified_dubai_leads.xlsx`](results/qualified_dubai_leads.xlsx): Professionally styled Excel workbook with freeze-panes, auto-fit column widths, verified public links, and detailed 0–100 score breakdowns.

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
```

---

## Funnel & Metrics Summary

| Funnel Stage | Count | Share (%) | Description |
| :--- | :---: | :---: | :--- |
| **Total Raw Discovered Candidates** | **231** | 100.0% | Stored in `input/raw_discovered_candidates.json` & `.csv` |
| **Unique Deduplicated Prospects** | **222** | 96.1% | Pruned 9 duplicate handles and URLs |
| **Qualified Leads (Score > 70/100)** | **58** | **26.1%** | **Exported exclusively to `results/qualified_dubai_leads.xlsx`** |
| - *Tier 1 Premium (Score 90–100)* | 40 | 69.0% of qualified | Explicit budget + timeline + project + developer + verified location |
| - *Tier 2 High (Score 80–89)* | 10 | 17.2% of qualified | Explicit budget + project + developer + verified location |
| - *Tier 3 Qualified (Score 71–79)* | 8 | 13.8% of qualified | Stated budget + project/locality + verified location |

### Geographic Spread of Qualified Leads (> 70 Points)
- **Karnataka**: 16 (27.6%) — Bengaluru, Mysuru, Mangaluru, Hubballi
- **Tamil Nadu**: 12 (20.7%) — Chennai, Coimbatore, Madurai, Trichy
- **Andhra Pradesh**: 12 (20.7%) — Visakhapatnam, Vijayawada, Guntur, Tirupati
- **Telangana**: 10 (17.2%) — Hyderabad, Secunderabad, Warangal
- **Kerala**: 8 (13.8%) — Kochi, Thiruvananthapuram, Kozhikode, Thrissur

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
- `results/dubai_real_estate_south_india_prospects.csv`
- `results/dubai_real_estate_south_india_prospects.xlsx`
- `results/top_5_strongest_prospects.md`

### 3. Run Automated Tests
To run the automated test suite:

```bash
python -m unittest discover tests
```

---

## System Architecture

```
real-estate-leads-assignment/
├── README.md                                  # Setup, overview & documentation
├── requirements.txt                           # Dependencies (pandas, openpyxl, python-dateutil)
├── workflow/
│   ├── __init__.py
│   ├── config.py                              # Target geographies, keywords, micro-markets, developers
│   ├── harvesters/
│   │   ├── __init__.py
│   │   ├── base.py                            # Harvester base class
│   │   ├── reddit_harvester.py                # Reddit discovery across regional & finance subs
│   │   ├── youtube_harvester.py               # YouTube public webinars and comment feeds
│   │   └── forum_harvester.py                 # IREF, Quora, and South India Property Expos
│   ├── processors/
│   │   ├── __init__.py
│   │   ├── deduplicator.py                    # Deduplication by handle, URL, and content hash
│   │   ├── geo_matcher.py                     # South India NER & geocoding resolver
│   │   └── intent_classifier.py               # Intent scoring and status assignment engine
│   └── main.py                                # CLI orchestrator
├── results/
│   ├── dubai_real_estate_south_india_prospects.csv   # Master dataset (CSV)
│   ├── dubai_real_estate_south_india_prospects.xlsx  # Master dataset (Excel)
│   └── top_5_strongest_prospects.md           # Dossier of top 5 strongest prospects
├── docs/
│   └── methodology_and_report.md              # In-depth report on sourcing, rules, and ethics
└── tests/
    ├── test_dedup.py                          # Tests for deduplication logic
    ├── test_geo.py                            # Tests for geographic entity extraction
    └── test_classifier.py                     # Tests for qualification and broker rejection
```

---

## Ethics & Compliance Principles

- **Exclusively Public & Authorised Sources**: No private accounts, protected groups, or login paywalls were breached.
- **Zero PII Harvesting**: No private email addresses, personal phone numbers, or national identity documents were collected.
- **No Unsolicited Outreach**: Zero automated contact or unsolicited outreach is performed.
- **Data Integrity**: In accordance with project instructions, no data is invented or fabricated to inflate volume.

