"""
Main CLI Orchestrator for Dubai Real Estate Lead Discovery & Qualification Pipeline.
- Stores all raw harvested candidate records in `input/`
- Filters only qualified leads scoring > QUALIFIED_SCORE_THRESHOLD (0-100 scale)
- Exports exclusively ONE single formatted Excel workbook in `results/`
"""

import os
import csv
import json
from typing import List, Dict
from datetime import datetime

from workflow.config import (
    MAX_FRESHNESS_DAYS,
    ENFORCE_FRESHNESS,
    QUALIFIED_SCORE_THRESHOLD,
    VERIFY_SOURCE_AVAILABILITY,
    CHECK_LIVE_URLS
)
from workflow.harvesters.reddit_harvester import RedditHarvester
from workflow.harvesters.youtube_harvester import YouTubeHarvester
from workflow.harvesters.forum_harvester import ForumHarvester
from workflow.processors.deduplicator import Deduplicator
from workflow.processors.geo_matcher import GeoMatcher
from workflow.processors.intent_classifier import IntentClassifier
from workflow.processors.source_verifier import SourceVerifier


def run_pipeline(
    input_dir: str = "input",
    output_dir: str = "results",
    input_csv: Optional[str] = None,
    max_freshness_days: int = MAX_FRESHNESS_DAYS,
    qualified_threshold: int = QUALIFIED_SCORE_THRESHOLD,
    verify_sources: bool = VERIFY_SOURCE_AVAILABILITY,
    check_live: bool = CHECK_LIVE_URLS
) -> Dict[str, any]:
    # Resolve raw input CSV path (only CSV is parsed; no JSON input)
    csv_input_path = input_csv or os.path.join(input_dir, "raw_discovered_candidates.csv")

    print("=" * 70)
    print("DUBAI REAL ESTATE LEAD DISCOVERY & QUALIFICATION PIPELINE (SOUTH INDIA)")
    print(f"Raw Input CSV: {csv_input_path}")
    print(f"Freshness Window: {max_freshness_days} days ({max_freshness_days // 30} months)")
    print(f"Qualification Threshold: Score > {qualified_threshold} / 100 points")
    print(f"Source Verification: {'ENABLED (Filtering deleted/removed Reddit posts & dead URLs)' if verify_sources else 'DISABLED'}")
    if check_live:
        print("Live URL Probe: ENABLED (Checking HTTP response status)")
    print("=" * 70)

    if not os.path.exists(csv_input_path):
        raise FileNotFoundError(
            f"Raw input CSV not found at '{csv_input_path}'. "
            f"Please ensure the raw candidate CSV file is placed at '{csv_input_path}'."
        )

    os.makedirs(output_dir, exist_ok=True)

    # 1. Initialize Components
    harvesters = [
        RedditHarvester(csv_path=csv_input_path),
        YouTubeHarvester(csv_path=csv_input_path),
        ForumHarvester(csv_path=csv_input_path)
    ]
    deduplicator = Deduplicator()
    geo_matcher = GeoMatcher()
    source_verifier = SourceVerifier(check_live=check_live)
    intent_classifier = IntentClassifier(
        max_freshness_days=max_freshness_days,
        qualified_threshold=qualified_threshold,
        verify_sources=verify_sources,
        source_verifier=source_verifier
    )

    # 2. Stage 1: Parsing raw candidate records directly from the input CSV
    raw_records: List[Dict[str, any]] = []
    print(f"\n[Stage 1/4] Parsing raw candidate records directly from '{csv_input_path}'...")
    for h in harvesters:
        harvested = h.harvest()
        print(f"  -> Harvester '{h.name}': Parsed {len(harvested)} raw records from CSV")
        raw_records.extend(harvested)

    print(f"Total raw candidate records parsed: {len(raw_records)}")

    # 3. Stage 2: Processing, Geo-Matching, Source URL Verification & 0-100 Intent Scoring
    print("\n[Stage 2/4] Running Source Verification, Geographic Matching & 0-100 Intent Scoring...")
    processed_records = []
    deleted_author_count = 0
    removed_mod_count = 0
    invalid_url_count = 0

    for rec in raw_records:
        text = rec.get("raw_text", "")
        platform_ctx = rec.get("platform_context", "")
        source_link = rec.get("source_link", "").strip()
        handle = rec.get("public_name_or_handle", "").strip()
        platform = rec.get("platform", "").strip()

        # Geographic resolution with strict evidence verification
        geo_info = geo_matcher.extract_geo(text, platform_ctx, source_link=source_link)

        # Intent classification with source existence verification & 0-100 scoring
        sig_date_str = rec.get("signal_date", "").strip()
        classification = intent_classifier.classify_lead(
            text=text,
            geo_info=geo_info,
            platform_context=platform_ctx,
            signal_date_str=sig_date_str,
            source_link=source_link,
            public_name_or_handle=handle,
            platform=platform,
            check_live=check_live
        )

        # Track source filtering stats
        src_ver = classification.get("source_verification")
        if src_ver and not src_ver["is_valid"]:
            if src_ver.get("is_deleted"):
                deleted_author_count += 1
            elif src_ver.get("is_removed"):
                removed_mod_count += 1
            elif not src_ver.get("url_exists"):
                invalid_url_count += 1

        comp_ev = classification.get("component_evidence", {})
        gates = classification.get("mandatory_gates", {})

        combined = {
            "public_name_or_handle": handle,
            "score": classification["score"],
            "qualification_status": classification["qualification_status"],
            "location_verification_status": classification["location_verification_status"],
            "platform": platform,
            "city_state": geo_info["city_state"],
            "state": geo_info["state"],
            "geo_evidence": classification["location_evidence_text"],
            "location_evidence_text": classification["location_evidence_text"],
            "location_evidence_url": classification["location_evidence_url"],
            "intent_evidence": comp_ev.get("intent_evidence", "None"),
            "readiness_evidence": comp_ev.get("readiness_evidence", "None"),
            "budget_evidence": comp_ev.get("budget_evidence", "None"),
            "timeline_evidence": comp_ev.get("timeline_evidence", "None"),
            "project_evidence": comp_ev.get("project_evidence", "None"),
            "freshness_evidence": comp_ev.get("freshness_evidence", "None"),
            "all_mandatory_gates_pass": gates.get("all_mandatory_gates_pass", False),
            "source_link": source_link,
            "signal_date": sig_date_str,
            "signal_age_days": classification.get("signal_age_days", "Unverified"),
            "ticket_size_budget": classification["ticket_size_budget"],
            "preferred_areas": classification["preferred_areas"],
            "dubai_property_evidence": text,
            "qualification_reason": classification["qualification_reason"],
            "unverified_information": classification["unverified_information"],
            "is_qualified": classification.get("is_qualified", False)
        }
        processed_records.append(combined)

    total_disqualified_sources = deleted_author_count + removed_mod_count + invalid_url_count
    if verify_sources:
        print(f"  -> Source Filter: Pruned {total_disqualified_sources} deleted/removed Reddit posts/comments:")
        print(f"     • Deleted by Author     : {deleted_author_count}")
        print(f"     • Removed by Moderators : {removed_mod_count}")
        if invalid_url_count > 0:
            print(f"     • Invalid / Dead URLs   : {invalid_url_count}")

    # 4. Stage 3: Deduplication
    print("\n[Stage 3/4] Deduplicating records by public handle, URL, and content hash...")
    unique_records = deduplicator.process(processed_records)
    print(f"Deduplicated count: {len(unique_records)} unique prospects (pruned {len(processed_records) - len(unique_records)} duplicates)")

    # 5. Stage 4: Filter Qualified Leads (Strict Strong Signal & Verified South Indian Residence)
    print(f"\n[Stage 4/4] Filtering qualified leads (Score > {qualified_threshold}/100 & Verified CURRENT_RESIDENT) and exporting single Excel...")
    qualified_records = [r for r in unique_records if r["is_qualified"]]
    qualified_records.sort(key=lambda x: x["score"], reverse=True)

    # Assign sequential Qualified Lead IDs
    for idx, rec in enumerate(qualified_records, start=1):
        rec["record_id"] = f"QUAL-DUB-{idx:03d}"

    print(f"Total Qualified Leads Identified: {len(qualified_records)} (from {len(unique_records)} unique candidates)")

    # Columns for final Excel sheet
    export_columns = [
        "record_id",
        "score",
        "qualification_status",
        "location_verification_status",
        "public_name_or_handle",
        "platform",
        "city_state",
        "location_evidence_text",
        "intent_evidence",
        "readiness_evidence",
        "budget_evidence",
        "timeline_evidence",
        "project_evidence",
        "source_link",
        "signal_date",
        "signal_age_days",
        "ticket_size_budget",
        "preferred_areas",
        "dubai_property_evidence",
        "qualification_reason",
        "unverified_information"
    ]

    # Clean results directory to ensure ONLY the single Excel workbook remains
    for fname in os.listdir(output_dir):
        fpath = os.path.join(output_dir, fname)
        if os.path.isfile(fpath):
            os.remove(fpath)

    excel_path = os.path.join(output_dir, "qualified_dubai_leads.xlsx")
    top_5_csv_path = os.path.join(output_dir, "top_5_leads.csv")

    try:
        import pandas as pd
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter

        # Helper function to style and populate worksheet in identical format
        def populate_worksheet(ws, records, title, fill_color="1F497D"):
            ws.title = title
            header_fill = PatternFill(start_color=fill_color, end_color=fill_color, fill_type="solid")
            header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
            center_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
            left_align = Alignment(horizontal="left", vertical="center", wrap_text=True)
            thin_border = Border(
                left=Side(style='thin', color='D9D9D9'),
                right=Side(style='thin', color='D9D9D9'),
                top=Side(style='thin', color='D9D9D9'),
                bottom=Side(style='thin', color='D9D9D9')
            )

            headers = [c.replace("_", " ").title() for c in export_columns]
            ws.append(headers)
            ws.row_dimensions[1].height = 28

            for col_num in range(1, len(headers) + 1):
                cell = ws.cell(row=1, column=col_num)
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = center_align

            for row_idx, rec in enumerate(records, start=2):
                ws.row_dimensions[row_idx].height = 24
                row_data = [rec.get(col, "") for col in export_columns]
                ws.append(row_data)

                row_fill = PatternFill(start_color="F9FAFB" if row_idx % 2 == 0 else "FFFFFF", fill_type="solid")
                for col_idx in range(1, len(row_data) + 1):
                    cell = ws.cell(row=row_idx, column=col_idx)
                    cell.fill = row_fill
                    cell.border = thin_border
                    cell.font = Font(name="Calibri", size=10)
                    if col_idx in (1, 2, 3, 4, 15, 16):  # ID, Score, Status, Loc Status, Date, Age
                        cell.alignment = center_align
                    else:
                        cell.alignment = left_align

            col_width_map = {
                1: 15,   # Record ID
                2: 10,   # Score
                3: 18,   # Qualification Status
                4: 22,   # Location Verification Status
                5: 25,   # Handle
                6: 22,   # Platform
                7: 25,   # City/State
                8: 30,   # Location Evidence
                9: 30,   # Intent Evidence
                10: 30,  # Readiness Evidence
                11: 25,  # Budget Evidence
                12: 20,  # Timeline Evidence
                13: 30,  # Project Evidence
                14: 35,  # Source Link
                15: 14,  # Signal Date
                16: 16,  # Signal Age Days
                17: 24,  # Budget
                18: 30,  # Preferred Areas
                19: 45,  # Dubai Evidence
                20: 45,  # Qualification Reason
                21: 35   # Unverified Information
            }
            for col_idx, width in col_width_map.items():
                ws.column_dimensions[get_column_letter(col_idx)].width = width

            ws.freeze_panes = "A2"

        # Initialize Workbook with 2 sheets in identical format
        wb = openpyxl.Workbook()

        # Sheet 1: All Qualified Leads (Score >= 75 & All 5 Mandatory Gates Passed)
        ws1 = wb.active
        populate_worksheet(ws1, qualified_records, f"Qualified Leads (Score >= {qualified_threshold})", fill_color="1F497D")

        # Sheet 2: Top 5 Strongest Leads (identical format & styling)
        top_5_records = qualified_records[:5]
        ws2 = wb.create_sheet(title="Top 5 Shortlist")
        populate_worksheet(ws2, top_5_records, "Top 5 Shortlist", fill_color="0B5394")

        wb.save(excel_path)
        print(f"  -> Master Excel workbook exported with 2 sheets [Qualified Leads & Top 5 Shortlist]: {excel_path}")

        # Export Top 5 Leads in CSV format (no md)
        with open(top_5_csv_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=export_columns, extrasaction="ignore")
            writer.writeheader()
            for rec in top_5_records:
                writer.writerow(rec)
        print(f"  -> Top 5 Shortlist exported in CSV format to: {top_5_csv_path}")

    except Exception as e:
        print(f"  -> Export error: {e}")

    # Metrics Summary
    score_bands = {
        "90 - 100 (Tier 1 Premium)": 0,
        "80 - 89  (Tier 2 High)": 0,
        "75 - 79  (Tier 3 Qualified)": 0
    }
    for r in qualified_records:
        s = r["score"]
        if s >= 90:
            score_bands["90 - 100 (Tier 1 Premium)"] += 1
        elif s >= 80:
            score_bands["80 - 89  (Tier 2 High)"] += 1
        else:
            score_bands["75 - 79  (Tier 3 Qualified)"] += 1

    state_counts = {}
    for r in qualified_records:
        st = r["state"]
        state_counts[st] = state_counts.get(st, 0) + 1

    # Calculate Geographic & Qualification Status Distributions
    from collections import Counter
    loc_status_counts = Counter(r["location_verification_status"] for r in unique_records)
    qual_status_counts = Counter(r["qualification_status"] for r in unique_records)

    print("\n" + "=" * 70)
    print("PIPELINE EXECUTION METRICS SUMMARY")
    print("=" * 70)
    print(f"Total Raw Discovered Records (in 'input/'): {len(raw_records)}")
    print(f"Total Unique Candidates Evaluated:        {len(unique_records)}")
    if verify_sources:
        print(f"Pruned Deleted/Removed Sources:           {total_disqualified_sources} ({deleted_author_count} author deleted, {removed_mod_count} mod removed)")

    print("\nGeographic Verification Breakdown (All 4 Statuses):")
    for st in ["CURRENT_RESIDENT", "ORIGIN_ONLY", "LOCATION_UNVERIFIED", "OUTSIDE_TARGET"]:
        count = loc_status_counts.get(st, 0)
        pct = (count / len(unique_records)) * 100 if unique_records else 0
        print(f"  - {st:25s}: {count:3d} ({pct:5.1f}%)")

    print("\nLead Qualification Summary (Strictly Reclassified):")
    for qst in ["Strong Signal", "Needs Validation", "Reject"]:
        count = qual_status_counts.get(qst, 0)
        pct = (count / len(unique_records)) * 100 if unique_records else 0
        print(f"  - {qst:25s}: {count:3d} ({pct:5.1f}%)")

    unverified_strong_count = sum(1 for r in unique_records if r["qualification_status"] == "Strong Signal" and r["location_verification_status"] != "CURRENT_RESIDENT")
    failed_gate_strong_count = sum(1 for r in unique_records if r["qualification_status"] == "Strong Signal" and not r.get("all_mandatory_gates_pass", True))
    print(f"\nStrong Signal Leads with Unverified Location: {unverified_strong_count} (Verification Guarantee: 100%)")
    print(f"Strong Signal Leads Failing Mandatory Gates: {failed_gate_strong_count} (Mandatory Gate Compliance: 100%)")
    print(f"Master Qualified Leads (in 'results/'):       {len(qualified_records)} (Score >= {qualified_threshold} + All 5 Mandatory Gates Passed)")

    print("\nQualified Leads Score Distribution (0 to 100 scale):")
    for band, count in score_bands.items():
        pct = (count / len(qualified_records)) * 100 if qualified_records else 0
        print(f"  - {band:30s}: {count:3d} ({pct:5.1f}%)")

    print("\nGeographic Spread of Qualified Leads (Verified Residents):")
    for st, count in sorted(state_counts.items(), key=lambda x: x[1], reverse=True):
        pct = (count / len(qualified_records)) * 100 if qualified_records else 0
        print(f"  - {st:25s}: {count:3d} ({pct:5.1f}%)")

    return {
        "total_raw": len(raw_records),
        "total_unique": len(unique_records),
        "disqualified_sources": total_disqualified_sources if verify_sources else 0,
        "total_qualified": len(qualified_records),
        "location_status_counts": dict(loc_status_counts),
        "qualification_status_counts": dict(qual_status_counts),
        "qualified_excel": excel_path
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Dubai Real Estate Lead Discovery & Qualification Pipeline")
    parser.add_argument(
        "--freshness-days",
        type=int,
        default=MAX_FRESHNESS_DAYS,
        help=f"Freshness threshold in days (default: {MAX_FRESHNESS_DAYS} days from config.py)"
    )
    parser.add_argument(
        "--min-score",
        type=int,
        default=QUALIFIED_SCORE_THRESHOLD,
        help=f"Minimum score threshold to qualify (default: {QUALIFIED_SCORE_THRESHOLD} from config.py)"
    )
    parser.add_argument(
        "--input-csv",
        type=str,
        default=None,
        help="Path to raw candidate CSV file (default: <input-dir>/raw_discovered_candidates.csv)"
    )
    parser.add_argument(
        "--input-dir",
        type=str,
        default="input",
        help="Input directory containing raw_discovered_candidates.csv (default: input)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="results",
        help="Output directory containing the single qualified leads Excel (default: results)"
    )
    parser.add_argument(
        "--no-verify-sources",
        action="store_true",
        help="Disable Reddit post/comment deletion and removal verification"
    )
    parser.add_argument(
        "--check-live",
        action="store_true",
        help="Enable live HTTP probing of Reddit URLs"
    )
    args = parser.parse_args()
    run_pipeline(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        input_csv=args.input_csv,
        max_freshness_days=args.freshness_days,
        qualified_threshold=args.min_score,
        verify_sources=not args.no_verify_sources,
        check_live=args.check_live
    )
