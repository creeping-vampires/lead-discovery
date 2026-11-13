# Dubai Real Estate Lead Discovery and Qualification Workflow (South India)

A Python pipeline to discover, normalize, qualify, audit, and export prospective Dubai real estate buyers and investors based in South India (Karnataka, Kerala, Tamil Nadu, Telangana, and Andhra Pradesh).

The pipeline filters raw social discussions, excludes brokers, channel partners, and spam, and categorizes candidates into **Strong Signal**, **Needs Validation**, and **Reject** with traceable source URLs, evidence quotes, timestamps, and explicit qualification reasoning.

---

## Input and Output Architecture

### 1. `input/` Directory (Raw Discovered Candidates)
Contains raw candidate CSV and JSON files ingested by the pipeline:
- [`input/raw_discovered_candidates.csv`](input/raw_discovered_candidates.csv): Master tabular CSV containing discovered candidate records across Reddit, YouTube, and real estate forums before filtering, deduplication, or scoring.
- Additional batch files (e.g. `raw_leads_batch_2.csv`, `raw_leads_batch_south_india_dubai.json`) are processed incrementally.
- Harvesters (`RedditHarvester`, `YouTubeHarvester`, `ForumHarvester`) parse records dynamically without hardcoded prospect arrays.

### 2. `results/` Directory (Canonical Pipeline Deliverables)
All generated outputs and audit records reside in `results/`:
- [`results/all_candidates.csv`](results/all_candidates.csv): All unique candidate records evaluated, with extracted evidence, source verification flags, and qualification status.
- [`results/qualified_dubai_leads.xlsx`](results/qualified_dubai_leads.xlsx): Master formatted Excel workbook containing all qualified Strong Signal leads scoring >= 75 points with verified `CURRENT_RESIDENT` status, across two formatted worksheets (`Qualified Leads` and `Top 5 Shortlist`).
- [`results/top_5_leads.csv`](results/top_5_leads.csv): The top 5 human-reviewed Strong Signal leads in CSV format with auditor verification notes.
- [`results/audit_report.json`](results/audit_report.json): Machine-readable reconciliation report detailing discovery totals, deduplication delta, pre-freshness vs final breakdown, 180-day downgrade counts, and stratified sampling.
- [`results/processed.json`](results/processed.json): Incremental processing registry recording filename, status (`PROCESSED`), records count, and MD5 checksum of every processed input file.

---

## 100-Point Weighted Scoring Model & Mandatory Evidence Gates

Lead qualification is governed by 5 mandatory gates and an objective 100-point weighted scoring model configured in [`workflow/config.py`](workflow/config.py):

### 5 Mandatory Strong Signal Requirements (All Must Pass)
1. **Explicit Personal Intent**: First-person statement of intent to purchase or invest in Dubai real estate (`"actively looking to purchase"`, `"planning to buy"`, `"ready to sign"`, `"want to invest"`, `"booked a token"`). General ROI queries, Golden Visa questions, profession alone, or financial capacity alone never satisfy intent.
2. **Verifiable Source URL**: Traceable public URL and original text, excluding author-deleted (`[deleted]`) or moderator-removed (`[removed]`) posts.
3. **Verified Current Residence**: Traceable evidence of current residence in target South Indian states (`location_verification_status == "CURRENT_RESIDENT"`).
4. **Freshness Window**: Buying-intent signal dated within the last 180 days (<= 180 days).
5. **No Broker or Promotional Activity**: Absence of broker, agent, seller, or job-seeker behavior.

### 100-Point Weighted Scoring Rubric

| Criteria Dimension | Score Points | Qualifying Standard |
| :--- | :---: | :--- |
| **Explicit Personal Purchase Intent** | **30 pts** | First-person statement to buy or invest in Dubai property |
| **Purchase Readiness** | **20 pts** | Transactional step underway (token paid, down payment, LRS 15CA, SPA, travel) |
| **Budget or Financing Requirements** | **15 pts** | Stated budget in AED, INR, USD, or explicit payment plan structure |
| **Purchase Timeline** | **15 pts** | Concrete purchase horizon (immediate, next month, this quarter, by Q3) |
| **Specific Project or Property Requirements** | **10 pts** | Named Dubai micro-market (JVC, Marina, Business Bay), developer, or unit type |
| **Freshness** | **10 pts** | Signal timestamp within the last 180 days (<= 180 days) |
| **Total Maximum Score** | **100 pts** | Theoretical maximum composite score |

### Classification Rules
- **`STRONG_SIGNAL`**: All 5 mandatory gates pass AND score >= 75.
- **`NEEDS_VALIDATION`**: Plausible buyer but one or more requirements are unverified, signal is stale (> 180 days), or score < 75.
- **`REJECT`**: Confirmed broker or promoter, irrelevant inquiry, no meaningful buying intent, or confirmed outside target geography.

---

## Strict Geographic Evidence Verification Engine

