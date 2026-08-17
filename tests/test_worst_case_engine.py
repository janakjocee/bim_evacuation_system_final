"""
Tests for the Fire-Origin Worst-Case Scenario Engine.
"""
import json

from src.scenario.worst_case_engine import (
    WorstCaseScenarioEngine,
    build_graph_from_dataset,
    load_worst_case_dataset,
    dataset_summary,
    validate_scenario_dataset,
)


def test_worst_case_demo_dataset_loads():
    dataset = load_worst_case_dataset()
    assert dataset["building_id"] == "DEMO_WORST_CASE_001"
    assert len(dataset["spaces"]) >= 8
    assert len(dataset["connections"]) >= 10
    assert len(dataset["hazard_scenarios"]) >= 4
    assert dataset["dataset_kind"] == "demonstration_only"
    assert dataset["provenance"]["source_type"] == "bundled_synthetic_academic_demo"
    assert dataset["provenance"]["ifc_derived"] is False
    assert dataset_summary(dataset)["hazard_scenarios"] >= 4


def test_dataset_validation_rejects_missing_graph_data():
    try:
        validate_scenario_dataset({"spaces": [], "connections": [], "hazard_scenarios": []})
    except ValueError as exc:
        assert "spaces" in str(exc)
    else:
        raise AssertionError("Invalid dataset was accepted")


def test_graph_builds_from_worst_case_dataset():
    dataset = load_worst_case_dataset()
    graph = build_graph_from_dataset(dataset)
    assert graph.number_of_nodes() == len(dataset["spaces"])
    assert graph.number_of_edges() == len(dataset["connections"])
    assert "R5" in graph
    assert "E1" in graph


def test_wc01_produces_high_risk_or_rerouting():
    engine = WorstCaseScenarioEngine()
    scenario = next(s for s in engine.get_scenarios() if s["scenario_id"] == "WC01")
    result = engine.run_scenario(scenario)
    assert result.overall_risk in {"High", "Critical"}
    assert result.room_results
    assert result.rerouted_rooms or result.affected_occupants > 0


def test_wc02_creates_critical_result_or_trapped_rooms():
    engine = WorstCaseScenarioEngine()
    scenario = next(s for s in engine.get_scenarios() if s["scenario_id"] == "WC02")
    result = engine.run_scenario(scenario)
    assert result.overall_risk == "Critical"
    assert result.trapped_rooms or result.trapped_occupants > 0


def test_blocked_exit_changes_available_route():
    engine = WorstCaseScenarioEngine()
    scenario = next(s for s in engine.get_scenarios() if s["scenario_id"] == "WC03")
    result = engine.run_scenario(scenario)
    assert "E2" in result.affected_exits
    assert any(row["available_exit"] != "E2" for row in result.room_results if not row["trapped"])


def test_no_path_produces_trapped_result_instead_of_crashing():
    engine = WorstCaseScenarioEngine()
    scenario = {
        "scenario_id": "TEST_NO_PATH",
        "scenario_name": "Block both exits and corridor link",
        "fire_origin": "C1",
        "fire_origin_name": "Main Corridor",
        "fire_severity": "critical",
        "smoke_spread_nodes": ["C1", "C2"],
        "blocked_nodes": ["C1", "C2"],
        "blocked_edges": ["D10", "D11", "D9"],
        "high_risk_edges": [],
        "affected_exit": "E1",
        "occupancy_multiplier": 1.0,
        "pre_movement_delay_seconds": 120,
        "expected_risk": "Critical",
    }
    result = engine.run_scenario(scenario)
    assert result.overall_risk == "Critical"
    assert result.trapped_rooms


def test_auto_rank_worst_fire_origins_returns_sorted_results():
    engine = WorstCaseScenarioEngine()
    rankings = engine.auto_rank_fire_origins()
    assert rankings
    assert rankings[0]["rank"] == 1
    assert rankings == sorted(rankings, key=lambda r: r["rank"])
    assert rankings[0]["overall_risk"] in {"Medium", "High", "Critical"}


def test_export_includes_worst_case_scenario_fields():
    engine = WorstCaseScenarioEngine()
    scenario = next(s for s in engine.get_scenarios() if s["scenario_id"] == "WC04")
    result = engine.run_scenario(scenario)
    payload = json.loads(engine.to_json(result, auto_rankings=[]))
    assert payload["selected_fire_scenario"]["scenario_id"] == "WC04"
    assert "fire_origin" in payload
    assert "smoke_affected_nodes" in payload
    assert "room_results" in payload
    assert "limitations" in payload
    assert payload["hazard_priority_score"] == payload["risk_score"]
    assert "retained for compatibility" in payload["legacy_risk_score_note"]
    assert payload["score_semantics"]["direction"] == "higher_is_higher_screening_priority"
    assert payload["assumption_registry"]["calibration_status"] == "unvalidated_research_assumption"
