"""Benchmark regulation evidence retrieval on supplied text sources."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.evaluation.retrieval_benchmark import evaluate_sources


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--queries",
        type=Path,
        default=Path("evaluation/regulation_retrieval/queries.jsonl"),
    )
    parser.add_argument(
        "--sample",
        type=Path,
        default=Path("data/sample_regulations/approved_document_b.txt"),
    )
    parser.add_argument("--practical", type=Path)
    parser.add_argument("--include-embeddings", action="store_true")
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("evaluation/results/regulation_retrieval.json"),
    )
    args = parser.parse_args()

    sources = {"sample_demo": args.sample}
    if args.practical:
        sources["practical_adb"] = args.practical
    report = evaluate_sources(args.queries, sources, include_embeddings=args.include_embeddings)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
