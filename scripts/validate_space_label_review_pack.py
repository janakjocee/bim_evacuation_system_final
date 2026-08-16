"""Validate a completed independent space-use labelling pack."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.evaluation.space_classification import load_records, validate_label_review_pack


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("review_pack", type=Path)
    args = parser.parse_args()
    report = validate_label_review_pack(load_records(args.review_pack))
    print(json.dumps(report, indent=2))
    return 0 if report["eligible_for_grouped_model_evaluation"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
