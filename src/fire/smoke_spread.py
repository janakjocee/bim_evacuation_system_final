"""Graph-based smoke spread approximation.

This module approximates smoke spread over a BIM-derived connectivity graph. It
uses graph distance, HRR intensity, door assumptions and ventilation factors to
estimate affected, high-risk and untenable nodes over time. It is intentionally
simple and explainable; it is not CFD.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Set

try:
    import networkx as nx
except ImportError:  # pragma: no cover
    nx = None


@dataclass
class SmokeSpreadConfig:
    fire_origin: str
    door_state_assumption: str = "mixed"  # open, closed, mixed
    ventilation_factor: float = 1.0
    smoke_spread_speed_factor: float = 1.0
    fire_rated_separation: bool = False
    blocked_nodes: Optional[List[str]] = None
    blocked_edges: Optional[List[str]] = None
    exits: Optional[List[str]] = None


def _door_factor(assumption: str) -> float:
    assumption = (assumption or "mixed").lower()
    if assumption == "open":
        return 1.25
    if assumption == "closed":
        return 0.55
    return 0.85


def _hrr_factor(hrr_kw: float) -> float:
    if hrr_kw >= 2500:
        return 1.8
    if hrr_kw >= 1000:
        return 1.4
    if hrr_kw >= 250:
        return 1.0
    return 0.65


def _edge_id(data: Dict[str, Any]) -> str:
    return str(data.get("connection_id") or data.get("id") or "")


def simulate_smoke_spread(graph: Any, fire_growth_result: Dict[str, Any], config: SmokeSpreadConfig | Dict[str, Any]) -> Dict[str, Any]:
    """Simulate graph-based smoke spread and node time-to-untenable values."""
    if nx is None:
        raise RuntimeError("NetworkX is required for smoke spread modelling")
    if isinstance(config, dict):
        config = SmokeSpreadConfig(**config)
    if config.fire_origin not in graph:
        raise ValueError(f"Fire origin {config.fire_origin} is not present in the building graph")

    blocked_nodes: Set[str] = set(config.blocked_nodes or [])
    blocked_edges: Set[str] = set(config.blocked_edges or [])
    exits: Set[str] = set(config.exits or [])
    door_factor = _door_factor(config.door_state_assumption)
    ventilation_factor = max(0.1, float(config.ventilation_factor))
    spread_factor = max(0.1, float(config.smoke_spread_speed_factor))
    separation_factor = 0.65 if config.fire_rated_separation else 1.0

    working_graph = graph.copy()
    for u, v, data in list(working_graph.edges(data=True)):
        if _edge_id(data) in blocked_edges and working_graph.has_edge(u, v):
            working_graph.remove_edge(u, v)
    for node in blocked_nodes:
        if node in working_graph and node != config.fire_origin:
            working_graph.remove_node(node)

    lengths = nx.single_source_shortest_path_length(working_graph, config.fire_origin) if config.fire_origin in working_graph else {}
    time_to_untenable: Dict[str, Optional[int]] = {node: None for node in graph.nodes}
    timeline: List[Dict[str, Any]] = []

    for point in fire_growth_result.get("time_series", []):
        time_s = int(point.get("time_s", 0))
        hrr_kw = float(point.get("hrr_kw", 0.0))
        reach = (_hrr_factor(hrr_kw) * door_factor * ventilation_factor * spread_factor * separation_factor) * max(1, time_s / 60)
        smoke_nodes = {node for node, dist in lengths.items() if dist <= reach and node != config.fire_origin}
        high_risk_nodes = {node for node, dist in lengths.items() if dist <= max(0.0, reach - 0.75)} | {config.fire_origin}
        untenable_nodes = {node for node, dist in lengths.items() if dist <= max(0.0, reach - 1.5)} | {config.fire_origin}

        if time_s == 0:
            smoke_nodes = set()
            high_risk_nodes = {config.fire_origin}
            untenable_nodes = {config.fire_origin}

        for node in untenable_nodes:
            if time_to_untenable.get(node) is None:
                time_to_untenable[node] = time_s

        affected_edges = []
        for u, v, data in graph.edges(data=True):
            if u in smoke_nodes or v in smoke_nodes or u in high_risk_nodes or v in high_risk_nodes:
                affected_edges.append(_edge_id(data) or f"{u}-{v}")

        affected_exits = sorted(exits.intersection(smoke_nodes | high_risk_nodes | untenable_nodes))
        timeline.append({
            "time_s": time_s,
            "hrr_kw": round(hrr_kw, 3),
            "smoke_affected_nodes": sorted(smoke_nodes),
            "high_risk_nodes": sorted(high_risk_nodes),
            "untenable_nodes": sorted(untenable_nodes),
            "smoke_affected_edges": sorted(set(affected_edges)),
            "affected_exits": affected_exits,
        })

    return {
        "fire_origin": config.fire_origin,
        "door_state_assumption": config.door_state_assumption,
        "ventilation_factor": ventilation_factor,
        "smoke_spread_speed_factor": spread_factor,
        "time_to_untenable": time_to_untenable,
        "hazard_timeline": timeline,
        "final_smoke_affected_nodes": timeline[-1]["smoke_affected_nodes"] if timeline else [],
        "final_high_risk_nodes": timeline[-1]["high_risk_nodes"] if timeline else [],
        "final_untenable_nodes": timeline[-1]["untenable_nodes"] if timeline else [],
        "affected_exits": sorted({exit_id for row in timeline for exit_id in row.get("affected_exits", [])}),
        "explanation": "Smoke spread is approximated over the BIM-derived connectivity graph using HRR, graph distance, door-state and ventilation assumptions. This is not CFD.",
    }
