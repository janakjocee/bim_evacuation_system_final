"""Generate batch IFC compatibility diagnostics as CSV and JSON."""
from __future__ import annotations

import argparse
import contextlib
import csv
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.validate_ifcs import audit_file, discover_ifcs, route_loguru_to_stderr_for_json
from src.nlp.document_loader import extract_regulation_text


MATRIX_FIELDS = [
    "file_name",
    "path",
    "file_size_bytes",
    "source_file_sha256",
    "is_duplicate_payload",
    "duplicate_payload_of",
    "payload_occurrence_count",
    "ifc_schema",
    "opens_with_ifcopenshell",
    "extraction_mode",
    "source_mode",
    "geometry_source_types",
    "geometry_elements_available",
    "geometry_elements_used",
    "space_count",
    "door_count",
    "stair_count",
    "exit_count",
    "graph_node_count",
    "graph_edge_count",
    "verified_edges_count",
    "inferred_edges_count",
    "graph_confidence_score",
    "processing_readiness_score",
    "engineering_evidence_score",
    "analysis_scope",
    "disconnected_spaces_count",
    "doors_without_connected_spaces_count",
    "spaces_without_exit_route_count",
    "scenarios_generated",
    "high_risk_count",
    "medium_risk_count",
    "low_risk_count",
    "route_reliability_summary",
    "regulation_clause_count",
    "regulation_rule_count",
    "supported_uploaded_rule_candidates",
    "applied_uploaded_rules",
    "unsupported_rules",
    "success",
    "pass_partial_fail_status",
    "failure_reason",
    "reliability_notes",
]


def _json_safe(value):
    if isinstance(value, Path):
        return str(value)
    return value


def _safe_per_file_name(path: Path) -> str:
    return f"{path.stem.replace(' ', '_')}.diagnostic.json"


def normalise_row(row: dict) -> dict:
    """Map validator diagnostics to the final compatibility-matrix schema."""
    status = row.get("compatibility_status", "fail")
    reliability = row.get("reliability", "fail")
    route_reliabilities = row.get("route_reliabilities", []) or []
    reliability_notes = []
    if row.get("readiness_critical_issues"):
        reliability_notes.extend(row["readiness_critical_issues"])
    if row.get("readiness_warnings"):
        reliability_notes.extend(row["readiness_warnings"])
    if not reliability_notes and row.get("failure_reason"):
        reliability_notes.append(row["failure_reason"])

    normalised = {
        "file_name": row.get("file"),
        "path": row.get("path"),
        "file_size_bytes": row.get("file_size_bytes", 0),
        "source_file_sha256": row.get("source_file_sha256", ""),
        "is_duplicate_payload": False,
        "duplicate_payload_of": "",
        "payload_occurrence_count": 1,
        "ifc_schema": row.get("schema") or row.get("raw_schema", "UNKNOWN"),
        "opens_with_ifcopenshell": bool(row.get("ifcopenshell_open", False)),
        "extraction_mode": row.get("mode", "unknown"),
        "source_mode": row.get("mode", "unknown"),
        "geometry_source_types": row.get("geometry_source_types", []),
        "geometry_elements_available": row.get("geometry_elements_available", row.get("candidate_geometry_elements", 0)),
        "geometry_elements_used": row.get("geometry_elements_used", 0),
        "space_count": row.get("extracted_spaces", 0),
        "door_count": row.get("extracted_doors", 0),
        "stair_count": row.get("extracted_stairs", 0),
        "exit_count": row.get("detected_exits", 0),
        "graph_node_count": row.get("graph_node_count", 0),
        "graph_edge_count": row.get("graph_edge_count", 0),
        "verified_edges_count": row.get("verified_edges", 0),
        "inferred_edges_count": row.get("inferred_edges", 0),
        "graph_confidence_score": row.get("graph_confidence", 0),
        "processing_readiness_score": row.get("processing_readiness_score", 0),
        "engineering_evidence_score": row.get("engineering_evidence_score", row.get("readiness_score", 0)),
        "analysis_scope": row.get("analysis_scope", ""),
        "disconnected_spaces_count": len(row.get("disconnected_spaces", []) or []),
        "doors_without_connected_spaces_count": len(row.get("doors_without_connected_spaces", []) or []),
        "spaces_without_exit_route_count": len(row.get("spaces_without_exit_route", []) or []),
        "scenarios_generated": row.get("scenarios", 0),
        "high_risk_count": row.get("high_risk_count", 0),
        "medium_risk_count": row.get("medium_risk_count", 0),
        "low_risk_count": row.get("low_risk_count", 0),
        "route_reliability_summary": ", ".join(route_reliabilities) if route_reliabilities else reliability,
        "regulation_clause_count": row.get("regulation_clause_count", 0),
        "regulation_rule_count": row.get("regulation_rule_count", 0),
        "supported_uploaded_rule_candidates": row.get("supported_uploaded_rule_candidates", 0),
        "applied_uploaded_rules": row.get("applied_uploaded_rules", 0),
        "unsupported_rules": row.get("unsupported_rules", 0),
        "success": bool(row.get("success", False)),
        "pass_partial_fail_status": status,
        "failure_reason": row.get("failure_reason", ""),
        "reliability_notes": reliability_notes,
        "raw_validator_row": row,
    }
    return normalised