A dedicated geographic verifier ([`workflow/processors/geo_matcher.py`](workflow/processors/geo_matcher.py)) enforces geographic qualification:
1. **Attributable Current Residence Only**: A prospect qualifies as South India-based only if there is explicit, attributable evidence in the public text that they currently live, reside, or work in Karnataka, Kerala, Tamil Nadu, Telangana, or Andhra Pradesh.
2. **Negative Inferences Barred**: Current residence is never inferred from subreddit membership (e.g. posting on `r/bangalore`), language (e.g. Tamil or Kannada), birthplace, surname, profession, or posting/event location (e.g. attending a property roadshow).
3. **Four Location Statuses**:
   - `CURRENT_RESIDENT`: Explicit textual evidence of living, working, or residing in target states (e.g. "Living in HSR Layout Bangalore", "Resident of Kochi", "Working in OMR Chennai"). Eligible for `Strong Signal`.
   - `ORIGIN_ONLY`: Evidence of origin, hometown, or native roots without affirmative current local residence (e.g. "Thrissur native", "From Kannur holding NRE funds", "Malayali in Dubai").
   - `LOCATION_UNVERIFIED`: No attributable location statement in text.
   - `OUTSIDE_TARGET`: Explicit current residence outside target states (e.g. "Living in South Delhi / Gurgaon", "Resident of Mumbai"). Disqualified immediately.
4. **Audit Fields Stored for Every Prospect**:
   - `location_verification_status`: One of the 4 standard statuses.
   - `location_evidence_text`: Verbatim sentence extracted from public text providing the evidence.
   - `location_evidence_url`: Traceable source permalink.
5. **No Speculation**: If location is unverified, fields are recorded as `"Unverified"`, never guessed.
6. **Zero Unverified Strong Signal Leads**: Any lead scoring >= 75 whose residence is `LOCATION_UNVERIFIED` or `ORIGIN_ONLY` is placed in `Needs Validation`, never `Strong Signal`.
7. **Intent Preserved**: Clear buying intent with unverified location is placed into `Needs Validation`, never `Reject`.

---

## Source & URL Verification Engine

A dedicated verification engine ([`workflow/processors/source_verifier.py`](workflow/processors/source_verifier.py)) audits candidate URLs and text:
1. **URL Existence & Structure**: Validates that every link is a well-formed permalink with a valid domain and post identifier.
2. **Author Deletion Detection**: Detects accounts deleted by the author (`u/[deleted]`, `[deleted]`) and flags them.
3. **Moderator & Spam Removal Detection**: Identifies posts and comments removed by community moderators or spam filters (`[removed]`).
4. **Automated Disqualification**: Deleted or removed posts receive `score = 0` and `status = Reject` with a recorded audit reason.
5. **Live Probing**: Optional HTTP verification can be toggled via `--check-live` in CLI.

---

## Funnel & Metrics Summary

### Reconciled Funnel Metrics (Unique Prospects: 253)

| Funnel Stage | Count | Share (%) | Description |
| :--- | :---: | :---: | :--- |
| **Total Discovered Records** | **264** | - | Ingested across all input files |
| **Duplicates Pruned** | **11** | - | Intra-platform canonical handle and URL deduplication |
| **Unique Candidates Evaluated** | **253** | **100.0%** | Distinct candidate records |
| **- Strong Signal (Qualified)** | **24** | **9.5%** | Passed all 5 mandatory gates with score >= 75 |
| **- Needs Validation** | **127** | **50.2%** | Plausible buyers, unverified location, or stale signals |
| **- Reject** | **102** | **40.3%** | Brokers, spam, dead links, or outside target geography |

Reconciliation: `253 == 24 + 127 + 102` (Delta: 0, 100% reconciled).

### Geographic Verification Breakdown (Unique Prospects: 253)

| Location Verification Status | Count | Share (%) | Description |
| :--- | :---: | :---: | :--- |
| **`CURRENT_RESIDENT`** | **106** | **41.9%** | Attributable current residence in KA, KL, TN, TS, or AP |
| **`ORIGIN_ONLY`** | **17** | **6.7%** | Roots or heritage without verified South Indian residency |
| **`LOCATION_UNVERIFIED`** | **128** | **50.6%** | No attributable location statement in text |
| **`OUTSIDE_TARGET`** | **2** | **0.8%** | Explicit current residence outside target states |

### Freshness Audit Breakdown (180-Day Rule)
- **Pre-Freshness Strong Signal**: 32 records
- **Downgraded by 180-Day Rule**: 8 records (scored >= 75 but buying signal was > 180 days old; downgraded to `Needs Validation`)
- **Final Strong Signal Count**: 24 records (100% compliant with freshness and geographic criteria)

### Geographic Spread of Master Qualified Leads (24 Verified Residents)
- **Karnataka**: 7 (29.2%) in Bengaluru, Mysuru, Mangaluru, Hubballi
- **Tamil Nadu**: 5 (20.8%) in Chennai, Coimbatore, Madurai, Tiruchirappalli
- **Telangana**: 4 (16.7%) in Hyderabad, Secunderabad, Warangal
- **Andhra Pradesh**: 4 (16.7%) in Visakhapatnam, Vijayawada, Guntur, Tirupati
- **Kerala**: 4 (16.7%) in Kochi, Thiruvananthapuram, Kozhikode, Thrissur

