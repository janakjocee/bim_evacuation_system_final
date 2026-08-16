"""Build the transparent silver-label space metadata dataset from real IFCs."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.evaluation.space_classification import extract_silver_records, write_records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ifcs", nargs="+", type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("evaluation/space_classification/silver_labels.csv"),
    )
    args = parser.parse_args()
    records = extract_silver_records(args.ifcs)
    write_records(records, args.output)
    print(json.dumps({
        "output": str(args.output),
        "record_count": len(records),
        "families": dict(Counter(row["source_model_family"] for row in records)),
        "classes": dict(Counter(row["silver_label"] for row in records)),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
