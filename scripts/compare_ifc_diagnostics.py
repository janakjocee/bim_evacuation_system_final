"""Compare two IFC diagnostic matrices and write report-ready evidence."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


PUBLIC_FIELDS = [
    "file_name",
    "source_file_sha256",
    "ifc_schema",
    "extraction_mode",
    "space_count",
    "door_count",
    "exit_count",
    "verified_edges_count",
    "inferred_edges_count",
    "disconnected_spaces_count",
    "spaces_without_exit_route_count",
    "scenarios_generated",
    "processing_readiness_score",
    "engineering_evidence_score",
    "pass_partial_fail_status",
    "failure_reason",
]


def public_row(row: dict) -> dict:
    result = {key: row.get(key) for key in PUBLIC_FIELDS}
    if result.get("pass_partial_fail_status") == "pass":
        result["failure_reason"] = ""
    return result


def load_rows(path: Path) -> list[dict]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def compare(before_rows: list[dict], after_rows: list[dict]) -> dict:
    before_by_hash = {row.get("source_file_sha256"): row for row in before_rows}
    comparisons = []
    for after in after_rows:
        before = before_by_hash.get(after.get("source_file_sha256"))
        comparisons.append({
            "file_name": after.get("file_name"),
            "source_file_sha256": after.get("source_file_sha256"),
            "before_status": before.get("pass_partial_fail_status") if before else "not_tested",
            "after_status": after.get("pass_partial_fail_status"),
            "before_disconnected_spaces": before.get("disconnected_spaces_count") if before else None,
            "after_disconnected_spaces": after.get("disconnected_spaces_count"),
            "disconnected_spaces_delta": (
                after.get("disconnected_spaces_count", 0) - before.get("disconnected_spaces_count", 0)
                if before else None
            ),
            "before_spaces_without_exit_route": before.get("spaces_without_exit_route_count") if before else None,
            "after_spaces_without_exit_route": after.get("spaces_without_exit_route_count"),
            "spaces_without_exit_route_delta": (
                after.get("spaces_without_exit_route_count", 0) - before.get("spaces_without_exit_route_count", 0)
                if before else None
            ),
            "before_verified_edges": before.get("verified_edges_count") if before else None,
            "after_verified_edges": after.get("verified_edges_count"),
            "before_inferred_edges": before.get("inferred_edges_count") if before else None,
            "after_inferred_edges": after.get("inferred_edges_count"),
            "remaining_reason": (
                "" if after.get("pass_partial_fail_status") == "pass" else after.get("failure_reason", "")
            ),
        })

    comparable = [row for row in comparisons if row["before_status"] != "not_tested"]
    return {
        "comparison": "ifc_parser_connectivity_before_after_v1",
        "comparable_payload_count": len(comparable),
        "final_payload_count": len(after_rows),
        "before_total_disconnected_spaces": sum(row["before_disconnected_spaces"] or 0 for row in comparable),
        "after_total_disconnected_spaces": sum(row["after_disconnected_spaces"] or 0 for row in comparable),
        "before_total_spaces_without_exit_route": sum(row["before_spaces_without_exit_route"] or 0 for row in comparable),
        "after_total_spaces_without_exit_route": sum(row["after_spaces_without_exit_route"] or 0 for row in comparable),
        "final_status_counts": {
            status: sum(row.get("pass_partial_fail_status") == status for row in after_rows)
            for status in ("pass", "partial", "fail")
        },
        "interpretation": (
            "Supplementary links are labelled inferred and do not upgrade partial real models to verified. "
            "The controlled project-generated model provides the strict-pass regression case."
        ),
        "files": comparisons,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("evaluation/results"))
    args = parser.parse_args()
    before_rows = load_rows(args.before)
    after_rows = load_rows(args.after)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    final_rows = [public_row(row) for row in after_rows]
    (args.output_dir / "compatibility_matrix.json").write_text(
        json.dumps(final_rows, indent=2) + "\n",
        encoding="utf-8",
    )
    with (args.output_dir / "compatibility_matrix.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=PUBLIC_FIELDS)
        writer.writeheader()
        writer.writerows(final_rows)

    report = compare(before_rows, after_rows)
    (args.output_dir / "ifc_compatibility_comparison.json").write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
