"""Run the reproducible research-evidence suite and write one summary."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.generate_controlled_ifc import build_controlled_ifc
from src.evaluation.ifc_ground_truth import evaluate_controlled_ifc
from src.evaluation.retrieval_benchmark import evaluate_sources
from src.evaluation.scenario_benchmark import run_scenario_benchmark
from src.evaluation.space_classification import evaluate_classifier


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/research_evaluation"))
    parser.add_argument("--practical-regulations", type=Path)
    parser.add_argument("--include-embeddings", action="store_true")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    controlled_ifc = build_controlled_ifc(args.output_dir / "controlled_semantic_evacuation.ifc")
    ifc_report = evaluate_controlled_ifc(
        controlled_ifc,
        ROOT / "evaluation" / "ifc_ground_truth" / "controlled_semantic_evacuation.json",
    )
    ml_report = evaluate_classifier(
        ROOT / "evaluation" / "space_classification" / "silver_labels.csv"
    )
    sources = {
        "sample_demo": ROOT / "data" / "sample_regulations" / "approved_document_b.txt",
    }
    if args.practical_regulations:
        sources["practical_adb"] = args.practical_regulations
    retrieval_report = evaluate_sources(
        ROOT / "evaluation" / "regulation_retrieval" / "queries.jsonl",
        sources,
        include_embeddings=args.include_embeddings,
    )
    scenario_report = run_scenario_benchmark(
        controlled_ifc,
        ROOT / "evaluation" / "scenarios" / "expected_cases.json",
    )

    reports = {
        "ifc_ground_truth.json": ifc_report,
        "space_classification.json": ml_report,
        "regulation_retrieval.json": retrieval_report,
        "scenario_benchmark.json": scenario_report,
    }
    for name, report in reports.items():
        (args.output_dir / name).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    retrieval_gate = all(
        source["methods"]["tfidf_lexical"]["recall_at_3"] >= 0.90
        for source in retrieval_report["sources"]
    )
    gates = {
        "controlled_ifc_ground_truth": ifc_report["passed"],
        "scenario_expected_cases": scenario_report["passed"],
        "retrieval_recall_at_3_minimum_0_90": retrieval_gate,
        "ml_experiment_completed_with_runtime_gate": isinstance(
            ml_report["ml_eligible_for_runtime_default"], bool
        ),
    }
    summary = {
        "suite": "bim_evacuation_research_evaluation_v1",
        "passed": all(gates.values()),
        "gates": gates,
        "important_interpretation": {
            "ml_runtime_default": ml_report["runtime_recommendation"],
            "controlled_ground_truth_independent": ifc_report["independent_ground_truth"],
            "scenario_dataset_kind": scenario_report["dataset_kind"],
            "regulation_judgements": retrieval_report["query_judgement_status"],
        },
        "reports": sorted(reports),
    }
    (args.output_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
