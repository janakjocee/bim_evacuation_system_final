"""
Fire-origin worst-case scenario engine.

This module provides an indicative decision-support model for analysing
fire-origin-based worst-case evacuation scenarios. It is intentionally graph-based
and explainable: it does not perform CFD, certified evacuation modelling, or final
fire-safety approval. All outputs require human-in-the-loop expert review.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
import copy
import csv
import io
import json
import math

try:
    import networkx as nx
except ImportError:  # pragma: no cover - handled gracefully for UI/runtime
    nx = None


DEFAULT_DATASET_PATH = Path(__file__).resolve().parents[2] / "data" / "demo_worst_case_building.json"


@dataclass
class RiskScoringConfig:
    """Configurable risk scoring weights."""

    no_path_to_exit: int = 100
    only_one_exit_available: int = 25
    nearest_route_blocked: int = 20
    travel_distance_above_threshold: int = 20
    narrow_door_below_threshold: int = 15
    high_occupancy: int = 15
    bottleneck_encountered: int = 15
    smoke_or_high_risk_route: int = 25
    long_pre_movement_delay: int = 10
    travel_distance_threshold_m: float = 45.0
    narrow_door_threshold_m: float = 0.8
    high_occupancy_threshold: int = 50
    pre_movement_delay_threshold_s: int = 90
    walking_speed_mps: float = 1.2
    smoke_edge_weight_penalty: float = 25.0
    smoke_node_weight_penalty: float = 30.0


@dataclass
class WorstCaseResult:
    """Structured result for a worst-case analysis."""

    selected_fire_scenario: Dict[str, Any]
    fire_origin: str
    fire_origin_name: str
    smoke_affected_nodes: List[str]
    blocked_nodes: List[str]
    blocked_edges: List[str]
    affected_exits: List[str]
    room_results: List[Dict[str, Any]]
    compliance_checks: List[Dict[str, Any]]
    trapped_rooms: List[str]
    rerouted_rooms: List[str]
    safe_rooms: List[str]
    affected_occupants: int
    trapped_occupants: int
    average_delay_increase_s: float
    risk_score: int
    overall_risk: str
    explanation: str
    limitations: str = (
        "Indicative compliance-oriented screening only. This is not certified fire engineering, "
        "not CFD, not physical fire simulation, and not a replacement for qualified fire-safety review."
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "selected_fire_scenario": self.selected_fire_scenario,
            "fire_origin": self.fire_origin,
            "fire_origin_name": self.fire_origin_name,
            "smoke_affected_nodes": self.smoke_affected_nodes,
            "blocked_nodes": self.blocked_nodes,
            "blocked_edges": self.blocked_edges,
            "affected_exits": self.affected_exits,
            "room_results": self.room_results,
            "compliance_checks": self.compliance_checks,
            "trapped_rooms": self.trapped_rooms,
            "rerouted_rooms": self.rerouted_rooms,
            "safe_rooms": self.safe_rooms,
            "affected_occupants": self.affected_occupants,
            "trapped_occupants": self.trapped_occupants,
            "average_delay_increase_s": round(self.average_delay_increase_s, 1),
            "risk_score": self.risk_score,
            "overall_risk": self.overall_risk,
            "explanation": self.explanation,
            "limitations": self.limitations,
        }


class WorstCaseScenarioEngine:
    """Run fire-origin-based worst-case evacuation analysis over a building graph."""

    def __init__(self, dataset: Optional[Dict[str, Any]] = None, config: Optional[RiskScoringConfig] = None):
        self.dataset = dataset or load_worst_case_dataset()
        validate_scenario_dataset(self.dataset)
        self.config = config or RiskScoringConfig()
        self.graph = build_graph_from_dataset(self.dataset)
        self.connection_by_id = {c["id"]: c for c in self.dataset.get("connections", [])}
        self.space_by_id = {s["id"]: s for s in self.dataset.get("spaces", [])}
        self.exit_ids = [s["id"] for s in self.dataset.get("spaces", []) if s.get("type") == "exit"]

    def get_scenarios(self) -> List[Dict[str, Any]]:
        return list(self.dataset.get("hazard_scenarios", []))

    def get_node_options(self) -> List[str]:
        return list(self.space_by_id.keys())

    def get_edge_options(self) -> List[str]:
        return list(self.connection_by_id.keys())

    def run_scenario(self, scenario: Dict[str, Any]) -> WorstCaseResult:
        """Run a predefined or user-modified fire scenario."""
        if nx is None:
            raise RuntimeError("NetworkX is required for worst-case scenario analysis")

        fire_origin = scenario.get("fire_origin")
        if not fire_origin or fire_origin not in self.graph:
            raise ValueError(f"Invalid fire origin: {fire_origin}")

        blocked_nodes = list(dict.fromkeys(scenario.get("blocked_nodes", []) + [fire_origin]))
        blocked_edges = list(dict.fromkeys(scenario.get("blocked_edges", [])))
        smoke_nodes = list(dict.fromkeys(scenario.get("smoke_spread_nodes", [])))
        high_risk_edges = list(dict.fromkeys(scenario.get("high_risk_edges", [])))
        affected_exit = scenario.get("affected_exit")
        affected_exits = [affected_exit] if affected_exit else []

        normal_graph = copy.deepcopy(self.graph)
        hazard_graph = copy.deepcopy(self.graph)

        # Remove blocked evacuation route edges first.
        for edge_id in blocked_edges:
            self._remove_edge_by_id(hazard_graph, edge_id)

        # Remove directly blocked fire/hazard nodes. For critical smoke scenarios, smoke-filled
        # corridor nodes are often supplied in blocked_nodes by the dataset or UI.
        for node_id in blocked_nodes:
            if node_id in hazard_graph:
                hazard_graph.remove_node(node_id)

        # If the user explicitly blocks nearest/affected exit, remove it from hazard graph.
        for exit_id in affected_exits:
            scenario_severity = str(scenario.get("fire_severity", "")).lower()
            if scenario_severity == "critical" and exit_id in hazard_graph:
                hazard_graph.remove_node(exit_id)

        # Penalise smoke affected nodes and high-risk edges that remain available.
        self._apply_smoke_penalties(hazard_graph, smoke_nodes, high_risk_edges)

        room_results: List[Dict[str, Any]] = []
        occupied_rooms = self._occupied_room_ids()

        for room_id in occupied_rooms:
            result = self._analyse_room(room_id, normal_graph, hazard_graph, scenario, smoke_nodes, high_risk_edges)
            room_results.append(result)

        trapped_rooms = [r["start_room"] for r in room_results if r["trapped"]]
        rerouted_rooms = [r["start_room"] for r in room_results if r["rerouted"]]
        safe_rooms = [r["start_room"] for r in room_results if not r["trapped"] and r["risk_level"] in {"Low", "Medium"}]
        affected_occupants = sum(r["occupancy"] for r in room_results if r["risk_level"] in {"High", "Critical"})
        trapped_occupants = sum(r["occupancy"] for r in room_results if r["trapped"])
        delay_values = [r["delay_increase_s"] for r in room_results if r["delay_increase_s"] is not None]
        avg_delay = sum(delay_values) / len(delay_values) if delay_values else 0.0

        risk_score = self._overall_risk_score(room_results, scenario, len(self._available_exits(hazard_graph)))
        overall_risk = classify_risk(risk_score)
        compliance_checks = self.generate_compliance_checks(room_results, scenario, trapped_rooms)
        explanation = self.generate_explanation(
            scenario=scenario,
            room_results=room_results,
            trapped_rooms=trapped_rooms,
            rerouted_rooms=rerouted_rooms,
            affected_occupants=affected_occupants,
            overall_risk=overall_risk,
        )

        return WorstCaseResult(
            selected_fire_scenario=scenario,
            fire_origin=fire_origin,
            fire_origin_name=scenario.get("fire_origin_name") or self._node_name(fire_origin),
            smoke_affected_nodes=smoke_nodes,
            blocked_nodes=blocked_nodes,
            blocked_edges=blocked_edges,
            affected_exits=affected_exits,
            room_results=room_results,
            compliance_checks=compliance_checks,
            trapped_rooms=trapped_rooms,
            rerouted_rooms=rerouted_rooms,
            safe_rooms=safe_rooms,
            affected_occupants=affected_occupants,
            trapped_occupants=trapped_occupants,
            average_delay_increase_s=avg_delay,
            risk_score=risk_score,
            overall_risk=overall_risk,
            explanation=explanation,
        )

    def auto_rank_fire_origins(self) -> List[Dict[str, Any]]:
        """Treat each room/corridor as a possible fire origin and rank severity."""
        rankings: List[Dict[str, Any]] = []
        candidate_origins = [
            s["id"] for s in self.dataset.get("spaces", [])
            if s.get("type") not in {"exit"}
        ]

        for origin in candidate_origins:
            neighbours = list(self.graph.neighbors(origin)) if origin in self.graph else []
            smoke_nodes = [n for n in neighbours if n in self.space_by_id]
            blocked_edges = [
                data.get("connection_id")
                for _, _, data in self.graph.edges(origin, data=True)
                if data.get("connection_id")
            ]
            node_type = self.space_by_id.get(origin, {}).get("type", "unknown")
            severity = "critical" if node_type in {"high_hazard", "service"} else "high" if node_type == "corridor" else "medium"
            scenario = {
                "scenario_id": f"AUTO_{origin}",
                "scenario_name": f"Auto-ranked fire origin at {self._node_name(origin)}",
                "fire_origin": origin,
                "fire_origin_name": self._node_name(origin),
                "fire_severity": severity,
                "smoke_spread_nodes": smoke_nodes,
                "blocked_nodes": [origin],
                "blocked_edges": blocked_edges[:1],
                "high_risk_edges": blocked_edges[1:],
                "affected_exit": self._nearest_exit(origin),
                "occupancy_multiplier": 1.25 if node_type in {"corridor", "lecture_room"} else 1.0,
                "pre_movement_delay_seconds": 90 if severity == "critical" else 60,
                "expected_risk": "Critical" if severity == "critical" else "High",
            }
            result = self.run_scenario(scenario)
            worst_margin = min((r.get("delay_increase_s") or 0 for r in result.room_results), default=0)
            rankings.append({
                "rank": 0,
                "fire_origin": origin,
                "fire_origin_name": self._node_name(origin),
                "affected_occupants": result.affected_occupants,
                "trapped_rooms": len(result.trapped_rooms),
                "trapped_room_names": ", ".join(self._node_name(r) for r in result.trapped_rooms) or "None",
                "unavailable_exits": ", ".join(result.affected_exits) or "None",
                "average_delay_increase_s": round(result.average_delay_increase_s, 1),
                "worst_delay_increase_s": round(worst_margin, 1),
                "overall_risk": result.overall_risk,
                "risk_score": result.risk_score,
                "main_reason": self._ranking_reason(result, origin),
            })

        rankings.sort(key=lambda r: (risk_sort_value(r["overall_risk"]), r["trapped_rooms"], r["affected_occupants"], r["risk_score"]), reverse=True)
        for idx, row in enumerate(rankings, start=1):
            row["rank"] = idx
        return rankings

    def generate_compliance_checks(self, room_results: List[Dict[str, Any]], scenario: Dict[str, Any], trapped_rooms: List[str]) -> List[Dict[str, Any]]:
        """Generate compliance-oriented screening checks for the scenario."""
        checks: List[Dict[str, Any]] = []
        occupied_count = len(room_results)
        routed_count = sum(1 for r in room_results if not r["trapped"])
        rerouted_count = sum(1 for r in room_results if r["rerouted"])
        long_routes = [r for r in room_results if (r["worst_case_distance_m"] or 0) > self.config.travel_distance_threshold_m]
        bottlenecks = [r for r in room_results if r["bottleneck_edges"]]
        high_occ = [r for r in room_results if r["occupancy"] > self.config.high_occupancy_threshold]

        checks.append({
            "rule_check": "Every occupied room has at least one available evacuation route",
            "result": "Fail" if trapped_rooms else "Pass",
            "evidence": f"{routed_count}/{occupied_count} occupied rooms have a route after fire-origin disruption.",
            "recommendation": "Investigate trapped rooms and provide alternative escape route." if trapped_rooms else "No trapped rooms found in this indicative screening."
        })
        checks.append({
            "rule_check": "Alternative route availability when one exit or route is affected",
            "result": "Warning" if rerouted_count else "Requires Review",
            "evidence": f"{rerouted_count} rooms were forced onto alternative routes.",
            "recommendation": "Expert should confirm route redundancy, signage, compartmentation and door performance."
        })
        checks.append({
            "rule_check": "Travel distance remains within selected threshold",
            "result": "Fail" if long_routes else "Pass",
            "evidence": f"{len(long_routes)} routes exceed {self.config.travel_distance_threshold_m:.0f} m threshold.",
            "recommendation": "Review exit locations, protected corridors, or evacuation strategy." if long_routes else "Distances remain within the configured threshold."
        })
        checks.append({
            "rule_check": "Door width bottlenecks are flagged",
            "result": "Warning" if bottlenecks else "Pass",
            "evidence": f"{len(bottlenecks)} room routes include door/corridor widths below {self.config.narrow_door_threshold_m:.2f} m.",
            "recommendation": "Review bottleneck capacity and consider widening or rerouting." if bottlenecks else "No narrow-door bottlenecks were detected on selected routes."
        })
        checks.append({
            "rule_check": "High occupancy rooms are flagged",
            "result": "Warning" if high_occ else "Pass",
            "evidence": f"{len(high_occ)} rooms exceed {self.config.high_occupancy_threshold} occupants under multiplier assumptions.",
            "recommendation": "Expert should validate occupant load and evacuation management controls." if high_occ else "No high-occupancy warning triggered."
        })
        checks.append({
            "rule_check": "Fire-origin scenario requires expert review",
            "result": "Requires Review",
            "evidence": f"Scenario {scenario.get('scenario_id')} models fire origin {scenario.get('fire_origin_name', scenario.get('fire_origin'))}.",
            "recommendation": "Indicative compliance-oriented screening only. Requires expert review."
        })
        return checks

    def to_json(self, result: WorstCaseResult, auto_rankings: Optional[List[Dict[str, Any]]] = None, expert_reviews: Optional[Any] = None) -> str:
        data = result.to_dict()
        data["auto_ranked_worst_fire_origins"] = auto_rankings or []
        data["expert_review_notes"] = expert_reviews or []
        return json.dumps(data, indent=2)

    def to_csv(self, result: WorstCaseResult) -> str:
        output = io.StringIO()
        fieldnames = [
            "start_room", "start_room_name", "occupancy", "normal_route", "worst_case_route",
            "normal_distance_m", "worst_case_distance_m", "delay_increase_s", "available_exit",
            "trapped", "risk_score", "risk_level", "explanation"
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for row in result.room_results:
            csv_row = row.copy()
            csv_row["normal_route"] = " -> ".join(row.get("normal_route") or [])
            csv_row["worst_case_route"] = " -> ".join(row.get("worst_case_route") or [])
            writer.writerow({key: csv_row.get(key, "") for key in fieldnames})
        return output.getvalue()

    def to_html_report(self, result: WorstCaseResult, auto_rankings: Optional[List[Dict[str, Any]]] = None, expert_reviews: Optional[Any] = None) -> str:
        rows = "".join(
            f"<tr><td>{r['start_room_name']}</td><td>{r['occupancy']}</td><td>{r['risk_level']}</td>"
            f"<td>{'Yes' if r['trapped'] else 'No'}</td><td>{r.get('available_exit') or 'None'}</td>"
            f"<td>{r.get('worst_case_distance_m') if r.get('worst_case_distance_m') is not None else 'No path'}</td></tr>"
            for r in result.room_results
        )
        ranking_rows = "".join(
            f"<tr><td>{r['rank']}</td><td>{r['fire_origin_name']}</td><td>{r['affected_occupants']}</td>"
            f"<td>{r['trapped_rooms']}</td><td>{r['overall_risk']}</td><td>{r['main_reason']}</td></tr>"
            for r in (auto_rankings or [])
        )
        review_html = f"<pre>{json.dumps(expert_reviews or [], indent=2)}</pre>"
        return f"""<!DOCTYPE html>
