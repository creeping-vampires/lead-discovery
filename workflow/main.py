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
    QUALIFIED_SCORE_THRESHOLD
)
from workflow.harvesters.reddit_harvester import RedditHarvester
from workflow.harvesters.youtube_harvester import YouTubeHarvester
from workflow.harvesters.forum_harvester import ForumHarvester
from workflow.processors.deduplicator import Deduplicator
from workflow.processors.geo_matcher import GeoMatcher
from workflow.processors.intent_classifier import IntentClassifier


def run_pipeline(
    input_dir: str = "input",
    output_dir: str = "results",
    max_freshness_days: int = MAX_FRESHNESS_DAYS,
    qualified_threshold: int = QUALIFIED_SCORE_THRESHOLD
) -> Dict[str, any]:
    print("=" * 70)
    print("DUBAI REAL ESTATE LEAD DISCOVERY & QUALIFICATION PIPELINE (SOUTH INDIA)")
    print(f"Freshness Window: {max_freshness_days} days ({max_freshness_days // 30} months)")
    print(f"Qualification Threshold: Score > {qualified_threshold} / 100 points")
    print("=" * 70)

    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    # 1. Initialize Components
    harvesters = [
        RedditHarvester(),
        YouTubeHarvester(),
        ForumHarvester()
    ]
    deduplicator = Deduplicator()
    geo_matcher = GeoMatcher()
    intent_classifier = IntentClassifier(
        max_freshness_days=max_freshness_days,
        qualified_threshold=qualified_threshold
    )

    # 2. Stage 1: Harvesting raw candidate records
    raw_records: List[Dict[str, any]] = []
    print("\n[Stage 1/4] Harvesting raw candidate prospects across public channels...")
    for h in harvesters:
        harvested = h.harvest()
        print(f"  -> Harvester '{h.name}': Discovered {len(harvested)} raw records")
        raw_records.extend(harvested)

    print(f"Total raw candidate records harvested: {len(raw_records)}")

    # Store raw unadulterated data in input/
    raw_json_path = os.path.join(input_dir, "raw_discovered_candidates.json")
    with open(raw_json_path, "w", encoding="utf-8") as f:
        json.dump(raw_records, f, indent=2, ensure_ascii=False)

    raw_csv_path = os.path.join(input_dir, "raw_discovered_candidates.csv")
    raw_keys = ["public_name_or_handle", "platform", "signal_date", "source_link", "platform_context", "raw_text"]
    with open(raw_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=raw_keys, extrasaction="ignore")
        writer.writeheader()
        for r in raw_records:
            writer.writerow(r)
    print(f"  -> Raw discovery data stored in: {raw_json_path} & {raw_csv_path}")

    # 3. Stage 2: Processing, Geo-Matching & 0-100 Intent Scoring
    print("\n[Stage 2/4] Running Geographic Matching & 0-100 Intent Scoring...")
    processed_records = []
    for rec in raw_records:
        text = rec.get("raw_text", "")
        platform_ctx = rec.get("platform_context", "")

        # Geographic resolution
        geo_info = geo_matcher.extract_geo(text, platform_ctx)

        # Intent classification with strict freshness validation & 0-100 scoring
        sig_date_str = rec.get("signal_date", "").strip()
        classification = intent_classifier.classify_lead(
            text=text,
            geo_info=geo_info,
            platform_context=platform_ctx,
            signal_date_str=sig_date_str
        )

        combined = {
            "public_name_or_handle": rec.get("public_name_or_handle", "").strip(),
            "score": classification["score"],
            "qualification_status": classification["qualification_status"],
            "platform": rec.get("platform", "").strip(),
            "city_state": geo_info["city_state"],
            "state": geo_info["state"],
            "geo_evidence": geo_info["geo_evidence"],
            "source_link": rec.get("source_link", "").strip(),
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

    # 4. Stage 3: Deduplication
    print("\n[Stage 3/4] Deduplicating records by public handle, URL, and content hash...")
    unique_records = deduplicator.process(processed_records)
    print(f"Deduplicated count: {len(unique_records)} unique prospects (pruned {len(processed_records) - len(unique_records)} duplicates)")

    # 5. Stage 4: Filter Qualified Leads (Score > qualified_threshold)
    print(f"\n[Stage 4/4] Filtering qualified leads (Score > {qualified_threshold}/100) and exporting single Excel...")
    qualified_records = [r for r in unique_records if r["score"] > qualified_threshold]
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
        "public_name_or_handle",
        "platform",
        "city_state",
        "geo_evidence",
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
    try:
        import pandas as pd
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter

        # Prepare DataFrame
        df = pd.DataFrame(qualified_records)[export_columns]

        # Write styled Excel workbook
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = f"Qualified Leads (Score > {qualified_threshold})"

        # Header styling
        header_fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        center_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
        left_align = Alignment(horizontal="left", vertical="center", wrap_text=True)

        # Write headers
        headers = [c.replace("_", " ").title() for c in export_columns]
        ws.append(headers)
        ws.row_dimensions[1].height = 28

        for col_num in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col_num)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = center_align

        # Write data rows
        thin_border = Border(
            left=Side(style='thin', color='D9D9D9'),
            right=Side(style='thin', color='D9D9D9'),
            top=Side(style='thin', color='D9D9D9'),
            bottom=Side(style='thin', color='D9D9D9')
        )

        for row_idx, rec in enumerate(qualified_records, start=2):
            ws.row_dimensions[row_idx].height = 24
            row_data = [rec.get(col, "") for col in export_columns]
            ws.append(row_data)

            # Row zebra striping
            row_fill = PatternFill(start_color="F9FAFB" if row_idx % 2 == 0 else "FFFFFF", fill_type="solid")
            for col_idx in range(1, len(row_data) + 1):
                cell = ws.cell(row=row_idx, column=col_idx)
                cell.fill = row_fill
                cell.border = thin_border
                cell.font = Font(name="Calibri", size=10)
                if col_idx in (1, 2, 3, 9, 10):  # ID, Score, Status, Date, Age
                    cell.alignment = center_align
                else:
                    cell.alignment = left_align

        # Adjust column widths automatically
        col_width_map = {
            1: 15,   # Record ID
            2: 10,   # Score
            3: 18,   # Qualification Status
            4: 25,   # Handle
            5: 22,   # Platform
            6: 25,   # City/State
            7: 35,   # Geo Evidence
            8: 40,   # Source Link
            9: 14,   # Signal Date
            10: 16,  # Signal Age Days
            11: 24,  # Budget
            12: 30,  # Preferred Areas
            13: 45,  # Dubai Evidence
            14: 45,  # Qualification Reason
            15: 35   # Unverified Information
        }
        for col_idx, width in col_width_map.items():
            ws.column_dimensions[get_column_letter(col_idx)].width = width

        # Freeze top header row
        ws.freeze_panes = "A2"

        wb.save(excel_path)
        print(f"  -> Single master Excel workbook exported successfully to: {excel_path}")
    except Exception as e:
        print(f"  -> Excel export error: {e}")

    # Metrics Summary
    score_bands = {
        "90 - 100 (Tier 1 Premium)": 0,
        "80 - 89  (Tier 2 High)": 0,
        "71 - 79  (Tier 3 Qualified)": 0
    }
    for r in qualified_records:
        s = r["score"]
        if s >= 90:
            score_bands["90 - 100 (Tier 1 Premium)"] += 1
        elif s >= 80:
            score_bands["80 - 89  (Tier 2 High)"] += 1
        else:
            score_bands["71 - 79  (Tier 3 Qualified)"] += 1

    state_counts = {}
    for r in qualified_records:
        st = r["state"]
        state_counts[st] = state_counts.get(st, 0) + 1

    print("\n" + "=" * 70)
    print("PIPELINE EXECUTION METRICS SUMMARY")
    print("=" * 70)
    print(f"Total Raw Discovered Records (in 'input/'): {len(raw_records)}")
    print(f"Total Unique Candidates Evaluated:        {len(unique_records)}")
    print(f"Qualified Leads (Score > {qualified_threshold}/100):          {len(qualified_records)} (in 'results/qualified_dubai_leads.xlsx')")
    print("\nQualified Leads Score Distribution (0 to 100 scale):")
    for band, count in score_bands.items():
        pct = (count / len(qualified_records)) * 100 if qualified_records else 0
        print(f"  - {band:30s}: {count:3d} ({pct:5.1f}%)")

    print("\nGeographic Spread of Qualified Leads:")
    for st, count in sorted(state_counts.items(), key=lambda x: x[1], reverse=True):
        pct = (count / len(qualified_records)) * 100 if qualified_records else 0
        print(f"  - {st:25s}: {count:3d} ({pct:5.1f}%)")

    return {
        "total_raw": len(raw_records),
        "total_unique": len(unique_records),
        "total_qualified": len(qualified_records),
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
        "--input-dir",
        type=str,
        default="input",
        help="Input directory for raw harvested records (default: input)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="results",
        help="Output directory containing the single qualified leads Excel (default: results)"
    )
    args = parser.parse_args()
    run_pipeline(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        max_freshness_days=args.freshness_days,
        qualified_threshold=args.min_score
    )
