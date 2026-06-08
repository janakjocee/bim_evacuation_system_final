"""ASET/RSET-inspired evacuation screening.

This module compares Required Safe Egress Time (RSET) against an estimated
Available Safe Egress Time (ASET) produced by the graph-based smoke spread model.
It is an indicative screening calculation for expert review, not final approval.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

try:
    import networkx as nx
except ImportError:  # pragma: no cover
    nx = None


@dataclass
class AsetRsetConfig:
    detection_time_s: int = 30
    alarm_time_s: int = 15
    pre_movement_delay_s: int = 60
    walking_speed_mps: float = 1.2
    congestion_per_extra_person_s: float = 0.35
    narrow_door_threshold_m: float = 0.8
    narrow_door_delay_factor_s: float = 30.0
    reduced_margin_threshold_s: int = 60


def _available_exits(graph: Any, exits: List[str], affected_exits: Optional[List[str]] = None) -> List[str]:
    affected = set(affected_exits or [])
    return [exit_id for exit_id in exits if exit_id in graph and exit_id not in affected]


def _best_route(graph: Any, origin: str, exits: List[str], walking_speed: float, occupancy: int, cfg: AsetRsetConfig) -> Optional[Dict[str, Any]]:
    if origin not in graph:
        return None
    routes: List[Dict[str, Any]] = []
    for exit_id in exits:
        try:
            path = nx.shortest_path(graph, origin, exit_id, weight="weight")
            distance = float(nx.shortest_path_length(graph, origin, exit_id, weight="weight"))
            route_edges = list(zip(path[:-1], path[1:]))
            min_width = min((float(graph.edges[e].get("width_m", 1.0)) for e in route_edges), default=1.0)
            bottlenecks = [str(graph.edges[e].get("connection_id", f"{e[0]}-{e[1]}")) for e in route_edges if float(graph.edges[e].get("width_m", 1.0)) < cfg.narrow_door_threshold_m]
            congestion_delay = max(0, occupancy - 20) * cfg.congestion_per_extra_person_s
            congestion_delay += max(0.0, cfg.narrow_door_threshold_m - min_width) * cfg.narrow_door_delay_factor_s
            travel_time = distance / max(0.1, walking_speed) + congestion_delay
            routes.append({
                "path": path,
                "exit": exit_id,
                "distance_m": round(distance, 2),
                "travel_time_s": round(travel_time, 1),
                "min_width_m": round(min_width, 2),
                "bottleneck_edges": bottlenecks,
            })
        except Exception:
            continue
    if not routes:
        return None
    return sorted(routes, key=lambda row: (row["travel_time_s"], row["distance_m"]))[0]


def _minimum_aset_for_route(route: Optional[Dict[str, Any]], time_to_untenable: Dict[str, Any], default_aset_s: int) -> Optional[int]:
    if not route:
        return None
    values = []
    for node in route.get("path", []):
        value = time_to_untenable.get(node)
        values.append(default_aset_s if value is None else int(value))
    return min(values) if values else None


def classify_safety_margin(route: Optional[Dict[str, Any]], rset_s: Optional[float], aset_s: Optional[float], cfg: AsetRsetConfig) -> str:
    if route is None:
        return "no route / trapped"
    if aset_s is None or rset_s is None:
        return "requires review"
    margin = aset_s - rset_s
    if margin < 0:
        return "unsafe"
    if margin <= cfg.reduced_margin_threshold_s:
        return "reduced margin"
    return "safe margin"


def calculate_aset_rset(
    normal_graph: Any,
    fire_graph: Any,
    spaces: List[Dict[str, Any]],
    exits: List[str],
    smoke_result: Dict[str, Any],
    config: AsetRsetConfig | Dict[str, Any],
    affected_exits: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Calculate ASET/RSET comparison for each occupied room."""
    if nx is None:
        raise RuntimeError("NetworkX is required for ASET/RSET route analysis")
    if isinstance(config, dict):
        config = AsetRsetConfig(**config)

    time_to_untenable = smoke_result.get("time_to_untenable", {})
    default_aset = max((int(row.get("time_s", 0)) for row in smoke_result.get("hazard_timeline", [])), default=360)
    affected = list(set(affected_exits or []) | set(smoke_result.get("affected_exits", [])))
    safe_exits = _available_exits(fire_graph, exits, affected)

    results: List[Dict[str, Any]] = []
    for space in spaces:
        if space.get("type") in {"exit", "corridor"} or int(space.get("occupancy", 0)) <= 0:
            continue
        room_id = space["id"]
        occupancy = int(space.get("occupancy", 0))
        normal_route = _best_route(normal_graph, room_id, exits, config.walking_speed_mps, occupancy, config)
        fire_route = _best_route(fire_graph, room_id, safe_exits, config.walking_speed_mps, occupancy, config)
        travel_time = fire_route["travel_time_s"] if fire_route else None
        rset = None if travel_time is None else round(config.detection_time_s + config.alarm_time_s + config.pre_movement_delay_s + travel_time, 1)
        aset = _minimum_aset_for_route(fire_route, time_to_untenable, default_aset)
        margin = None if aset is None or rset is None else round(aset - rset, 1)
        classification = classify_safety_margin(fire_route, rset, aset, config)
        results.append({
            "room_id": room_id,
            "room_name": space.get("name", room_id),
            "occupancy": occupancy,
            "normal_route": normal_route.get("path") if normal_route else None,
            "fire_route": fire_route.get("path") if fire_route else None,
            "normal_distance_m": normal_route.get("distance_m") if normal_route else None,
            "fire_distance_m": fire_route.get("distance_m") if fire_route else None,
            "travel_time_s": travel_time,
            "detection_time_s": config.detection_time_s,
            "alarm_time_s": config.alarm_time_s,
            "pre_movement_delay_s": config.pre_movement_delay_s,
            "rset_s": rset,
            "aset_s": aset,
            "safety_margin_s": margin,
            "classification": classification,
            "available_exit": fire_route.get("exit") if fire_route else None,
            "bottleneck_edges": fire_route.get("bottleneck_edges") if fire_route else [],
            "rerouted": bool(normal_route and fire_route and normal_route.get("path") != fire_route.get("path")),
        })
    return results
