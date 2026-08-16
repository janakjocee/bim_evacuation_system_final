"""Tests for the reproducible research-evaluation assets."""
from pathlib import Path
import json
import subprocess
import sys

from scripts.compare_ifc_diagnostics import compare, public_row

from scripts.generate_controlled_ifc import build_controlled_ifc, stable_guid
from src.evaluation.ifc_ground_truth import evaluate_controlled_ifc
from src.evaluation.retrieval_benchmark import evaluate_sources, retrieval_metrics
from src.evaluation.scenario_benchmark import run_scenario_benchmark
from src.evaluation.space_classification import (
    deterministic_baseline,
    evaluate_classifier,
    silver_label,
)
from src.nlp.rag_engine import RAGEngine
from src.nlp.regulation_parser import RegulationClause


ROOT = Path(__file__).resolve().parents[1]
TRUTH = ROOT / "evaluation" / "ifc_ground_truth" / "controlled_semantic_evacuation.json"


def test_controlled_ifc_guid_is_stable_and_valid():
    assert stable_guid("space:office") == stable_guid("space:office")
    assert len(stable_guid("space:office")) == 22


def test_controlled_ifc_matches_declared_ground_truth(tmp_path):
    ifc_path = build_controlled_ifc(tmp_path / "controlled.ifc")
    report = evaluate_controlled_ifc(ifc_path, TRUTH)

    assert report["passed"], report
    assert report["metrics"]["connection_precision"] == 1.0
    assert report["metrics"]["connection_recall"] == 1.0
    assert report["metrics"]["route_reachability_recall"] == 1.0
    assert report["observed"]["compatibility_status"] == "pass"


def test_silver_labels_and_baseline_cover_declared_terms():
    assert silver_label("B104 Bathroom 1")[0] == "sanitary"
    assert silver_label("1C18 Physical Exam")[0] == "clinical"
    assert silver_label("A103 Kitchen")[0] == "kitchen"
    assert deterministic_baseline("A103 Kitchen") == "kitchen"
    assert deterministic_baseline("2D18 Tech Office") == "workplace"
    assert deterministic_baseline("Unspecified Room") == "unknown"


def test_space_classifier_uses_grouped_evaluation():
    dataset = ROOT / "evaluation" / "space_classification" / "silver_labels.csv"
    report = evaluate_classifier(dataset)

    assert report["record_count"] > 100
    assert report["model_families"] == ["clinic", "duplex"]
    assert len(report["folds"]) == 2
    assert report["validation"] == "leave-one-source-model-family-out"
    assert report["ground_truth_status"].startswith("rule_seeded_silver")
    assert isinstance(report["ml_eligible_for_runtime_default"], bool)


def test_retrieval_metrics_use_first_relevant_rank():
    queries = [{"query_id": "Q1", "relevant_clause_ids": ["B"]}]
    metrics = retrieval_metrics(queries, [["A", "B", "C"]])

    assert metrics["recall_at_1"] == 0
    assert metrics["recall_at_3"] == 1
    assert metrics["mrr"] == 0.5


def test_sample_regulation_retrieval_benchmark_runs():
    report = evaluate_sources(
        ROOT / "evaluation" / "regulation_retrieval" / "queries.jsonl",
        {"sample_demo": ROOT / "data" / "sample_regulations" / "approved_document_b.txt"},
    )

    source = report["sources"][0]
    assert source["query_count"] == 16
    assert source["methods"]["tfidf_lexical"]["recall_at_3"] >= 0.9
    assert report["query_judgement_status"].endswith("requires_project_author_review")


def test_declared_scenario_benchmark_passes(tmp_path):
    ifc_path = build_controlled_ifc(tmp_path / "controlled.ifc")
    report = run_scenario_benchmark(
        ifc_path,
        ROOT / "evaluation" / "scenarios" / "expected_cases.json",
    )

    assert report["passed"], report
    assert report["pass_rate"] == 1.0
    assert report["dataset_kind"] == "demonstration_only"
    assert all(case["checks"]["repeatability"] for case in report["cases"])


def test_ifc_corpus_manifest_has_unique_verified_hashes():
    manifest = json.loads((ROOT / "evaluation" / "ifc_corpus_manifest.json").read_text())
    hashes = [item["sha256"] for item in manifest["sources"]]

    assert len(hashes) == len(set(hashes))
    assert all(len(value) == 64 for value in hashes)
    assert all(item["licence"] for item in manifest["sources"])


def test_research_evaluation_command_passes(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_research_evaluation.py",
            "--output-dir",
            str(tmp_path / "evidence"),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    summary = json.loads((tmp_path / "evidence" / "summary.json").read_text())
    assert summary["passed"]
    assert all(summary["gates"].values())


def test_runtime_evidence_retrieval_uses_tfidf_by_default():
    clauses = [
        RegulationClause(clause_id="2.2", text="Maximum travel distance to nearest exit is 45 metres."),
        RegulationClause(clause_id="2.9", text="Protected stairway door minimum width is 800mm."),
    ]
    engine = RAGEngine()
    vector_built = engine.build_index(clauses)
    results = engine.retrieve("nearest exit travel distance", top_k=1)

    assert vector_built is False
    assert engine.retrieval_mode() == "tfidf_lexical"
    assert results[0][0].clause_id == "2.2"
    assert results[0][1] > 0


def test_compatibility_comparison_reports_improvement_and_sanitises_pass():
    before = [{
        "file_name": "model.ifc",
        "source_file_sha256": "a" * 64,
        "pass_partial_fail_status": "partial",
        "disconnected_spaces_count": 3,
        "spaces_without_exit_route_count": 3,
        "verified_edges_count": 10,
        "inferred_edges_count": 0,
        "failure_reason": "Three spaces disconnected",
    }]
    after = [{
        **before[0],
        "pass_partial_fail_status": "pass",
        "disconnected_spaces_count": 0,
        "spaces_without_exit_route_count": 0,
        "verified_edges_count": 13,
        "failure_reason": "stale text",
    }]

    report = compare(before, after)
    assert report["before_total_disconnected_spaces"] == 3
    assert report["after_total_disconnected_spaces"] == 0
    assert report["files"][0]["remaining_reason"] == ""
    assert public_row(after[0])["failure_reason"] == ""