<html>
<head>
<meta charset=\"utf-8\">
<title>Worst-Case Fire-Origin Scenario Report</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 32px; line-height: 1.5; }}
h1, h2 {{ color: #1a1a2e; }}
.badge {{ display: inline-block; padding: 8px 12px; border-radius: 6px; background: #ffebee; color: #b00020; font-weight: bold; }}
table {{ border-collapse: collapse; width: 100%; margin: 16px 0; }}
th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
th {{ background: #f4f4f4; }}
.notice {{ border-left: 4px solid #f44336; background: #fff5f5; padding: 12px; }}
</style>
</head>
<body>
<h1>Fire-Origin Worst-Case Scenario Report</h1>
<p><strong>Building:</strong> {self.dataset.get('building_name')}</p>
<p><strong>Scenario:</strong> {result.selected_fire_scenario.get('scenario_id')} - {result.selected_fire_scenario.get('scenario_name')}</p>
<p><span class=\"badge\">Overall Risk: {result.overall_risk} ({result.risk_score})</span></p>
<h2>Hazard Summary</h2>
<ul>
<li><strong>Fire origin:</strong> {result.fire_origin_name} ({result.fire_origin})</li>
<li><strong>Smoke affected areas:</strong> {', '.join(result.smoke_affected_nodes) or 'None'}</li>
<li><strong>Blocked nodes:</strong> {', '.join(result.blocked_nodes) or 'None'}</li>
<li><strong>Blocked edges:</strong> {', '.join(result.blocked_edges) or 'None'}</li>
<li><strong>Affected exits:</strong> {', '.join(result.affected_exits) or 'None'}</li>
<li><strong>Trapped rooms:</strong> {', '.join(result.trapped_rooms) or 'None'}</li>
<li><strong>Affected occupants:</strong> {result.affected_occupants}</li>
<li><strong>Trapped occupants:</strong> {result.trapped_occupants}</li>
</ul>
<h2>Room-by-Room Results</h2>
<table><tr><th>Room</th><th>Occupancy</th><th>Risk</th><th>Trapped</th><th>Available Exit</th><th>Worst-case Distance (m)</th></tr>{rows}</table>
<h2>Compliance-Oriented Screening</h2>
<table><tr><th>Check</th><th>Result</th><th>Evidence</th><th>Recommendation</th></tr>
{''.join(f"<tr><td>{c['rule_check']}</td><td>{c['result']}</td><td>{c['evidence']}</td><td>{c['recommendation']}</td></tr>" for c in result.compliance_checks)}
</table>
<h2>Auto-ranked Worst Fire Origins</h2>
<table><tr><th>Rank</th><th>Fire Origin</th><th>Affected Occupants</th><th>Trapped Rooms</th><th>Risk</th><th>Main Reason</th></tr>{ranking_rows}</table>
<h2>Explanation</h2>
<p>{result.explanation}</p>
<h2>Expert Review Notes</h2>
{review_html}
<div class=\"notice\"><strong>Limitations:</strong> {result.limitations}</div>
</body></html>"""

    def _analyse_room(self, room_id: str, normal_graph: Any, hazard_graph: Any, scenario: Dict[str, Any], smoke_nodes: List[str], high_risk_edges: List[str]) -> Dict[str, Any]:
        base_space = self.space_by_id.get(room_id, {})
        occupancy = int(math.ceil(base_space.get("occupancy", 0) * float(scenario.get("occupancy_multiplier", 1.0))))

        normal_route = self._best_route(normal_graph, room_id)
        worst_route = self._best_route(hazard_graph, room_id)
        normal_distance = normal_route["distance"] if normal_route else None
        worst_distance = worst_route["distance"] if worst_route else None
        delay_increase = None
        if normal_route and worst_route:
            delay_increase = max(0.0, worst_route["time"] - normal_route["time"])

        trapped = worst_route is None
        rerouted = bool(normal_route and worst_route and normal_route["path"] != worst_route["path"])
        risk_score, reasons, bottleneck_edges = self._room_risk_score(
            room_id=room_id,
            occupancy=occupancy,
            normal_route=normal_route,
            worst_route=worst_route,
            scenario=scenario,
            smoke_nodes=smoke_nodes,
            high_risk_edges=high_risk_edges,
            hazard_graph=hazard_graph,
        )
        risk_level = classify_risk(risk_score)
        explanation = self._room_explanation(room_id, risk_level, trapped, rerouted, reasons, worst_route)

        return {
            "start_room": room_id,
            "start_room_name": self._node_name(room_id),
            "occupancy": occupancy,
            "normal_route": normal_route["path"] if normal_route else None,
            "worst_case_route": worst_route["path"] if worst_route else None,
            "normal_distance_m": round(normal_distance, 2) if normal_distance is not None else None,
            "worst_case_distance_m": round(worst_distance, 2) if worst_distance is not None else None,
            "normal_time_s": round(normal_route["time"], 1) if normal_route else None,
            "worst_case_time_s": round(worst_route["time"], 1) if worst_route else None,
            "delay_increase_s": round(delay_increase, 1) if delay_increase is not None else None,
            "available_exit": worst_route["exit"] if worst_route else None,
            "blocked_elements_encountered_or_avoided": list(dict.fromkeys(scenario.get("blocked_nodes", []) + scenario.get("blocked_edges", []))),
            "trapped": trapped,
            "rerouted": rerouted,
            "bottleneck_edges": bottleneck_edges,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "explanation": explanation,
        }

    def _best_route(self, graph: Any, origin: str) -> Optional[Dict[str, Any]]:
        if origin not in graph:
            return None
        routes: List[Dict[str, Any]] = []
        for exit_id in self._available_exits(graph):
            try:
                path = nx.shortest_path(graph, origin, exit_id, weight="weight")
                distance = nx.shortest_path_length(graph, origin, exit_id, weight="weight")
                route_edges = list(zip(path[:-1], path[1:]))
                min_width = min((graph.edges[e].get("width_m", 1.0) for e in route_edges), default=1.0)
                congestion_delay = self._congestion_delay(origin, min_width)
                time_s = distance / self.config.walking_speed_mps + congestion_delay
                routes.append({"path": path, "distance": distance, "time": time_s, "exit": exit_id, "min_width": min_width})
            except Exception:
                continue
        if not routes:
            return None
        return sorted(routes, key=lambda r: (r["time"], r["distance"]))[0]

    def _room_risk_score(self, room_id: str, occupancy: int, normal_route: Optional[Dict[str, Any]], worst_route: Optional[Dict[str, Any]], scenario: Dict[str, Any], smoke_nodes: List[str], high_risk_edges: List[str], hazard_graph: Any) -> Tuple[int, List[str], List[str]]:
        score = 0
        reasons: List[str] = []
        bottleneck_edges: List[str] = []

        if worst_route is None:
            score += self.config.no_path_to_exit
            reasons.append("No path to an available exit was found after blocked evacuation route assumptions were applied.")
            return score, reasons, bottleneck_edges

        if len(self._available_exits(hazard_graph)) <= 1:
            score += self.config.only_one_exit_available
            reasons.append("Only one exit remains available in the hazard-adjusted graph.")

        if normal_route and normal_route["path"] != worst_route["path"]:
            score += self.config.nearest_route_blocked
            reasons.append("The nearest/baseline evacuation route changed because the fire-origin scenario disrupted normal egress.")

        if worst_route["distance"] > self.config.travel_distance_threshold_m:
            score += self.config.travel_distance_above_threshold
            reasons.append(f"Worst-case travel distance exceeds {self.config.travel_distance_threshold_m:.0f} m.")

        if occupancy > self.config.high_occupancy_threshold:
            score += self.config.high_occupancy
            reasons.append("High occupancy increases congestion pressure and evacuation delay.")

        if int(scenario.get("pre_movement_delay_seconds", 0)) > self.config.pre_movement_delay_threshold_s:
            score += self.config.long_pre_movement_delay
            reasons.append("Pre-movement delay is above the configured threshold.")

        path_nodes = set(worst_route.get("path") or [])
        if path_nodes.intersection(smoke_nodes):
            score += self.config.smoke_or_high_risk_route
            reasons.append("Worst-case route passes through smoke-affected or high-risk areas.")

        route_edges = list(zip(worst_route["path"][:-1], worst_route["path"][1:]))
        for u, v in route_edges:
            edge_data = hazard_graph.edges[u, v]
            width = edge_data.get("width_m", 1.0)
            connection_id = edge_data.get("connection_id", f"{u}-{v}")
            if width < self.config.narrow_door_threshold_m:
                bottleneck_edges.append(connection_id)
            if connection_id in high_risk_edges and "high-risk edge" not in reasons:
                score += self.config.smoke_or_high_risk_route
                reasons.append("Worst-case route uses a high-risk edge affected by fire/smoke assumptions.")
        if bottleneck_edges:
            score += self.config.bottleneck_encountered
            reasons.append("Route includes narrow bottleneck door/corridor elements.")

        return score, reasons, bottleneck_edges

    def _overall_risk_score(self, room_results: List[Dict[str, Any]], scenario: Dict[str, Any], available_exit_count: int) -> int:
        if not room_results:
            return 0
        max_room_score = max(r["risk_score"] for r in room_results)
        trapped_bonus = 35 if any(r["trapped"] for r in room_results) else 0
        exit_bonus = self.config.only_one_exit_available if available_exit_count <= 1 else 0
        severity_bonus = 20 if str(scenario.get("fire_severity", "")).lower() == "critical" else 10
        avg_room_score = sum(r["risk_score"] for r in room_results) / len(room_results)
        return int(max(max_room_score, avg_room_score + trapped_bonus + exit_bonus + severity_bonus))

    def _apply_smoke_penalties(self, graph: Any, smoke_nodes: Iterable[str], high_risk_edges: Iterable[str]) -> None:
        for node in smoke_nodes:
            if node not in graph:
                continue
            for neighbour in list(graph.neighbors(node)):
                if graph.has_edge(node, neighbour):
                    graph.edges[node, neighbour]["weight"] = graph.edges[node, neighbour].get("weight", 1.0) + self.config.smoke_node_weight_penalty
                    graph.edges[node, neighbour]["smoke_affected"] = True
        for edge_id in high_risk_edges:
            for u, v, data in graph.edges(data=True):
                if data.get("connection_id") == edge_id:
                    data["weight"] = data.get("weight", 1.0) + self.config.smoke_edge_weight_penalty
                    data["high_risk"] = True

    def _remove_edge_by_id(self, graph: Any, edge_id: str) -> None:
        for u, v, data in list(graph.edges(data=True)):
            if data.get("connection_id") == edge_id and graph.has_edge(u, v):
                graph.remove_edge(u, v)

    def _available_exits(self, graph: Any) -> List[str]:
        return [exit_id for exit_id in self.exit_ids if exit_id in graph]

    def _occupied_room_ids(self) -> List[str]:
        return [s["id"] for s in self.dataset.get("spaces", []) if s.get("type") not in {"exit", "corridor"} and s.get("occupancy", 0) > 0]

    def _node_name(self, node_id: str) -> str:
        return self.space_by_id.get(node_id, {}).get("name", node_id)

    def _nearest_exit(self, origin: str) -> Optional[str]:
        route = self._best_route(self.graph, origin)
        return route["exit"] if route else (self.exit_ids[0] if self.exit_ids else None)

    def _congestion_delay(self, room_id: str, min_width: float) -> float:
        occupancy = self.space_by_id.get(room_id, {}).get("occupancy", 0)
        width_penalty = max(0.0, self.config.narrow_door_threshold_m - min_width) * 30
        occupancy_penalty = max(0, occupancy - 20) * 0.35
        return width_penalty + occupancy_penalty

    def _room_explanation(self, room_id: str, risk_level: str, trapped: bool, rerouted: bool, reasons: List[str], worst_route: Optional[Dict[str, Any]]) -> str:
        room_name = self._node_name(room_id)
        if trapped:
            return f"{room_name} is classified as {risk_level} because no safe path to an available exit was found after applying fire-origin blocked evacuation route assumptions. Expert review is required."
        route_text = " -> ".join(worst_route["path"]) if worst_route else "No route"
        reroute_text = " The room was forced onto an alternative route." if rerouted else ""
        reason_text = " ".join(reasons) if reasons else "No major risk trigger was detected."
        return f"{room_name} is classified as {risk_level}.{reroute_text} Worst-case route: {route_text}. {reason_text}"

    def _ranking_reason(self, result: WorstCaseResult, origin: str) -> str:
        if result.trapped_rooms:
            return f"Fire at {self._node_name(origin)} traps {len(result.trapped_rooms)} rooms and affects {result.affected_occupants} occupants."
        if result.affected_occupants:
            return f"Fire at {self._node_name(origin)} creates smoke-affected route pressure for {result.affected_occupants} occupants."
        return f"Fire at {self._node_name(origin)} leaves evacuation routes mostly available but still requires expert review."

    def generate_explanation(self, scenario: Dict[str, Any], room_results: List[Dict[str, Any]], trapped_rooms: List[str], rerouted_rooms: List[str], affected_occupants: int, overall_risk: str) -> str:
        origin_name = scenario.get("fire_origin_name") or self._node_name(scenario.get("fire_origin", ""))
        smoke = ", ".join(self._node_name(n) for n in scenario.get("smoke_spread_nodes", [])) or "no explicitly smoke-affected rooms"
        blocked_nodes = ", ".join(self._node_name(n) for n in scenario.get("blocked_nodes", [])) or "no extra blocked rooms"
        blocked_edges = ", ".join(scenario.get("blocked_edges", [])) or "no blocked doors/edges"
        affected_exit = scenario.get("affected_exit") or "no single affected exit"
        high_occ_rooms = [r["start_room_name"] for r in room_results if r["occupancy"] > self.config.high_occupancy_threshold]

        text = (
            f"This fire-origin-based worst-case scenario is classified as {overall_risk} because fire starts in {origin_name}. "
            f"Smoke affects {smoke}; blocked elements include {blocked_nodes} and {blocked_edges}; affected exit: {affected_exit}. "
        )
        if trapped_rooms:
            text += f"The analysis detected trapped room(s): {', '.join(self._node_name(r) for r in trapped_rooms)}. "
        if rerouted_rooms:
            text += f"Alternative route availability is required for: {', '.join(self._node_name(r) for r in rerouted_rooms)}. "
        if high_occ_rooms:
            text += f"High occupancy pressure is present in: {', '.join(high_occ_rooms)}. "
        text += (
            f"Indicative affected occupants: {affected_occupants}. Expert review should verify compartmentation, smoke control, exit signage, "
            "door widths, protected routes, travel distances and whether the assumptions match the actual BIM/fire strategy. "
            "This is compliance-oriented screening and an indicative decision-support result only."
        )
        return text


def load_worst_case_dataset(path: Optional[str] = None) -> Dict[str, Any]:
    """Load the bundled worst-case demo dataset."""
    dataset_path = Path(path) if path else DEFAULT_DATASET_PATH
    with dataset_path.open("r", encoding="utf-8") as f:
        dataset = json.load(f)
    validate_scenario_dataset(dataset)
    return dataset


def validate_scenario_dataset(dataset: Dict[str, Any]) -> None:
    """Validate the minimum graph/scenario structure required by the fire engines."""
    if not isinstance(dataset, dict):
        raise ValueError("Dataset must be a JSON object.")

    spaces = dataset.get("spaces")
    connections = dataset.get("connections")
    scenarios = dataset.get("hazard_scenarios")
    if not isinstance(spaces, list) or not spaces:
        raise ValueError("Dataset must contain a non-empty 'spaces' list.")
    if not isinstance(connections, list) or not connections:
        raise ValueError("Dataset must contain a non-empty 'connections' list.")
    if not isinstance(scenarios, list) or not scenarios:
        raise ValueError("Dataset must contain a non-empty 'hazard_scenarios' list.")

    space_ids = {space.get("id") for space in spaces}
    if None in space_ids or len(space_ids) != len(spaces):
        raise ValueError("Every space requires a unique 'id'.")
    if not any(space.get("type") == "exit" for space in spaces):
        raise ValueError("Dataset must contain at least one space with type 'exit'.")

    for connection in connections:
        if not connection.get("id"):
            raise ValueError("Every connection requires an 'id'.")
        if connection.get("from") not in space_ids or connection.get("to") not in space_ids:
            raise ValueError(f"Connection '{connection.get('id')}' references an unknown space.")
    for scenario in scenarios:
        if scenario.get("fire_origin") not in space_ids:
            raise ValueError(f"Scenario '{scenario.get('scenario_id')}' has an unknown fire origin.")


def dataset_summary(dataset: Dict[str, Any]) -> Dict[str, Any]:
    """Return a compact, reader-facing dataset provenance summary."""
    spaces = dataset.get("spaces", [])
    return {
        "building_id": dataset.get("building_id", "Not provided"),
        "building_name": dataset.get("building_name", "Unnamed dataset"),
        "spaces": len(spaces),
        "connections": len(dataset.get("connections", [])),
        "exits": sum(space.get("type") == "exit" for space in spaces),
        "hazard_scenarios": len(dataset.get("hazard_scenarios", [])),
        "total_occupancy": sum(int(space.get("occupancy", 0)) for space in spaces),
    }


def build_graph_from_dataset(dataset: Dict[str, Any]) -> Any:
    """Build a NetworkX graph from the worst-case demo dataset."""
    if nx is None:
        raise RuntimeError("NetworkX is required to build the worst-case graph")
    graph = nx.Graph()
    for space in dataset.get("spaces", []):
        graph.add_node(
            space["id"],
            name=space.get("name", space["id"]),
            node_type=space.get("type", "unknown"),
            occupancy=space.get("occupancy", 0),
            floor=space.get("floor"),
        )
    for connection in dataset.get("connections", []):
        graph.add_edge(
            connection["from"],
            connection["to"],
            weight=float(connection.get("distance_m", 1.0)),
            distance_m=float(connection.get("distance_m", 1.0)),
            width_m=float(connection.get("width_m", 1.0)),
            connection_id=connection.get("id"),
            edge_type=connection.get("type", "connection"),
        )
    return graph


def classify_risk(score: float) -> str:
    if score <= 25:
        return "Low"
    if score <= 50:
        return "Medium"
    if score <= 80:
        return "High"
    return "Critical"


def risk_sort_value(risk: str) -> int:
    return {"Low": 1, "Medium": 2, "High": 3, "Critical": 4}.get(risk, 0)
