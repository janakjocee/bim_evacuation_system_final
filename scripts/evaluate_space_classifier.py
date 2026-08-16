"""Evaluate the IFC space-use ML experiment against the deterministic baseline."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.evaluation.space_classification import evaluate_classifier, write_json


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("evaluation/space_classification/silver_labels.csv"),
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("evaluation/results/space_classification.json"),
    )
    args = parser.parse_args()
    report = evaluate_classifier(args.dataset)
    write_json(report, args.report)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
