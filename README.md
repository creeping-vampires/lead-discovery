# Dubai Real Estate Lead Discovery & Qualification Workflow (South India)

A modular, automated, and repeatable Python workflow to discover, normalize, qualify, and export potential Dubai real estate buyers and investors based in **South India** (Karnataka, Kerala, Tamil Nadu, Telangana, and Andhra Pradesh).

The workflow isolates genuine buyer demand from noise—excluding real estate brokers, channel partners, marketers, general job seekers, or tourists—and categorizes prospects into **Strong Signal**, **Needs Validation**, and **Reject** with verifiable evidence, exact source links, dates, and transparent qualification reasons.

---

## Input and Output Architectureqs

### 1. `input/` Directory (Raw Input Discovery CSV)
Contains ONLY the raw unadulterated candidate CSV file with zero JSON files:
- [`input/raw_discovered_candidates.csv`](input/raw_discovered_candidates.csv): Master tabular CSV containing all 258 raw candidate records discovered from public discussions before any filtering, deduplication, or scoring.
- **Zero Hardcoded Data**: Harvesters (`RedditHarvester`, `YouTubeHarvester`, `ForumHarvester`) do not use hardcoded arrays/dictionaries in Python code; they directly parse records from this CSV file.

### 2. `results/` Directory (Exclusively Results Files)
Stores all output datasets and audit artifacts (no result files in repo root):
- [`results/all_candidates.csv`](results/all_candidates.csv): Master CSV containing all 249 unique candidate records with source audits, date separation, and anomaly review flags.
- [`results/qualified_dubai_leads.xlsx`](results/qualified_dubai_leads.xlsx): Master formatted Excel workbook containing all 24 qualified Strong Signal leads scoring >= 75 points with verified `CURRENT_RESIDENT` status, across two formatted sheets (`Qualified Leads` and `Top 5 Shortlist`).
- [`results/top_5_leads.csv`](results/top_5_leads.csv): The top 5 human-reviewed Strong Signal leads in CSV format with complete attributes and auditor verification notes.
- [`results/audit_report.json`](results/audit_report.json): Reconciled funnel report with pre-freshness vs final breakdown, 180-day downgrade audit, and manual review sampling.
- [`results/processed.json`](results/processed.json): Incremental processing state file recording filename, processed status (`PROCESSED`), records count, and MD5 checksum of every processed input file.

---

## 100-Point Weighted Scoring Model & Mandatory Evidence Gates

Lead qualification is governed by **5 Mandatory Evidence Gates** and an objective **100-point weighted scoring rubric** configured in [`workflow/config.py`](workflow/config.py):

### 5 Mandatory Strong Signal Requirements (ALL Must Pass)
1. **Explicit Personal Intent**: First-person statement of intent to purchase or invest in Dubai real estate (`"actively looking to purchase"`, `"planning to buy"`, `"ready to sign"`, `"want to invest"`, `"booked a token"`). General ROI questions, Golden Visa queries, profession alone, or financial capacity alone never qualify.
2. **Verifiable Source URL**: Traceable, well-formed public URL and original text (excluding author-deleted `[deleted]` or moderator-removed `[removed]` posts).
3. **Verified Current Residence**: Traceable evidence of current residence in target South Indian states (`location_verification_status == "CURRENT_RESIDENT"`).
4. **Freshness Window**: Buying-intent signal dated within the last 180 days ($\le 180$ days).
5. **No Broker / Spam**: Free of broker, promoter, seller, or job-seeker behavior.

### 100-Point Weighted Scoring Rubric

| Criteria Dimension | Score Points | Qualifying Standard |
| :--- | :---: | :--- |
| **Explicit Personal Purchase Intent** | **30 pts** | First-person commitment to buy or invest in Dubai property |
| **Purchase Readiness** | **20 pts** | Transactional step underway (token paid, down payment, LRS 15CA, SPA, travel) |
| **Budget or Financing Requirements** | **15 pts** | Stated budget in AED, INR, USD, or explicit payment plan structure |
| **Purchase Timeline** | **15 pts** | Concrete purchase horizon (immediate, next month, this quarter, by Q3) |
| **Specific Project / Property Requirements** | **10 pts** | Named Dubai micro-market (JVC, Marina, Business Bay), developer, or unit type |
| **Freshness** | **10 pts** | Signal timestamp within the last 180 days ($\le 180$ days) |
| **Total Maximum Score** | **100 pts** | Theoretical maximum composite score |

