"""Generate and evaluate the controlled IFC ground-truth fixture."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.generate_controlled_ifc import build_controlled_ifc
from src.evaluation.ifc_ground_truth import evaluate_controlled_ifc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ifc-output", type=Path, default=Path("data/generated/controlled_semantic_evacuation.ifc"))
    parser.add_argument(
        "--truth",
        type=Path,
        default=Path("evaluation/ifc_ground_truth/controlled_semantic_evacuation.json"),
    )
    parser.add_argument("--report", type=Path, default=Path("evaluation/results/ifc_ground_truth.json"))
    args = parser.parse_args()

    build_controlled_ifc(args.ifc_output)
    report = evaluate_controlled_ifc(args.ifc_output, args.truth)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
