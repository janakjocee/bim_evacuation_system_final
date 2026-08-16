"""Create a blinded space-use labelling pack for independent human review."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.evaluation.space_classification import (
    build_blinded_label_review_pack,
    load_records,
    write_label_review_pack,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("evaluation/space_classification/silver_labels.csv"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("outputs/space_label_review/independent_label_review.csv"),
    )
    args = parser.parse_args()
    pack = build_blinded_label_review_pack(load_records(args.dataset))
    write_label_review_pack(pack, args.output)
    print(json.dumps({
        "output": str(args.output),
        "record_count": len(pack),
        "status": "awaiting_independent_human_labels",
        "silver_labels_exposed_to_reviewer": False,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
