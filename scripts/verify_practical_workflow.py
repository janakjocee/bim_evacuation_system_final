"""Run an evidence-backed end-to-end verification for one IFC and regulation file."""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
import platform
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.validate_ifcs import _ifc_entity_counts, route_loguru_to_stderr_for_json
from src.nlp.document_loader import extract_regulation_text
from src.pipeline.evacuation_pipeline import EvacuationPipeline, _looks_like_git_lfs_pointer


DEPENDENCIES = [
    "ifcopenshell",
    "networkx",
    "numpy",
    "pandas",
    "spacy",
    "streamlit",
    "plotly",
    "pypdf",
    "python-docx",
]


def _dependency_versions() -> dict[str, str]:
    versions = {"python": platform.python_version()}
    for package in DEPENDENCIES:
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = "not installed"
    return versions


def _gate(gates: list[dict[str, Any]], gate_id: str, name: str, passed: bool, evidence: str) -> None:
    gates.append({
        "id": gate_id,
        "name": name,
        "status": "PASS" if passed else "FAIL",
        "evidence": evidence,
    })


def _write_markdown(report: dict[str, Any], path: Path) -> None:
    source = report["source"]
    pipeline = report["pipeline"]
    regulations = report["regulations"]
    lines = [
        "# Practical IFC Verification Report",
        "",
        f"Overall operational verdict: **{report['operational_verdict']}**",
        "",
        f"Engineering-use verdict: **{report['engineering_verdict']}**",
        "",
        "## Source Provenance",
        "",
        f"- File: `{source['file_name']}`",
        f"- Size: `{source['file_size_bytes']}` bytes",
        f"- SHA-256: `{source['sha256']}`",
        f"- IFC schema: `{source['ifc_schema']}`",
        f"- Extraction mode: `{pipeline['source_mode']}`",
        f"- Analysis scope: `{pipeline['analysis_scope']}`",
        "",
        "## Acceptance Gates",
        "",
        "| ID | Gate | Status | Evidence |",
        "|---|---|---|---|",
    ]
    for gate in report["gates"]:
        evidence = str(gate["evidence"]).replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {gate['id']} | {gate['name']} | **{gate['status']}** | {evidence} |")

    lines.extend([
        "",
        "## Measured Pipeline Result",
        "",
        f"- Processing time: `{pipeline['processing_time_seconds']:.3f}` seconds",
        f"- Operational processing readiness: `{pipeline['processing_readiness_score']}/100`",
        f"- Engineering evidence quality: `{pipeline['engineering_evidence_score']}/100`",
        f"- Analyzed nodes/connectors/exits: `{pipeline['analysis_space_count']}` / "
        f"`{pipeline['analysis_door_count']}` / `{pipeline['exit_count']}`",
        f"- Graph nodes/edges: `{pipeline['graph_node_count']}` / `{pipeline['graph_edge_count']}`",
        f"- Verified/inferred graph edges: `{pipeline['verified_edges']}` / `{pipeline['inferred_edges']}`",
        f"- Spaces/elements without an exit route: `{pipeline['without_exit_route']}`",
        f"- Scenarios generated: `{pipeline['scenario_count']}`",
        f"- Scenario confidence range: `{pipeline['min_confidence']:.2f}` to `{pipeline['max_confidence']:.2f}`",
        "",
        "## Regulation Evidence",
        "",
        f"- Input: `{regulations['file_name'] or 'built-in defaults'}`",
        f"- Parsed clauses: `{regulations['clause_count']}`",
        f"- Extracted structured rules: `{regulations['extracted_rule_count']}`",
        f"- Supported rule candidates: `{regulations['supported_candidate_count']}`",
        f"- Active uploaded thresholds: `{regulations['active_uploaded_threshold_count']}`",
        f"- Explicitly unsupported rules: `{regulations['unsupported_rule_count']}`",
        "",
        "## Runtime Requirements",
        "",
    ])
    for package, version in report["runtime_versions"].items():
        lines.append(f"- `{package}`: `{version}`")

    lines.extend([
        "",
        "## Honest Boundary",
        "",
    ])
    for limitation in report["limitations"]:
        lines.append(f"- {limitation}")
    lines.extend([
        "",
        "This is a deterministic academic screening result. It is not legal approval, CFD, "
        "or certified evacuation simulation.",
        "",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")


def verify(ifc_path: Path, regulation_path: Path | None, output_dir: Path, max_scenarios: int) -> dict[str, Any]:
    ifc_path = ifc_path.expanduser().resolve()
    if not ifc_path.is_file():
        raise FileNotFoundError(ifc_path)
    regulation_path = regulation_path.expanduser().resolve() if regulation_path else None
    regulation_text = extract_regulation_text(regulation_path) if regulation_path else None

    pipeline = EvacuationPipeline()
    result = pipeline.run(
        str(ifc_path),
        regulation_text=regulation_text,
        max_scenarios=max_scenarios,
        enable_rag=True,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    export_dir = output_dir / "exports"
    exported = pipeline.export_results(result, str(export_dir), formats=["json", "csv"])

    source_hash = hashlib.sha256(ifc_path.read_bytes()).hexdigest()
    raw = _ifc_entity_counts(ifc_path)
    graph = result.graph_stats or {}
    application = result.regulation_application or {}
    scenario_payloads = [scenario.to_dict() for scenario in result.scenarios]
    route_payloads = [scenario["evacuation_route"] for scenario in scenario_payloads]
    confidences = [float(scenario["confidence_score"]) for scenario in scenario_payloads]

    exported_json = {}
    if exported.get("json"):
        exported_json = json.loads(Path(exported["json"]).read_text(encoding="utf-8"))
    csv_rows = []
    if exported.get("csv"):
        with Path(exported["csv"]).open(newline="", encoding="utf-8") as handle:
            csv_rows = list(csv.DictReader(handle))

    gates: list[dict[str, Any]] = []
    _gate(
        gates,
        "G1",
        "Real IFC payload opens",
        raw.get("ifcopenshell_open", False) and not _looks_like_git_lfs_pointer(ifc_path),
        f"schema={raw.get('raw_schema')}; entities available; size={ifc_path.stat().st_size} bytes",
    )
    _gate(
        gates,
        "G2",
        "Uploaded-file provenance retained",
        result.source_file_name == ifc_path.name and result.source_file_sha256 == source_hash,
        f"name={result.source_file_name}; sha256={result.source_file_sha256}",
    )
    _gate(
        gates,
        "G3",
        "IFC extraction produces analyzable data",
        bool(result.building and result.building.spaces and result.building.doors and result.building.exits),
        f"mode={result.source_mode}; nodes={len(result.building.spaces) if result.building else 0}; "
        f"connectors={len(result.building.doors) if result.building else 0}; exits={len(result.building.exits) if result.building else 0}",
    )
    _gate(
        gates,
        "G4",
        "Route graph is operational",
        bool(graph.get("node_count") and graph.get("edge_count") and not graph.get("spaces_without_exit_route")),
        f"nodes={graph.get('node_count', 0)}; edges={graph.get('edge_count', 0)}; "
        f"without_exit_route={len(graph.get('spaces_without_exit_route', []))}",
    )
    _gate(
        gates,
        "G5",
        "Scenarios are traceable",
        bool(scenario_payloads)
        and all(item.get("decision_trace") for item in scenario_payloads)
        and all(route.get("path") and route.get("route_reliability") for route in route_payloads),
        f"scenarios={len(scenario_payloads)}; decision traces and route evidence exported",
    )
    regulation_gate = not regulation_path or (
        result.regulation_clause_count > 0
        and result.regulation_rule_count > 0
        and application.get("active_uploaded_threshold_count", 0) > 0
    )
    _gate(
        gates,
        "G6",
        "Regulation input is parsed and applied",
        regulation_gate,
        f"clauses={result.regulation_clause_count}; extracted_rules={result.regulation_rule_count}; "
        f"active_uploaded_thresholds={application.get('active_uploaded_threshold_count', 0)}; "
        f"unsupported={application.get('unsupported_rule_count', 0)}",
    )
    _gate(
        gates,
        "G7",
        "JSON and CSV exports reconcile",
        len(exported_json.get("scenarios", [])) == len(scenario_payloads) == len(csv_rows),
        f"pipeline={len(scenario_payloads)}; json={len(exported_json.get('scenarios', []))}; csv={len(csv_rows)}",
    )
    _gate(
        gates,
        "G8",
        "Inference is explicitly bounded",
        all(
            route.get("route_reliability") in {"verified", "partially_inferred", "heavily_inferred", "insufficient"}
            for route in route_payloads
        )
        and all(item.get("data_quality_notes") for item in scenario_payloads),
        f"route_reliabilities={sorted({route.get('route_reliability') for route in route_payloads})}",
    )

    all_gates_pass = all(gate["status"] == "PASS" for gate in gates)
    evidence_score = result.readiness.get("engineering_evidence_score", 0)
    if not all_gates_pass:
        operational_verdict = "FAIL"
    elif evidence_score >= 90 and result.source_mode == "semantic_ifc":
        operational_verdict = "PASS"
    else:
        operational_verdict = "PASS_WITH_REVIEW_LIMITATIONS"

    engineering_verdict = (
        "SUITABLE_FOR_EXPERT_REVIEWED_SEMANTIC_SCREENING"
        if evidence_score >= 70 and result.source_mode == "semantic_ifc"
        else "EXPLORATORY_ONLY_NOT_A_VERIFIED_EVACUATION_MODEL"
    )
    limitations = list(dict.fromkeys(
        (result.readiness.get("critical_issues", []) or [])
        + (result.readiness.get("warnings", []) or [])
    ))

    report = {
        "operational_verdict": operational_verdict,
        "engineering_verdict": engineering_verdict,
        "source": {
            "file_name": ifc_path.name,
            "path": str(ifc_path),
            "file_size_bytes": ifc_path.stat().st_size,
            "sha256": source_hash,
            "ifc_schema": result.ifc_schema,
            "raw_entity_counts": raw,
        },
        "pipeline": {
            "success": result.success,
            "source_mode": result.source_mode,
            "analysis_scope": result.readiness.get("analysis_scope", ""),
            "processing_time_seconds": result.processing_time,
            "processing_readiness_score": result.readiness.get("processing_readiness_score", 0),
            "engineering_evidence_score": evidence_score,
            "analysis_space_count": len(result.building.spaces) if result.building else 0,
            "analysis_door_count": len(result.building.doors) if result.building else 0,
            "exit_count": len(result.building.exits) if result.building else 0,
            "graph_node_count": graph.get("node_count", 0),
            "graph_edge_count": graph.get("edge_count", 0),
            "verified_edges": graph.get("verified_edges_count", 0),
            "inferred_edges": graph.get("inferred_edges_count", 0),
            "without_exit_route": len(graph.get("spaces_without_exit_route", [])),
            "scenario_count": len(scenario_payloads),
            "min_confidence": min(confidences, default=0.0),
            "max_confidence": max(confidences, default=0.0),
        },
        "regulations": {
            "file_name": regulation_path.name if regulation_path else "",
            "clause_count": result.regulation_clause_count,
            "extracted_rule_count": result.regulation_rule_count,
            "supported_candidate_count": application.get("supported_uploaded_rule_candidate_count", 0),
            "active_uploaded_threshold_count": application.get("active_uploaded_threshold_count", 0),
            "unsupported_rule_count": application.get("unsupported_rule_count", 0),
            "active_thresholds": application.get("active_thresholds", []),
            "unsupported_rules": application.get("unsupported_rules", []),
        },
        "exports": exported,
        "runtime_versions": _dependency_versions(),
        "gates": gates,
        "limitations": limitations,
    }
    json_path = output_dir / "verification_report.json"
    markdown_path = output_dir / "verification_report.md"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    _write_markdown(report, markdown_path)
    report["report_files"] = {"json": str(json_path), "markdown": str(markdown_path)}
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ifc", type=Path, help="Real IFC file to verify")
    parser.add_argument("--regulations", type=Path, help="Optional TXT, MD, PDF or DOCX regulation file")
    parser.add_argument("--output", type=Path, default=Path("outputs/practical_verification"))
    parser.add_argument("--max-scenarios", type=int, default=20)
    args = parser.parse_args()

    route_loguru_to_stderr_for_json()
    report = verify(args.ifc, args.regulations, args.output, args.max_scenarios)
    print(json.dumps({
        "operational_verdict": report["operational_verdict"],
        "engineering_verdict": report["engineering_verdict"],
        "gates": {gate["id"]: gate["status"] for gate in report["gates"]},
        "processing_readiness_score": report["pipeline"]["processing_readiness_score"],
        "engineering_evidence_score": report["pipeline"]["engineering_evidence_score"],
        "reports": report["report_files"],
    }, indent=2))
    return 0 if report["operational_verdict"] != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
