"""Tests for the ASET/RSET-inspired fire modelling package."""

from src.fire.fire_growth import FireGrowthConfig, simulate_fire_growth
from src.fire.smoke_spread import SmokeSpreadConfig, simulate_smoke_spread
from src.fire.aset_rset import AsetRsetConfig, calculate_aset_rset
from src.fire.life_safety_impact import estimate_life_safety_impact
from src.fire.fire_scenario_engine import FireScenarioEngine
from src.scenario.worst_case_engine import build_graph_from_dataset, load_worst_case_dataset


def test_fire_growth_hrr_calculation():
    result = simulate_fire_growth(FireGrowthConfig(
        fire_origin="R5",
        fire_growth_class="fast",
        simulation_duration_seconds=60,
        time_step_seconds=60,
        max_hrr_kw=10000,
    ))
    assert result["time_series"][1]["time_s"] == 60
    assert abs(result["time_series"][1]["hrr_kw"] - 168.84) < 0.01
    assert result["peak_hrr_kw"] > 0


def test_suppression_reduces_or_caps_hrr():
    without = simulate_fire_growth(FireGrowthConfig(
        fire_origin="R5", fire_growth_class="fast", simulation_duration_seconds=240, time_step_seconds=120, max_hrr_kw=10000
    ))
    with_suppression = simulate_fire_growth(FireGrowthConfig(
        fire_origin="R5", fire_growth_class="fast", simulation_duration_seconds=240, time_step_seconds=120,
        suppression_enabled=True, sprinkler_activation_time_seconds=120, max_hrr_kw=10000
    ))
    assert with_suppression["peak_hrr_kw"] < without["peak_hrr_kw"]


def test_smoke_spreads_to_adjacent_graph_nodes():
    dataset = load_worst_case_dataset()
    graph = build_graph_from_dataset(dataset)
    growth = simulate_fire_growth(FireGrowthConfig(fire_origin="R5", fire_growth_class="fast", simulation_duration_seconds=180, time_step_seconds=60))
    smoke = simulate_smoke_spread(graph, growth, SmokeSpreadConfig(fire_origin="R5", exits=["E1", "E2"]))
    final_affected = set(smoke["final_smoke_affected_nodes"] + smoke["final_high_risk_nodes"] + smoke["final_untenable_nodes"])
    assert "C1" in final_affected


def test_aset_rset_calculation_returns_safety_margin():
    engine = FireScenarioEngine()
    scenario = next(s for s in engine.get_scenarios() if s["scenario_id"] == "WC01")
    result = engine.run_fire_scenario(scenario, {"simulation_duration_seconds": 240, "time_step_seconds": 60})
    assert result["aset_rset_results"]
    assert "safety_margin_s" in result["aset_rset_results"][0]


def test_trapped_occupants_detected_when_no_route_exists():
    engine = FireScenarioEngine()
    scenario = {
        "scenario_id": "NO_ROUTE",
        "scenario_name": "No route test",
        "fire_origin": "C1",
        "fire_origin_name": "Main Corridor",
        "room_type": "corridor",
        "growth_class": "fast",
        "detection_time": 30,
        "alarm_time": 15,
        "pre_movement_delay": 60,
        "ventilation_factor": 1.0,
        "smoke_spread_speed": 1.0,
        "blocked_nodes": ["C1", "C2"],
        "blocked_edges": ["D9", "D10", "D11"],
        "affected_exit": "E1",
        "suppression_enabled": False,
        "occupancy_multiplier": 1.0,
    }
    result = engine.run_fire_scenario(scenario)
    assert result["life_safety_impact"]["trapped_occupants"] > 0
    assert result["overall_risk_level"] == "Critical"


def test_rset_greater_than_aset_produces_unsafe_classification():
    engine = FireScenarioEngine()
    scenario = next(s for s in engine.get_scenarios() if s["scenario_id"] == "WC05")
    result = engine.run_fire_scenario(scenario, {"pre_movement_delay": 240, "simulation_duration_seconds": 180, "time_step_seconds": 30})
    classifications = {row["classification"] for row in result["aset_rset_results"]}
    assert "unsafe" in classifications or "no route / trapped" in classifications


def test_life_safety_impact_avoids_forbidden_wording():
    impact = estimate_life_safety_impact([
        {"room_id": "R1", "room_name": "Classroom A", "occupancy": 10, "classification": "unsafe", "fire_route": ["R1", "C1", "E1"]}
    ], {"final_smoke_affected_nodes": ["C1"], "final_high_risk_nodes": []})
    text = impact["explanation"].lower()
    assert "confirmed casualties" not in text
    assert "certified casualty prediction" not in text
    assert "final legal safety result" not in text
    assert impact["potentially_affected_occupants"] == 10


def test_auto_rank_worst_fire_origins_returns_sorted_risks():
    engine = FireScenarioEngine()
    rankings = engine.auto_rank_worst_fire_origins({"simulation_duration_seconds": 120, "time_step_seconds": 60})
    assert rankings
    assert rankings[0]["rank"] == 1
    assert rankings == sorted(rankings, key=lambda row: row["rank"])


def test_export_includes_fire_scenario_outputs():
    engine = FireScenarioEngine()
    scenario = next(s for s in engine.get_scenarios() if s["scenario_id"] == "WC01")
    result = engine.run_fire_scenario(scenario)
    assert "fire_growth" in result
    assert "smoke_spread" in result
    assert "aset_rset_results" in result
    assert "fds_skeleton" in result
    fds = engine.export_fds_skeleton(result)
    assert "FDS skeleton for expert completion" in fds
