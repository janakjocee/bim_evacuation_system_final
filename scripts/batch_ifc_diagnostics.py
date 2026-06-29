"""Generate batch IFC compatibility diagnostics as CSV and JSON."""
from __future__ import annotations

import argparse
import contextlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.validate_ifcs import audit_file, discover_ifcs, route_loguru_to_stderr_for_json, write_csv
from src.nlp.document_loader import extract_regulation_text


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "inputs",
        nargs="*",
        default=["data/test_ifc"],
        help="IFC files or folders to audit. Defaults to data/test_ifc.",
    )
    parser.add_argument("--max-scenarios", type=int, default=5)
    parser.add_argument("--regulations", help="Optional TXT/MD/PDF/DOCX regulation file to apply")
    parser.add_argument("--output-dir", default="outputs/ifc_diagnostics")
    args = parser.parse_args()

    files = discover_ifcs(args.inputs)
    if not files:
        parser.error("No IFC files found in the supplied inputs.")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "compatibility_matrix.json"
    csv_path = output_dir / "compatibility_matrix.csv"

    route_loguru_to_stderr_for_json()
    with contextlib.redirect_stdout(sys.stderr):
        regulation_text = extract_regulation_text(args.regulations) if args.regulations else None
        rows = [audit_file(path, args.max_scenarios, regulation_text=regulation_text) for path in files]

    json_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    write_csv(rows, csv_path)

    status_counts = {}
    for row in rows:
        status = row["compatibility_status"]
        status_counts[status] = status_counts.get(status, 0) + 1

    print(json.dumps({
        "input_count": len(rows),
        "status_counts": status_counts,
        "json": str(json_path),
        "csv": str(csv_path),
    }, indent=2))
    return 0 if status_counts.get("fail", 0) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