### Classification Rules
- **`STRONG_SIGNAL`**: All 5 mandatory gates pass AND score $\ge 75$.
- **`NEEDS_VALIDATION`**: Plausible buyer but one or more requirements are unverified, signal is stale ($>180$ days), or score $< 75$.
- **`REJECT`**: Confirmed broker/promoter, irrelevant enquiry, no meaningful buying intent, or confirmed outside target geography.

---

## Strict Geographic Evidence Verification Engine

A dedicated geographic verifier ([`workflow/processors/geo_matcher.py`](workflow/processors/geo_matcher.py)) enforces strict evidence verification rules:
1. **Attributable Current Residence Only**: A prospect qualifies as South India-based only if there is explicit, attributable evidence in the public text that they currently live, reside, or work in Karnataka, Kerala, Tamil Nadu, Telangana, or Andhra Pradesh.
2. **Strict Negative Inferences**: Current residence is **never** inferred from subreddit membership (e.g. posting on `r/bangalore`), language (e.g. Tamil/Kannada), birthplace, surname, profession, or posting/event location (e.g. attending an expo or roadshow).
3. **Four Exhaustive Location Statuses**:
   - `CURRENT_RESIDENT`: Explicit textual evidence of living/working/residing in target states (e.g. "Living in HSR Layout Bangalore", "Resident of Kochi", "Working in OMR Chennai"). Earns +25 pts and is eligible for `Strong Signal`.
   - `ORIGIN_ONLY`: Evidence of origin, hometown, or native roots without affirmative current local residence (e.g. "Thrissur native", "From Kannur holding NRE funds", "Malayali in Dubai").
   - `LOCATION_UNVERIFIED`: No attributable location statement in text.
   - `OUTSIDE_TARGET`: Explicit current residence outside target states (e.g. "Living in South Delhi / Gurgaon", "Resident of Mumbai"). Disqualified immediately.
4. **Audit Fields Stored for Every Prospect**:
   - `location_verification_status`: One of the 4 standard statuses.
   - `location_evidence_text`: Verbatim sentence extracted from public text providing the evidence.
   - `location_evidence_url`: Traceable source permalink.
5. **No Hallucinations / Guessing**: If location is unverified, fields are recorded as `"Unverified"`, never guessed.
6. **Zero Unverified Strong Signal Leads**: Any lead scoring > 70 whose residence is `LOCATION_UNVERIFIED` or `ORIGIN_ONLY` is capped at **`Needs Validation`**, never `Strong Signal`.
7. **Intent Preserved**: Clear buying intent with unverified location is placed into **`Needs Validation`**, never `Reject`.

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

### Geographic Verification Breakdown (Unique Prospects: 249)
| Location Verification Status | Count | Share (%) | Description |
| :--- | :---: | :---: | :--- |
| **`CURRENT_RESIDENT`** | **106** | **42.6%** | Explicit, attributable current residence in KA, KL, TN, TS, or AP |
| **`ORIGIN_ONLY`** | **15** | **6.0%** | Roots, native town, or heritage without current South Indian residency |
| **`LOCATION_UNVERIFIED`** | **126** | **50.6%** | No attributable location statement in text (subreddit/language ignored) |
| **`OUTSIDE_TARGET`** | **2** | **0.8%** | Explicit current residence outside target geography (Delhi NCR, etc.) |

---

### Before vs. After Lead Reclassification Summary