def failed_row(path: Path, exc: Exception) -> dict:
    return normalise_row({
        "file": path.name,
        "path": str(path),
        "file_size_bytes": path.stat().st_size if path.exists() else 0,
        "source_file_sha256": (
            hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""
        ),
        "schema": "UNKNOWN",
        "ifcopenshell_open": False,
        "success": False,
        "mode": "error",
        "compatibility_status": "fail",
        "failure_reason": f"{type(exc).__name__}: {exc}",
        "errors": [str(exc)],
    })


def annotate_duplicate_payloads(rows: list[dict]) -> list[dict]:
    """Label repeated file contents without removing tested input paths."""
    groups: dict[str, list[dict]] = {}
    for row in rows:
        fingerprint = row.get("source_file_sha256") or f"path:{row.get('path', '')}"
        groups.setdefault(fingerprint, []).append(row)

    for group in groups.values():
        canonical_name = group[0]["file_name"]
        occurrence_count = len(group)
        for index, row in enumerate(group):
            row["payload_occurrence_count"] = occurrence_count
            row["is_duplicate_payload"] = index > 0
            row["duplicate_payload_of"] = canonical_name if index > 0 else ""
    return rows


def duplicate_summary(rows: list[dict]) -> dict:
    """Summarise unique payloads and duplicate groups for honest corpus reporting."""
    unique_rows = [row for row in rows if not row.get("is_duplicate_payload")]
    unique_status_counts: dict[str, int] = {}
    for row in unique_rows:
        status = row["pass_partial_fail_status"]
        unique_status_counts[status] = unique_status_counts.get(status, 0) + 1

    duplicate_groups = []
    for row in unique_rows:
        count = int(row.get("payload_occurrence_count", 1))
        if count <= 1:
            continue
        matching = [
            item["file_name"]
            for item in rows
            if item.get("source_file_sha256") == row.get("source_file_sha256")
        ]
        duplicate_groups.append({
            "source_file_sha256": row.get("source_file_sha256", ""),
            "canonical_file": row["file_name"],
            "files": matching,
            "occurrence_count": count,
        })

    return {
        "unique_payload_count": len(unique_rows),
        "duplicate_input_count": len(rows) - len(unique_rows),
        "unique_status_counts": unique_status_counts,
        "duplicate_payload_groups": duplicate_groups,
    }


def write_matrix_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=MATRIX_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({
                key: json.dumps(value) if isinstance(value, (list, dict)) else value
                for key, value in row.items()
                if key in MATRIX_FIELDS
            })


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "inputs",
        nargs="*",
        help="IFC files or folders to audit. Defaults to data/test_ifc.",
    )
    parser.add_argument("--input", action="append", dest="input_paths", help="IFC file or folder to audit")
    parser.add_argument("--max-scenarios", type=int, default=5)
    parser.add_argument("--regulations", help="Optional TXT/MD/PDF/DOCX regulation file to apply")
    parser.add_argument("--output", dest="output_dir", help="Output directory for compatibility matrices")
    parser.add_argument("--output-dir", dest="output_dir", default="outputs/ifc_diagnostics")
    args = parser.parse_args()

    input_values = (args.input_paths or []) + (args.inputs or [])
    files = discover_ifcs(input_values or ["data/test_ifc"])
    if not files:
        parser.error("No IFC files found in the supplied inputs.")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    per_file_dir = output_dir / "per_file"
    per_file_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "compatibility_matrix.json"
    csv_path = output_dir / "compatibility_matrix.csv"
    summary_path = output_dir / "compatibility_summary.json"

    route_loguru_to_stderr_for_json()
    with contextlib.redirect_stdout(sys.stderr):
        regulation_text = extract_regulation_text(args.regulations) if args.regulations else None
        rows = []
        for path in files:
            try:
                row = normalise_row(audit_file(path, args.max_scenarios, regulation_text=regulation_text))
            except Exception as exc:
                row = failed_row(path, exc)
            rows.append(row)

        annotate_duplicate_payloads(rows)
        for path, row in zip(files, rows):
            per_file_path = per_file_dir / _safe_per_file_name(path)
            per_file_path.write_text(json.dumps(row, indent=2, default=_json_safe), encoding="utf-8")

    json_path.write_text(json.dumps(rows, indent=2, default=_json_safe), encoding="utf-8")
    write_matrix_csv(rows, csv_path)

    status_counts = {}
    for row in rows:
        status = row["pass_partial_fail_status"]
        status_counts[status] = status_counts.get(status, 0) + 1

    summary = {
        "input_count": len(rows),
        "status_counts": status_counts,
        **duplicate_summary(rows),
        "json": str(json_path),
        "csv": str(csv_path),
        "summary_json": str(summary_path),
        "per_file_json_dir": str(per_file_dir),
        "failed_or_partial": [
            {
                "file_name": row["file_name"],
                "status": row["pass_partial_fail_status"],
                "failure_reason": row["failure_reason"],
            }
            for row in rows
            if row["pass_partial_fail_status"] != "pass"
        ],
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if status_counts.get("fail", 0) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
