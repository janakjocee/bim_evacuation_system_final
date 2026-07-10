"""Combined fire-scenario engine for ASET/RSET-inspired screening."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
import copy
import json
from pathlib import Path

try:
    import networkx as nx
except ImportError:  # pragma: no cover
    nx = None

from src.scenario.worst_case_engine import (
    build_graph_from_dataset,
    classify_risk,
    load_worst_case_dataset,
    risk_sort_value,
    validate_scenario_dataset,
)
from .fire_growth import FireGrowthConfig, simulate_fire_growth
from .smoke_spread import SmokeSpreadConfig, simulate_smoke_spread
from .aset_rset import AsetRsetConfig, calculate_aset_rset
from .life_safety_impact import estimate_life_safety_impact
from .fds_exporter import create_fds_skeleton


ROOM_TYPE_GROWTH = {
    "office": "slow",
    "meeting_room": "slow",
    "classroom": "medium",
    "lecture_room": "medium",
    "lab": "fast",
    "corridor": "fast",
    "high_hazard": "fast",
    "service": "ultra_fast",
}


class FireScenarioEngine:
    """Run fire growth, smoke spread, ASET/RSET and life-safety impact checks."""

    def __init__(self, dataset: Optional[Dict[str, Any]] = None):
        self.dataset = dataset or load_worst_case_dataset()
        validate_scenario_dataset(self.dataset)
        if nx is None:
            raise RuntimeError("NetworkX is required for fire scenario analysis")
        self.graph = build_graph_from_dataset(self.dataset)
        self.spaces = self.dataset.get("spaces", [])
        self.space_by_id = {space["id"]: space for space in self.spaces}
        self.connections = self.dataset.get("connections", [])
        self.exit_ids = [space["id"] for space in self.spaces if space.get("type") == "exit"]
        self.defaults = self.dataset.get("fire_model_defaults", {})

    def get_scenarios(self) -> List[Dict[str, Any]]:
        return list(self.dataset.get("hazard_scenarios", []))

    def get_fire_origin_options(self) -> List[str]:
        return [space["id"] for space in self.spaces if space.get("type") != "exit"]

    def get_growth_class_for_room(self, room_id: str) -> str:
        space = self.space_by_id.get(room_id, {})
        return space.get("default_growth_class") or ROOM_TYPE_GROWTH.get(space.get("type"), "medium")

    def run_fire_scenario(self, scenario: Dict[str, Any], settings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        settings = settings or {}
        scenario = copy.deepcopy(scenario)
        fire_origin = scenario.get("fire_origin")
        if fire_origin not in self.graph:
            raise ValueError(f"Fire origin {fire_origin} is not present in the graph")

        growth_class = settings.get("fire_growth_class") or scenario.get("growth_class") or self.get_growth_class_for_room(fire_origin)
        duration = int(settings.get("simulation_duration_seconds", self.defaults.get("simulation_duration_seconds", 360)))
        step = int(settings.get("time_step_seconds", self.defaults.get("time_step_seconds", 30)))
        ventilation = float(settings.get("ventilation_factor", scenario.get("ventilation_factor", self.defaults.get("ventilation_factor", 1.0))))
        suppression_enabled = bool(settings.get("suppression_enabled", scenario.get("suppression_enabled", False)))
        sprinkler_time = int(settings.get("sprinkler_activation_time_seconds", scenario.get("sprinkler_activation_time_seconds", 180)))
        max_hrr = float(settings.get("max_hrr_kw", self.defaults.get("max_hrr_kw", 5000)))

        fire_growth = simulate_fire_growth(FireGrowthConfig(
            fire_origin=fire_origin,
            room_type=scenario.get("room_type", self.space_by_id.get(fire_origin, {}).get("type", "unknown")),
            fire_growth_class=growth_class,
            simulation_duration_seconds=duration,
            time_step_seconds=step,
            suppression_enabled=suppression_enabled,
            sprinkler_activation_time_seconds=sprinkler_time,
            ventilation_factor=ventilation,
            max_hrr_kw=max_hrr,
        ))

        fire_graph = self._hazard_adjusted_graph(scenario)
        smoke_result = simulate_smoke_spread(
            self.graph,
            fire_growth,
            SmokeSpreadConfig(
                fire_origin=fire_origin,
                door_state_assumption=settings.get("door_state_assumption", self.defaults.get("door_state_assumption", "mixed")),
                ventilation_factor=ventilation,
                smoke_spread_speed_factor=float(settings.get("smoke_spread_speed", scenario.get("smoke_spread_speed", 1.0))),
                fire_rated_separation=bool(settings.get("fire_rated_separation", False)),
                blocked_nodes=list(set(scenario.get("blocked_nodes", []) + [fire_origin])),
                blocked_edges=scenario.get("blocked_edges", []),
                exits=self.exit_ids,
            ),
        )

        # Remove untenable nodes at final time and explicitly blocked nodes/edges for route analysis.
        final_hazard_graph = self._hazard_adjusted_graph(scenario)
        for node in smoke_result.get("final_untenable_nodes", []):
            if node in final_hazard_graph and node not in self.exit_ids:
                final_hazard_graph.remove_node(node)
        affected_exits = sorted(set([scenario.get("affected_exit")] if scenario.get("affected_exit") else []) | set(smoke_result.get("affected_exits", [])))

        aset_cfg = AsetRsetConfig(
            detection_time_s=int(settings.get("detection_time", scenario.get("detection_time", 30))),
            alarm_time_s=int(settings.get("alarm_time", scenario.get("alarm_time", 15))),
            pre_movement_delay_s=int(settings.get("pre_movement_delay", scenario.get("pre_movement_delay", scenario.get("pre_movement_delay_seconds", 60)))),
            walking_speed_mps=float(settings.get("walking_speed_mps", self.defaults.get("walking_speed_mps", 1.2))),
            narrow_door_threshold_m=float(self.defaults.get("narrow_door_threshold_m", 0.8)),
            reduced_margin_threshold_s=int(self.defaults.get("reduced_margin_threshold_seconds", 60)),
        )
        aset_rset_results = calculate_aset_rset(
            normal_graph=self.graph,
            fire_graph=final_hazard_graph,
            spaces=self._occupancy_adjusted_spaces(scenario),
            exits=self.exit_ids,
            smoke_result=smoke_result,
            config=aset_cfg,
            affected_exits=affected_exits,
        )
        impact = estimate_life_safety_impact(aset_rset_results, smoke_result)
        risk_score = self._risk_score(aset_rset_results, impact, affected_exits)
        overall_risk = classify_risk(risk_score)
        compliance_checks = self._compliance_checks(aset_rset_results, impact, affected_exits)
        explanation = self._explain(scenario, fire_growth, smoke_result, aset_rset_results, impact, overall_risk)
        result = {
            "scenario": scenario,
            "fire_scenario_id": scenario.get("scenario_id"),
            "fire_scenario_name": scenario.get("scenario_name"),
            "fire_origin": fire_origin,
            "fire_origin_name": scenario.get("fire_origin_name") or self.space_by_id.get(fire_origin, {}).get("name", fire_origin),
            "fire_growth_class": growth_class,
            "fire_growth": fire_growth,
            "smoke_spread": smoke_result,
            "affected_rooms_corridors": sorted(set(smoke_result.get("final_smoke_affected_nodes", [])) | set(smoke_result.get("final_high_risk_nodes", [])) | set(smoke_result.get("final_untenable_nodes", []))),
            "untenable_time_per_node": smoke_result.get("time_to_untenable", {}),
            "affected_exits": affected_exits,
            "aset_rset_results": aset_rset_results,
            "life_safety_impact": impact,
            "trapped_rooms": [row["room_id"] for row in aset_rset_results if row.get("classification") == "no route / trapped"],
            "potentially_affected_occupants": impact.get("potentially_affected_occupants", 0),
            "overall_risk_score": risk_score,
            "overall_risk_level": overall_risk,
            "compliance_oriented_checks": compliance_checks,
            "expert_review_recommendation": "Expert review required: verify fire origin assumptions, smoke control, compartmentation, exit availability, RSET/ASET margins and BIM data completeness.",
            "explanation": explanation,
            "fds_skeleton": "Use export_fds_skeleton(result) to generate an expert-completion FDS template.",
            "limitations": "Academic decision-support only. No CFD, no certified evacuation modelling, no toxic gas/FED model and no final fire-safety certification.",
        }
        return result

    def auto_rank_worst_fire_origins(self, settings: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for origin in self.get_fire_origin_options():
            space = self.space_by_id.get(origin, {})
            neighbours = list(self.graph.neighbors(origin)) if origin in self.graph else []
            scenario = {
                "scenario_id": f"AUTO_FIRE_{origin}",
                "scenario_name": f"Automatic fire-origin screening at {space.get('name', origin)}",
                "fire_origin": origin,
                "fire_origin_name": space.get("name", origin),
                "room_type": space.get("type", "unknown"),
                "growth_class": self.get_growth_class_for_room(origin),
                "detection_time": 45,
                "alarm_time": 15,
                "pre_movement_delay": 90 if space.get("type") in {"corridor", "high_hazard", "service"} else 60,
                "ventilation_factor": 1.1 if space.get("type") in {"corridor", "high_hazard", "service"} else 1.0,
                "smoke_spread_speed": 1.15 if space.get("type") in {"corridor", "high_hazard", "service"} else 1.0,
                "blocked_nodes": [origin],
                "blocked_edges": [],
                "affected_exit": self._nearest_exit(origin),
                "suppression_enabled": False,
                "occupancy_multiplier": 1.25,
            }
            result = self.run_fire_scenario(scenario, settings=settings)
            margins = [row.get("safety_margin_s") for row in result["aset_rset_results"] if row.get("safety_margin_s") is not None]
            rows.append({
                "rank": 0,
                "fire_origin": origin,
                "fire_origin_name": space.get("name", origin),
                "room_type": space.get("type", "unknown"),
                "growth_class": scenario["growth_class"],
                "affected_exits": ", ".join(result.get("affected_exits", [])) or "None",
                "trapped_occupants": result["life_safety_impact"].get("trapped_occupants", 0),
                "potentially_affected_occupants": result["life_safety_impact"].get("potentially_affected_occupants", 0),
                "worst_safety_margin_s": min(margins) if margins else None,
                "overall_risk": result["overall_risk_level"],
                "risk_score": result["overall_risk_score"],
                "main_reason": result["explanation"][:240] + "...",
            })
        rows.sort(key=lambda row: (risk_sort_value(row["overall_risk"]), row["trapped_occupants"], row["potentially_affected_occupants"], row["risk_score"]), reverse=True)
        for idx, row in enumerate(rows, 1):
            row["rank"] = idx
        return rows

    def export_fds_skeleton(self, result: Dict[str, Any]) -> str:
        return create_fds_skeleton(result)

    def _hazard_adjusted_graph(self, scenario: Dict[str, Any]) -> Any:
        graph = copy.deepcopy(self.graph)
        blocked_edges = set(scenario.get("blocked_edges", []))
        for u, v, data in list(graph.edges(data=True)):
            if str(data.get("connection_id")) in blocked_edges and graph.has_edge(u, v):
                graph.remove_edge(u, v)
        for node in set(scenario.get("blocked_nodes", [])) | {scenario.get("fire_origin")}:
            if node in graph:
                graph.remove_node(node)
        high_risk_edges = set(scenario.get("high_risk_edges", []))
        for u, v, data in graph.edges(data=True):
            if str(data.get("connection_id")) in high_risk_edges:
                data["weight"] = float(data.get("weight", 1.0)) + 25
        return graph

    def _occupancy_adjusted_spaces(self, scenario: Dict[str, Any]) -> List[Dict[str, Any]]:
        multiplier = float(scenario.get("occupancy_multiplier", 1.0))
        adjusted = []
        for space in self.spaces:
            clone = copy.deepcopy(space)
            clone["occupancy"] = int(round(int(clone.get("occupancy", 0)) * multiplier))
            adjusted.append(clone)
        return adjusted

    def _nearest_exit(self, origin: str) -> Optional[str]:
        if origin not in self.graph:
            return self.exit_ids[0] if self.exit_ids else None
        routes = []
        for exit_id in self.exit_ids:
            try:
                length = nx.shortest_path_length(self.graph, origin, exit_id, weight="weight")
                routes.append((length, exit_id))
            except Exception:
                pass
        return sorted(routes)[0][1] if routes else (self.exit_ids[0] if self.exit_ids else None)

    def _risk_score(self, rows: List[Dict[str, Any]], impact: Dict[str, Any], affected_exits: List[str]) -> int:
        score = 0
        score += 100 if impact.get("trapped_occupants", 0) > 0 else 0
        score += 35 if impact.get("rset_exceeds_aset_occupants", 0) > 0 else 0
        score += 25 if affected_exits else 0
        score += 20 if impact.get("high_risk_reduced_margin_occupants", 0) > 0 else 0
        score += 20 if any(row.get("rerouted") for row in rows) else 0
        score += min(30, int(impact.get("smoke_route_exposure_occupants", 0) / 5))
        return score

    def _compliance_checks(self, rows: List[Dict[str, Any]], impact: Dict[str, Any], affected_exits: List[str]) -> List[Dict[str, str]]:
        trapped = [r for r in rows if r.get("classification") == "no route / trapped"]
        unsafe = [r for r in rows if r.get("classification") == "unsafe"]
        bottlenecks = [r for r in rows if r.get("bottleneck_edges")]
        return [
            {"check": "Route available from every occupied room", "result": "Fail" if trapped else "Pass", "evidence": f"{len(trapped)} trapped rooms detected.", "recommendation": "Provide/verify alternative routes and protected escape paths."},
            {"check": "RSET below ASET", "result": "Fail" if unsafe else "Pass", "evidence": f"{len(unsafe)} rooms have RSET greater than ASET.", "recommendation": "Review detection, alarm, pre-movement delay, smoke control and travel distance assumptions."},
            {"check": "Affected exit warning", "result": "Warning" if affected_exits else "Pass", "evidence": f"Affected exits: {', '.join(affected_exits) or 'None'}.", "recommendation": "Validate exit redundancy under fire-origin assumptions."},
            {"check": "Bottleneck/narrow door warning", "result": "Warning" if bottlenecks else "Pass", "evidence": f"{len(bottlenecks)} routes include bottleneck edges.", "recommendation": "Review door width, occupant load and route capacity."},
            {"check": "Regulatory/RAG link", "result": "Requires Review", "evidence": "Use selected regulation source or conservative fallback constraints.", "recommendation": "Low-confidence or missing regulation evidence must be reviewed by an expert."},
        ]

    def _explain(self, scenario: Dict[str, Any], growth: Dict[str, Any], smoke: Dict[str, Any], rows: List[Dict[str, Any]], impact: Dict[str, Any], risk: str) -> str:
        origin = scenario.get("fire_origin_name", scenario.get("fire_origin"))
        trapped_rooms = [row["room_name"] for row in rows if row.get("classification") == "no route / trapped"]
        unsafe_rooms = [row["room_name"] for row in rows if row.get("classification") == "unsafe"]
        affected = ", ".join(smoke.get("final_smoke_affected_nodes", [])) or "no final smoke-affected spaces"
        text = (
            f"This ASET/RSET fire-origin-based scenario is classified as {risk}. Fire starts in {origin} using a {growth.get('growth_class')} t-squared growth assumption, "
            f"with peak HRR approximately {growth.get('peak_hrr_kw')} kW. The graph-based smoke spread approximation identifies {affected}. "
        )
        if trapped_rooms:
            text += f"Trapped rooms detected: {', '.join(trapped_rooms)}. "
        if unsafe_rooms:
            text += f"Rooms where RSET exceeds ASET: {', '.join(unsafe_rooms)}. "
        text += (
            f"Indicative life-safety impact reports {impact.get('potentially_affected_occupants', 0)} potentially affected occupants. "
            "This result requires expert validation and should be treated as compliance-oriented decision support, not CFD, not certified evacuation modelling and not final approval."
        )
        return text