| Qualification Status | Before Strict Geo Rules | After Strict Geo Rules | Net Change | Reclassification Rationale |
| :--- | :---: | :---: | :---: | :--- |
| **Strong Signal** | **50** | **24** | **-26** | Only leads with explicit, attributable `CURRENT_RESIDENT` status qualify |
| **Needs Validation** | **105** | **133** | **+28** | Captures high-intent buyers whose location is unverified or origin-only |
| **Reject** | **94** | **92** | **-2** | Pruned brokers, job seekers, outside-target leads, and deleted posts |
| **Strong Signal with Unverified Location** | **26** | **0** | **-26** | **100% Verification Guarantee** (0 unverified in Strong Signal) |

---

### Geographic Spread of Master Qualified Leads (24 Verified Residents)
- **Karnataka**: 9 (37.5%) — Bengaluru, Mysuru, Mangaluru, Hubballi
- **Tamil Nadu**: 5 (20.8%) — Chennai, Coimbatore, Madurai, Trichy
- **Kerala**: 4 (16.7%) — Kochi, Thiruvananthapuram, Kozhikode, Thrissur
- **Andhra Pradesh**: 4 (16.7%) — Visakhapatnam, Vijayawada, Guntur, Tirupati
- **Telangana**: 2 (8.3%) — Hyderabad, Secunderabad, Warangal

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

The output will automatically generate / update in `results/`:
- `results/all_candidates.csv` (All unique candidate records evaluated)
- `results/qualified_dubai_leads.xlsx` (Master workbook with `Qualified Leads` & `Top 5 Shortlist` tabs)
- `results/top_5_leads.csv` (Top 5 human-reviewed Strong Signal leads in CSV format)
- `results/audit_report.json` (Reconciled funnel report & manual review sampling)
- `results/processed.json` (Registry of processed input files and `PROCESSED` status)

> **Incremental Pipeline Execution**:
> The orchestrator tracks processed files in `results/processed.json`. If you add new raw JSON or CSV files to `input/` and re-run `python -m workflow.main`, the pipeline automatically identifies only the new unprocessed files, parses their leads, merges them into existing results, and updates all deliverables without redundant re-processing.

### 3. Run Automated Tests
To run the automated test suite (45 unit tests):

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
│   │   ├── deduplicator.py                    # Intra-platform deduplication by handle and URL
│   │   ├── geo_matcher.py                     # South India NER & geocoding resolver
│   │   ├── intent_classifier.py               # 100-point weighted scoring and mandatory gates engine
│   │   ├── source_verifier.py                 # Source URL existence, permitted use & post checker
│   │   ├── evidence_auditor.py                # Evidence auditing, anomaly flagging & manual sampling
│   │   └── file_tracker.py                    # Processed file tracking & incremental state management
│   └── main.py                                # CLI orchestrator
├── results/
│   ├── all_candidates.csv                     # Master evaluated candidates CSV
│   ├── qualified_dubai_leads.xlsx             # Master Excel (Qualified >= 75 + Top 5 Shortlist)
│   ├── top_5_leads.csv                        # Top 5 human-reviewed Strong Signal leads (CSV)
│   ├── audit_report.json                      # Comprehensive audit & reconciled funnel metrics JSON
│   └── processed.json                         # Processed input files tracking (incremental pipeline state)
├── docs/
│   └── methodology_and_report.md              # In-depth report on sourcing, rules, and ethics
└── tests/
    ├── test_dedup.py                          # Tests for deduplication logic
    ├── test_geo.py                            # Tests for geographic entity extraction
    ├── test_classifier.py                     # Tests for qualification and broker rejection
    ├── test_source_verifier.py                # Tests for Reddit URL existence and deletion filtering
    ├── test_harvesters.py                     # Tests for CSV-based harvesters (zero hardcoded data)
    ├── test_audit.py                          # Tests for evidence auditing, dates, and funnel reconciliation
    └── test_incremental.py                    # Tests for processed.json tracking and incremental execution
```

---

## Ethics & Compliance Principles

- **Exclusively Public & Authorised Sources**: No private accounts, protected groups, or login paywalls were breached.
- **Zero PII Harvesting**: No private email addresses, personal phone numbers, or national identity documents were collected.
- **No Unsolicited Outreach**: Zero automated contact or unsolicited outreach is performed.
- **Data Integrity**: In accordance with project instructions, no data is invented or fabricated to inflate volume.

