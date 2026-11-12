# Dubai Real Estate Lead Discovery & Qualification Workflow (South India)

A modular, automated, and repeatable Python workflow to discover, normalize, qualify, and export potential Dubai real estate buyers and investors based in **South India** (Karnataka, Kerala, Tamil Nadu, Telangana, and Andhra Pradesh).

The workflow isolates genuine buyer demand from noise—excluding real estate brokers, channel partners, marketers, general job seekers, or tourists—and categorizes prospects into **Strong Signal**, **Needs Validation**, and **Reject** with verifiable evidence, exact source links, dates, and transparent qualification reasons.

---

## Key Deliverables

1. **Master Results Dataset (222 Unique Candidate Prospects)**:
   - CSV Format: [`results/dubai_real_estate_south_india_prospects.csv`](results/dubai_real_estate_south_india_prospects.csv) (Google Sheets compatible)
   - Excel Format: [`results/dubai_real_estate_south_india_prospects.xlsx`](results/dubai_real_estate_south_india_prospects.xlsx)
2. **Top 5 Strongest Prospects Shortlist**:
   - Detailed Buyer Dossier: [`results/top_5_strongest_prospects.md`](results/top_5_strongest_prospects.md)
3. **Comprehensive Methodology & Analysis Report**:
   - In-depth Report: [`docs/methodology_and_report.md`](docs/methodology_and_report.md)
4. **Automated Test Suite**:
   - Unit Tests: [`tests/`](tests/) (13 automated test cases covering dedup, geo matching, and qualification scoring)

---

## Dataset Schema

Each prospect record includes:
- `record_id`: Unique tracking ID (e.g., `DUB-SI-001`)
- `public_name_or_handle`: Public username or handle on the platform
- `platform`: Community or forum platform (Reddit, YouTube, IREF, Quora, Property Expos)
- `city_state`: Identified South Indian city and state (e.g., `Bengaluru, Karnataka`, `Hyderabad, Telangana`)
- `geo_evidence`: Verbatim excerpt confirming regional residency or origin
- `source_link`: Exact public URL of the discussion thread or video comment
- `signal_date`: Date when the buying signal was posted
- `dubai_property_evidence`: Verbatim text demonstrating interest in Dubai property
- `qualification_status`: Classification (`Strong Signal`, `Needs Validation`, `Reject`)
- `qualification_reason`: Explicit rationale behind the classification decision
- `unverified_information`: Key parameters remaining unconfirmed
- `ticket_size_budget`: Stated or estimated budget (INR and AED equivalent)
- `preferred_areas`: Target Dubai communities (e.g., JVC, Business Bay, Marina, Downtown) or developers (Emaar, Sobha, Danube)

---

## Funnel & Metrics Summary

| Classification | Count | Percentage | Description |
| :--- | :--- | :--- | :--- |
| **Strong Signal** | **96** | **43.2%** | High intent & verified fresh (≤ 6 months / 180 days): Stated budget, timeline, target projects, verified South Indian location, non-broker. |
| **Needs Validation** | **69** | **31.1%** | Moderate intent OR high-intent signals older than 6 months requiring active status re-validation. |
| **Reject** | **57** | **25.7%** | Disqualified: Identified as broker/agent selling units, job seeker, or out-of-geography inquiry. |
| **Total Unique** | **222** | **100.0%** | **Deduplicated from 231 raw harvested records** |

### Geographic Spread

- **Karnataka**: 45 (20.3%) — Bengaluru, Mysuru, Mangaluru, Hubballi
- **Kerala**: 44 (19.8%) — Kochi, Thiruvananthapuram, Kozhikode, Thrissur, Kannur
- **Telangana**: 42 (18.9%) — Hyderabad, Secunderabad, Warangal, Karimnagar
- **Tamil Nadu**: 42 (18.9%) — Chennai, Coimbatore, Madurai, Tiruchirappalli
- **Andhra Pradesh**: 38 (17.1%) — Visakhapatnam, Vijayawada, Guntur, Tirupati
- **Unverified / Out of Region**: 11 (5.0%) — Disqualified non-South Indian inquiries

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

