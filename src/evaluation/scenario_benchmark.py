"""Expected-case and repeatability benchmark for scenario engines."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict

from src.fire.fire_scenario_engine import FireScenarioEngine
from src.pipeline.evacuation_pipeline import EvacuationPipeline
from src.scenario.worst_case_engine import WorstCaseScenarioEngine, load_worst_case_dataset


def _digest(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def _controlled_outcome(ifc_path: Path) -> Dict[str, Any]:
    pipeline = EvacuationPipeline()
    result = pipeline.run(str(ifc_path), max_scenarios=100, enable_rag=False)
    graph = pipeline.graph_builder.get_graph_stats() if pipeline.graph_builder else {}
    compatibility = (
        "pass"
        if result.success and result.source_mode == "semantic_ifc" and graph.get("graph_confidence_score", 0) >= 0.8
        else "partial" if result.success else "fail"
    )
    return {
        "success": result.success,
        "scenario_count": len(result.scenarios),
        "route_reliabilities": sorted({
            scenario.to_dict()["evacuation_route"]["route_reliability"]
            for scenario in result.scenarios
        }),
        "outcomes": sorted(
            (
                scenario.origin_space_name,
                scenario.evacuation_route.destination,
                round(scenario.evacuation_route.distance, 4),
                scenario.risk_level.value,
                scenario.compliance_status.value,
            )
            for scenario in result.scenarios
        ),
        "compatibility_status": compatibility,
    }


def _worst_outcome(engine: WorstCaseScenarioEngine, scenario_id: str) -> Dict[str, Any]:
    scenario = next(item for item in engine.get_scenarios() if item["scenario_id"] == scenario_id)
    result = engine.run_scenario(scenario)
    return {
        "risk": result.overall_risk,
        "affected_exits": sorted(result.affected_exits),
        "trapped_rooms": sorted(result.trapped_rooms),
        "trapped_occupants": result.trapped_occupants,
        "rerouted_rooms": sorted(result.rerouted_rooms),
        "available_exits": sorted({
            row["available_exit"]
            for row in result.room_results
            if not row["trapped"] and row.get("available_exit")
        }),
        "affected_occupants": result.affected_occupants,
    }


def _fire_outcome(engine: FireScenarioEngine, scenario: Dict[str, Any]) -> Dict[str, Any]:
    result = engine.run_fire_scenario(scenario)
    return {
        "risk": result["overall_risk_level"],
        "aset_rset_rows": len(result["aset_rset_results"]),
        "classifications": sorted({row["classification"] for row in result["aset_rset_results"]}),
        "trapped_occupants": result["life_safety_impact"]["trapped_occupants"],
        "affected_exits": sorted(result["affected_exits"]),
        "qualified_review_required": "Qualified review required" in result["qualified_review_recommendation"],
    }


def run_scenario_benchmark(ifc_path: Path, cases_path: Path) -> Dict[str, Any]:
    declaration = json.loads(Path(cases_path).read_text(encoding="utf-8"))
    dataset = load_worst_case_dataset()
    outcomes = []

    for case in declaration["cases"]:
        engine_name = case["engine"]
        expected = case["expected"]
        if engine_name == "evacuation_pipeline":
            first = _controlled_outcome(ifc_path)
            second = _controlled_outcome(ifc_path)
            checks = {
                "scenario_count": first["scenario_count"] == expected["scenario_count"],
                "route_reliability": first["route_reliabilities"] == [expected["route_reliability"]],
                "compatibility_status": first["compatibility_status"] == expected["compatibility_status"],
            }
        elif engine_name == "worst_case":
            first = _worst_outcome(WorstCaseScenarioEngine(dataset), case["scenario_id"])
            second = _worst_outcome(WorstCaseScenarioEngine(dataset), case["scenario_id"])
            checks = {}
            if "risk" in expected:
                checks["risk"] = first["risk"] == expected["risk"]
            if "risk_one_of" in expected:
                checks["risk_one_of"] = first["risk"] in expected["risk_one_of"]
            if "minimum_trapped_rooms" in expected:
                checks["minimum_trapped_rooms"] = len(first["trapped_rooms"]) >= expected["minimum_trapped_rooms"]
            if expected.get("reroute_or_affected"):
                checks["reroute_or_affected"] = bool(first["rerouted_rooms"] or first["affected_occupants"])
            if "affected_exit" in expected:
                checks["affected_exit"] = expected["affected_exit"] in first["affected_exits"]
            if "available_routes_avoid_exit" in expected:
                checks["available_routes_avoid_exit"] = expected["available_routes_avoid_exit"] not in first["available_exits"]
        else:
            engine = FireScenarioEngine(dataset)
            scenario = case.get("scenario") or next(
                item for item in engine.get_scenarios() if item["scenario_id"] == case["scenario_id"]
            )
            first = _fire_outcome(engine, scenario)
            second = _fire_outcome(FireScenarioEngine(dataset), scenario)
            checks = {}
            if "risk" in expected:
                checks["risk"] = first["risk"] == expected["risk"]
            if "minimum_aset_rset_rows" in expected:
                checks["minimum_aset_rset_rows"] = first["aset_rset_rows"] >= expected["minimum_aset_rset_rows"]
            if "minimum_trapped_occupants" in expected:
                checks["minimum_trapped_occupants"] = first["trapped_occupants"] >= expected["minimum_trapped_occupants"]
            if expected.get("qualified_review_required"):
                checks["qualified_review_required"] = first["qualified_review_required"]

        repeatable = _digest(first) == _digest(second)
        checks["repeatability"] = repeatable
        outcomes.append({
            "case_id": case["case_id"],
            "engine": engine_name,
            "passed": all(checks.values()),
            "checks": checks,
            "observed": first,
            "repeatability_digest": _digest(first),
        })

    return {
        "benchmark_id": declaration["benchmark_id"],
        "evidence_status": declaration["evidence_status"],
        "dataset_kind": dataset.get("dataset_kind"),
        "case_count": len(outcomes),
        "passed_case_count": sum(item["passed"] for item in outcomes),
        "pass_rate": round(sum(item["passed"] for item in outcomes) / max(len(outcomes), 1), 4),
        "passed": all(item["passed"] for item in outcomes),
        "cases": outcomes,
        "limitations": declaration["limitations"],
    }