---

## Setup & Execution Instructions

### Prerequisites
- Python 3.9+ on macOS, Linux, or Windows.

### 1. Environment Setup
```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Run the Batch Pipeline
To run discovery, normalization, geo matching, intent scoring, deduplication, and export:
```bash
python -m workflow.main
```

Deliverables are generated in `results/`:
- `results/all_candidates.csv`
- `results/qualified_dubai_leads.xlsx`
- `results/top_5_leads.csv`
- `results/audit_report.json`
- `results/processed.json`

### 3. Launch the Web UI Dashboard
A web dashboard is included to inspect leads, review evidence, approve or reject prospects, and trigger workflow runs:
```bash
python app.py --port 5001
```
Open `http://127.0.0.1:5001` in your browser.

Features:
- Segmented views for Qualified Leads, Needs Review, All Candidates, and Processed Files.
- Lead Review Modal: Inspect verbatim statements, 6-point evidence breakdown, adjust score, update location evidence, and click "Approve as Qualified Lead" to update all deliverables on disk.
- Pipeline Trigger: Run pipeline incrementally or check "Reset & Reprocess All" to reset `processed.json` and rerun from scratch.

### 4. Run Automated Test Suite
To run all 54 unit tests:
```bash
python -m unittest discover tests
```

---

## System Architecture

```
real-estate-leads-assignment/
├── README.md                                  # Setup, overview, and verification documentation
├── requirements.txt                           # Dependencies (pandas, openpyxl, python-dateutil, flask)
├── app.py                                     # UI dashboard entrypoint
├── input/
│   ├── raw_discovered_candidates.csv          # Base discovery dataset
│   ├── raw_leads_batch_2.csv                  # Incremental batch 1
│   ├── raw_leads_batch_south_india_dubai.csv  # Incremental batch 2 (CSV)
├── workflow/
│   ├── __init__.py
│   ├── config.py                              # Configuration, gates, thresholds, and keyword maps
│   ├── harvesters/                            # Harvesters parse from raw input files
│   │   ├── __init__.py
│   │   ├── base.py                            # Base harvester and platform router
│   │   ├── reddit_harvester.py                # Reddit discussion parser
│   │   ├── youtube_harvester.py               # YouTube comment feed parser
│   │   └── forum_harvester.py                 # IREF, Quora, and Expo forum parser
│   ├── processors/
│   │   ├── __init__.py
│   │   ├── deduplicator.py                    # Intra-platform handle and URL deduplication
│   │   ├── geo_matcher.py                     # South India NER and geocoding verifier
│   │   ├── intent_classifier.py               # 100-point weighted scoring and mandatory gates engine
│   │   ├── source_verifier.py                 # URL existence, permitted use, and post verification
│   │   ├── evidence_auditor.py                # Evidence auditing, anomaly flagging, and manual sampling
│   │   └── file_tracker.py                    # Processed file tracking and incremental state management
│   └── main.py                                # CLI orchestrator
├── ui/
│   ├── __init__.py
│   ├── app.py                                 # Flask REST API server and review controllers
│   └── templates/
│       └── index.html                         # Interactive leads and review dashboard
├── results/
│   ├── all_candidates.csv                     # Master evaluated candidates CSV (253 rows)
│   ├── qualified_dubai_leads.xlsx             # Master Excel (Qualified >= 75 + Top 5 Shortlist)
│   ├── top_5_leads.csv                        # Top 5 human-reviewed Strong Signal leads (CSV)
│   ├── audit_report.json                      # Comprehensive audit and reconciled funnel metrics JSON
│   └── processed.json                         # Processed input files tracking (incremental state)
├── docs/
│   └── methodology_and_report.md              # Methodology, sourcing rationale, and compliance
└── tests/
    ├── test_dedup.py                          # Tests for deduplication logic
    ├── test_geo.py                            # Tests for geographic entity extraction
    ├── test_classifier.py                     # Tests for qualification and broker rejection
    ├── test_source_verifier.py                # Tests for URL existence and deletion filtering
    ├── test_harvesters.py                     # Tests for file harvesters
    ├── test_audit.py                          # Tests for evidence auditing, dates, and funnel reconciliation
    ├── test_incremental.py                    # Tests for processed.json tracking and incremental execution
    └── test_ui.py                             # Tests for Flask UI API routes and review synchronization
```

---

## Ethics and Compliance Principles

- **Exclusively Public Sources**: The pipeline processes only publicly indexed discussions. No private accounts, protected groups, or login paywalls were accessed.
- **Zero PII Harvesting**: No private email addresses, personal phone numbers, or national identity documents were collected.
- **No Unsolicited Contact**: No automated outreach, direct messaging, or contact initiation is performed.
- **Data Integrity**: In accordance with pipeline requirements, missing evidence is never fabricated.
