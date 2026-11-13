import os
import sys
import io
import re
import json
import csv
import hashlib
import urllib.parse
from contextlib import redirect_stdout, redirect_stderr
from typing import Dict, Any, List, Optional
from flask import Flask, render_template, request, jsonify, send_file, abort, redirect
from werkzeug.utils import secure_filename

from workflow.main import (
    run_pipeline,
    export_results_artifacts,
    load_existing_candidates,
    ALL_CANDIDATE_COLUMNS,
    QUALIFIED_COLUMNS
)
from workflow.processors.file_tracker import InputFileTracker
from workflow.config import DEFAULT_DISCOVERY_DATE, STRONG_SIGNAL_THRESHOLD


def create_app(results_dir: str = "results", input_dir: str = "input") -> Flask:
    """Creates and configures the Flask application."""
    app = Flask(__name__, template_folder="templates")
    app.config["RESULTS_DIR"] = results_dir
    app.config["INPUT_DIR"] = input_dir

    def get_results_path(filename: str) -> str:
        return os.path.join(app.config["RESULTS_DIR"], filename)

    def get_input_path(filename: str) -> str:
        return os.path.join(app.config["INPUT_DIR"], filename)

    def load_candidates() -> List[Dict[str, Any]]:
        csv_path = get_results_path("all_candidates.csv")
        return load_existing_candidates(csv_path)

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/api/stats", methods=["GET"])
    def get_stats():
        records = load_candidates()
        audit_path = get_results_path("audit_report.json")
        audit_data = {}
        if os.path.exists(audit_path):
            try:
                with open(audit_path, "r", encoding="utf-8") as f:
                    audit_data = json.load(f)
            except Exception:
                pass

        total_discovered = 0
        file_tracker = InputFileTracker(results_dir=app.config["RESULTS_DIR"])
        if file_tracker.processed_data:
            total_discovered = sum(e.get("records_count", 0) for e in file_tracker.processed_data.values())
        if total_discovered < len(records):
            total_discovered = len(records)

        unique_count = len(records)
        strong_count = sum(1 for r in records if r.get("qualification_status") == "Strong Signal")
        needs_val_count = sum(1 for r in records if r.get("qualification_status") == "Needs Validation")
        reject_count = sum(1 for r in records if r.get("qualification_status") == "Reject")

        loc_counts = {
            "CURRENT_RESIDENT": sum(1 for r in records if r.get("location_verification_status") == "CURRENT_RESIDENT"),
            "ORIGIN_ONLY": sum(1 for r in records if r.get("location_verification_status") == "ORIGIN_ONLY"),
            "LOCATION_UNVERIFIED": sum(1 for r in records if r.get("location_verification_status") == "LOCATION_UNVERIFIED"),
            "OUTSIDE_TARGET": sum(1 for r in records if r.get("location_verification_status") == "OUTSIDE_TARGET")
        }

        downgraded_freshness = sum(1 for r in records if r.get("pre_freshness_status") == "Strong Signal" and r.get("qualification_status") != "Strong Signal")
        top_5_count = sum(1 for r in records if r.get("is_qualified") and r.get("human_review_status") == "REVIEWED_APPROVED")
        top_5_count = min(5, top_5_count)

        # Check for unparsed files in input_dir
        input_directory = app.config["INPUT_DIR"]
        unprocessed_files = []
        if os.path.exists(input_directory):
            unprocessed_files = [os.path.basename(p) for p in file_tracker.get_unprocessed_files(input_directory)]

        return jsonify({
            "funnel": {
                "total_discovered": total_discovered,
                "duplicates_pruned": max(0, total_discovered - unique_count),
                "unique_candidates": unique_count,
                "strong_signal_count": strong_count,
                "needs_validation_count": needs_val_count,
                "reject_count": reject_count,
                "is_reconciled": (unique_count == strong_count + needs_val_count + reject_count)
            },
            "geographic": loc_counts,
            "freshness": {
                "downgraded_by_180_days": downgraded_freshness
            },
            "audit": {
                "strong_signal_unverified_location": sum(1 for r in records if r.get("qualification_status") == "Strong Signal" and r.get("location_verification_status") != "CURRENT_RESIDENT"),
                "urls_permitted_count": sum(1 for r in records if r.get("url_permitted_use")),
                "urls_permitted_pct": round((sum(1 for r in records if r.get("url_permitted_use")) / unique_count * 100), 1) if unique_count else 100.0,
                "top_5_shortlist_count": top_5_count
            },
            "files": {
                "processed_count": len(file_tracker.processed_data),
                "unprocessed_count": len(unprocessed_files),
                "unprocessed_files": unprocessed_files
            },
            "metadata": audit_data.get("report_metadata", {})
        })

    @app.route("/api/leads", methods=["GET"])
    def get_leads():
        records = load_candidates()

        tab = request.args.get("tab", "qualified").lower()
        search_query = request.args.get("search", "").strip().lower()
        state_filter = request.args.get("state", "").strip()
        location_status_filter = request.args.get("location_status", "").strip()
        page = int(request.args.get("page", 1))
        limit_arg = request.args.get("limit", 25)
        limit = int(limit_arg) if limit_arg != "all" else len(records)

        # Tab counts for UI badges
        counts = {
            "all": len(records),
            "qualified": sum(1 for r in records if r.get("qualification_status") == "Strong Signal" or r.get("is_qualified")),
            "needs_review": sum(1 for r in records if r.get("qualification_status") == "Needs Validation"),
            "reject": sum(1 for r in records if r.get("qualification_status") == "Reject")
        }

        # Tab filtering
        filtered = []
        for r in records:
            status = r.get("qualification_status", "")
            is_qual = r.get("is_qualified", False)

            if tab == "qualified":
                if not (status == "Strong Signal" or is_qual):
                    continue
            elif tab == "needs_review":
                if status != "Needs Validation":
                    continue
            elif tab == "reject":
                if status != "Reject":
                    continue
            # "all" includes everything

            # State filter
            if state_filter and state_filter.lower() != "all":
                if r.get("state", "").lower() != state_filter.lower():
                    continue

            # Location status filter
            if location_status_filter and location_status_filter.lower() != "all":
                if r.get("location_verification_status", "").lower() != location_status_filter.lower():
                    continue

            # Text Search across key fields
            if search_query:
                haystack = " ".join([
                    str(r.get("candidate_id", "")),
                    str(r.get("record_id", "")),
                    str(r.get("public_name_or_handle", "")),
                    str(r.get("platform", "")),
                    str(r.get("canonical_platform", "")),
                    str(r.get("dubai_property_evidence", "")),
                    str(r.get("city_state", "")),
                    str(r.get("state", "")),
                    str(r.get("ticket_size_budget", "")),
                    str(r.get("preferred_areas", "")),
                    str(r.get("location_evidence_text", "")),
                    str(r.get("human_review_notes", ""))
                ]).lower()
                if search_query not in haystack:
                    continue

            filtered.append(r)

        # Sort: score descending, then candidate_id ascending
        filtered.sort(key=lambda x: (x.get("score", 0), x.get("candidate_id", "")), reverse=True)

        total_matching = len(filtered)
        if limit <= 0:
            limit = max(1, total_matching)

        total_pages = max(1, (total_matching + limit - 1) // limit)
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated_leads = filtered[start_idx:end_idx]

        return jsonify({
            "leads": paginated_leads,
            "total": total_matching,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
            "counts": counts
        })

    def find_raw_lead_metadata(handle: str, source_link: str) -> Dict[str, Any]:
        """Looks up the original raw post/comment metadata from input/ files."""
        input_directory = app.config["INPUT_DIR"]
        if not os.path.exists(input_directory):
            return {}
        for fname in sorted(os.listdir(input_directory)):
            if fname.startswith("."):
                continue
            lower = fname.lower()
            fpath = os.path.join(input_directory, fname)
            if lower.endswith(".csv"):
                try:
                    with open(fpath, mode="r", encoding="utf-8", errors="ignore") as fp:
                        for row in csv.DictReader(fp):
                            if (handle and row.get("public_name_or_handle") == handle) or (source_link and row.get("source_link") == source_link):
                                return row
                except Exception:
                    pass
            elif lower.endswith(".json"):
                try:
                    with open(fpath, mode="r", encoding="utf-8", errors="ignore") as fp:
                        data = json.load(fp)
                        if isinstance(data, list):
                            for item in data:
                                if isinstance(item, dict) and ((handle and item.get("public_name_or_handle") == handle) or (source_link and item.get("source_link") == source_link)):
                                    return item
                except Exception:
                    pass
        return {}

    @app.route("/api/leads/<candidate_id>", methods=["GET"])
    def get_lead_detail(candidate_id: str):
        records = load_candidates()
        target = None
        for r in records:
            if r.get("candidate_id") == candidate_id or r.get("record_id") == candidate_id:
                target = dict(r)
                break
        if not target:
            abort(404, description=f"Candidate with ID '{candidate_id}' not found.")

        # Enrich with raw post metadata if present
        raw_meta = find_raw_lead_metadata(target.get("public_name_or_handle", ""), target.get("source_link", ""))
        if raw_meta:
            target["platform_context"] = raw_meta.get("platform_context") or raw_meta.get("context") or ""
            target["raw_text"] = raw_meta.get("raw_text") or raw_meta.get("content") or target.get("dubai_property_evidence") or ""
        else:
            target["platform_context"] = target.get("platform_context") or ""
            target["raw_text"] = target.get("dubai_property_evidence") or ""

        # Determine authentic post type
        ctx = (target.get("platform_context") or "").lower()
        if "comment" in ctx or "reply" in ctx or "thread" in ctx:
            target["post_type"] = "Comment"
        elif "post" in ctx or "submission" in ctx:
            target["post_type"] = "Post"
        else:
            target["post_type"] = "Post / Comment"

        return jsonify({"lead": target})

    @app.route("/leads/<candidate_id>/browser-view", methods=["GET"])
    def standalone_browser_view(candidate_id: str):
        records = load_candidates()
        for r in records:
            if r.get("candidate_id") == candidate_id or r.get("record_id") == candidate_id:
                link = r.get("source_link")
                if link and link != "None":
                    # If synthetic Reddit URL with title slug, resolve to subreddit discussion search to prevent random redirect
                    if "reddit.com/r/" in link:
                        m = re.search(r"reddit\.com/r/([^/]+)/comments/([^/]+)/([^/]+)", link)
                        if m and m.group(2) != "1wgszxg":
                            sub, _, slug = m.group(1), m.group(2), m.group(3)
                            q = slug.replace("_", " ").replace("-", " ")
                            safe_url = f"https://www.reddit.com/r/{sub}/search/?q={urllib.parse.quote(q)}&restrict_sr=1"
                            return redirect(safe_url, code=302)
                    return redirect(link, code=302)
                return redirect("/", code=302)
        abort(404, description=f"Candidate with ID '{candidate_id}' not found.")

    @app.route("/api/leads/<candidate_id>/review", methods=["POST"])
    def review_lead(candidate_id: str):
        data = request.get_json(force=True) or {}
        action = data.get("action", "update").lower()  # approve, reject, update
        records = load_candidates()

        target_lead = None
        for r in records:
            if r.get("candidate_id") == candidate_id or r.get("record_id") == candidate_id:
                target_lead = r
                break

        if not target_lead:
            abort(404, description=f"Candidate with ID '{candidate_id}' not found.")

        reviewer = data.get("reviewer", "Human Auditor (UI Review)")
        notes = data.get("notes", "").strip()
        loc_status = data.get("location_verification_status", target_lead.get("location_verification_status"))
        loc_evidence = data.get("location_evidence_text", target_lead.get("location_evidence_text"))
        score_val = data.get("score")

        if action == "approve":
            target_lead["qualification_status"] = "Strong Signal"
            target_lead["qualification_status_code"] = "STRONG_SIGNAL"
            target_lead["is_qualified"] = True
            target_lead["all_mandatory_gates_pass"] = True
            target_lead["human_review_status"] = "REVIEWED_APPROVED"
            target_lead["requires_human_review"] = False
            target_lead["human_reviewer"] = reviewer

            # Mandatory rule: Strong Signal must have CURRENT_RESIDENT status
            target_lead["location_verification_status"] = "CURRENT_RESIDENT" if loc_status == "CURRENT_RESIDENT" or not loc_status else loc_status
            if loc_evidence:
                target_lead["location_evidence_text"] = loc_evidence

            # Ensure minimum Strong Signal score threshold (>= 75)
            if score_val is not None:
                try:
                    target_lead["score"] = max(STRONG_SIGNAL_THRESHOLD, int(score_val))
                except Exception:
                    pass
            elif target_lead.get("score", 0) < STRONG_SIGNAL_THRESHOLD:
                target_lead["score"] = STRONG_SIGNAL_THRESHOLD

            target_lead["human_review_notes"] = notes or f"Manually verified and approved as Strong Signal by {reviewer}."
            target_lead["qualification_reason"] = f"Approved Strong Signal [{target_lead['score']}/100 pts, Manual Review]: {target_lead['human_review_notes']}"

        elif action == "reject":
            target_lead["qualification_status"] = "Reject"
            target_lead["qualification_status_code"] = "REJECT"
            target_lead["is_qualified"] = False
            target_lead["human_review_status"] = "REVIEWED_REJECTED"
            target_lead["requires_human_review"] = False
            target_lead["human_reviewer"] = reviewer
            if loc_status:
                target_lead["location_verification_status"] = loc_status
            if loc_evidence:
                target_lead["location_evidence_text"] = loc_evidence
            if score_val is not None:
                try:
                    target_lead["score"] = int(score_val)
                except Exception:
                    pass

            target_lead["human_review_notes"] = notes or f"Rejected during manual audit by {reviewer}."
            target_lead["qualification_reason"] = f"Rejected [Manual Review]: {target_lead['human_review_notes']}"

        else:  # update
            if "qualification_status" in data:
                q_stat = data["qualification_status"]
                target_lead["qualification_status"] = q_stat
                target_lead["is_qualified"] = (q_stat == "Strong Signal")
            if loc_status:
                target_lead["location_verification_status"] = loc_status
            if loc_evidence:
                target_lead["location_evidence_text"] = loc_evidence
            if score_val is not None:
                try:
                    target_lead["score"] = int(score_val)
                except Exception:
                    pass
            if notes:
                target_lead["human_review_notes"] = notes
            if "human_review_status" in data:
                target_lead["human_review_status"] = data["human_review_status"]
            target_lead["human_reviewer"] = reviewer

        # Persist and synchronize all 4 deliverables (all_candidates.csv, qualified_dubai_leads.xlsx, top_5_leads.csv, audit_report.json)
        file_tracker = InputFileTracker(results_dir=app.config["RESULTS_DIR"])
        export_results_artifacts(
            unique_records=records,
            output_dir=app.config["RESULTS_DIR"],
            file_tracker=file_tracker
        )

        return jsonify({
            "success": True,
            "message": f"Lead {candidate_id} updated ({target_lead['qualification_status']}) and all deliverables synchronized.",
            "lead": target_lead
        })

    @app.route("/api/pipeline/check-file", methods=["POST"])
    def check_file():
        file_tracker = InputFileTracker(results_dir=app.config["RESULTS_DIR"])
        uploaded_file = request.files.get("file")
        if uploaded_file and uploaded_file.filename:
            raw_fname = uploaded_file.filename
            safe_fname = secure_filename(raw_fname) or "uploaded_file.csv"
            file_bytes = uploaded_file.read()
            checksum = hashlib.md5(file_bytes).hexdigest()
        else:
            data = request.get_json(silent=True) or {}
            safe_fname = data.get("filename", "")
            checksum = data.get("checksum_md5")

        if not safe_fname:
            return jsonify({"error": "No filename provided"}), 400

        entry = file_tracker.find_processed_entry(filename=safe_fname, checksum=checksum)
        if entry:
            return jsonify({
                "already_processed": True,
                "filename": safe_fname,
                "status": "PROCESSED",
                "processed_at": entry.get("processed_at"),
                "records_count": entry.get("records_count"),
                "checksum_md5": entry.get("checksum_md5"),
                "message": f"File '{safe_fname}' is already recorded as PROCESSED in results/processed.json ({entry.get('records_count', 0)} records)."
            })
        else:
            return jsonify({
                "already_processed": False,
                "filename": safe_fname,
                "message": f"File '{safe_fname}' is a new unprocessed input file."
            })

    @app.route("/api/pipeline/run", methods=["POST"])
    def trigger_pipeline():
        uploaded_file = request.files.get("file")
        if uploaded_file and uploaded_file.filename:
            reset_all = request.form.get("reset", "false").lower() in ("true", "1")
        else:
            payload = request.get_json(silent=True) or {}
            reset_all = bool(payload.get("reset", False)) or (request.form.get("reset", "false").lower() in ("true", "1"))

        file_tracker = InputFileTracker(results_dir=app.config["RESULTS_DIR"])
        uploaded_filename = None

        if uploaded_file and uploaded_file.filename:
            raw_fname = uploaded_file.filename
            safe_fname = secure_filename(raw_fname)
            if not safe_fname:
                safe_fname = "uploaded_raw_leads.csv"
            uploaded_filename = safe_fname

            lower = safe_fname.lower()
            if not (lower.endswith(".csv") or lower.endswith(".json")):
                return jsonify({
                    "success": False,
                    "error": f"Invalid file format for '{safe_fname}'. Only .csv and .json files are supported."
                }), 400

            file_bytes = uploaded_file.read()
            uploaded_checksum = hashlib.md5(file_bytes).hexdigest()

            # If not forcing reset, check if already processed
            if not reset_all:
                processed_entry = file_tracker.find_processed_entry(filename=safe_fname, checksum=uploaded_checksum)
                if processed_entry:
                    proc_at = str(processed_entry.get("processed_at", ""))
                    recs = processed_entry.get("records_count", 0)
                    msg = (
                        f"File '{safe_fname}' is already processed ({proc_at[:10] if proc_at else 'earlier'}, "
                        f"{recs} records). Pipeline was NOT run to prevent duplicate processing."
                    )
                    return jsonify({
                        "success": True,
                        "already_processed": True,
                        "filename": safe_fname,
                        "message": msg,
                        "records_count": recs,
                        "processed_at": proc_at,
                        "logs": f"[Notice] {msg}\nCheck 'Reset & Reprocess All' if you wish to force re-running qualification on this file."
                    })

            # If new file: move/save the file to the input folder
            os.makedirs(app.config["INPUT_DIR"], exist_ok=True)
            target_path = os.path.join(app.config["INPUT_DIR"], safe_fname)
            with open(target_path, "wb") as f:
                f.write(file_bytes)

        # Capture output logs and execute pipeline
        log_buffer = io.StringIO()
        try:
            with redirect_stdout(log_buffer), redirect_stderr(log_buffer):
                summary = run_pipeline(
                    input_dir=app.config["INPUT_DIR"],
                    output_dir=app.config["RESULTS_DIR"],
                    reprocess_all=reset_all
                )
            output_text = log_buffer.getvalue()
            return jsonify({
                "success": True,
                "already_processed": False,
                "reset": reset_all,
                "uploaded_file": uploaded_filename,
                "metrics": summary,
                "logs": output_text
            })
        except Exception as e:
            output_text = log_buffer.getvalue()
            return jsonify({
                "success": False,
                "error": str(e),
                "logs": output_text
            }), 500

    @app.route("/api/processed-files", methods=["GET"])
    def get_processed_files():
        file_tracker = InputFileTracker(results_dir=app.config["RESULTS_DIR"])
        input_directory = app.config["INPUT_DIR"]

        input_files_status = []
        if os.path.exists(input_directory):
            for fname in sorted(os.listdir(input_directory)):
                if (fname.lower().endswith(".csv") or fname.lower().endswith(".json")) and not fname.startswith("."):
                    full_p = os.path.join(input_directory, fname)
                    is_done = file_tracker.is_file_processed(full_p)
                    info = file_tracker.processed_data.get(fname, {})
                    input_files_status.append({
                        "filename": fname,
                        "file_path": full_p,
                        "size_bytes": os.path.getsize(full_p) if os.path.exists(full_p) else 0,
                        "is_processed": is_done,
                        "processed_at": info.get("processed_at", None),
                        "records_count": info.get("records_count", None),
                        "status": info.get("status", "UNPROCESSED" if not is_done else "PROCESSED"),
                        "checksum_md5": info.get("checksum_md5", None)
                    })

        return jsonify({
            "total_tracked": len(file_tracker.processed_data),
            "files": input_files_status,
            "processed_json_path": file_tracker.processed_path
        })

    @app.route("/api/download/<file_type>", methods=["GET"])
    def download_artifact(file_type: str):
        file_type = file_type.lower()
        if file_type in ("excel", "xlsx"):
            path = get_results_path("qualified_dubai_leads.xlsx")
            download_name = "qualified_dubai_leads.xlsx"
            mimetype = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        elif file_type in ("top5", "top_5"):
            path = get_results_path("top_5_leads.csv")
            download_name = "top_5_leads.csv"
            mimetype = "text/csv"
        elif file_type in ("all", "all_candidates"):
            path = get_results_path("all_candidates.csv")
            download_name = "all_candidates.csv"
            mimetype = "text/csv"
        elif file_type in ("audit", "audit_report"):
            path = get_results_path("audit_report.json")
            download_name = "audit_report.json"
            mimetype = "application/json"
        elif file_type in ("processed", "processed_json"):
            path = get_results_path("processed.json")
            download_name = "processed.json"
            mimetype = "application/json"
        else:
            abort(400, description=f"Unknown artifact type: '{file_type}'")

        if not os.path.exists(path):
            abort(404, description=f"File not found on disk: {path}")

        return send_file(path, as_attachment=True, download_name=download_name, mimetype=mimetype)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="127.0.0.1", port=5001, debug=True)
