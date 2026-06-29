"""Export IFC-derived evacuation graph data to fire/worst-case dataset JSON."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..bim_processing.feature_extractor import ExtractedFeatures
from ..bim_processing.ifc_parser import BuildingData
from ..bim_processing.spatial_graph import SpatialGraphBuilder


def building_to_worst_case_dataset(
    building: BuildingData,
    graph_builder: Optional[SpatialGraphBuilder] = None,
    features: Optional[ExtractedFeatures] = None,
    source_file_name: str = "",
    ifc_schema: str = "UNKNOWN",
) -> Dict[str, Any]:
    """Convert parsed IFC building data into the worst-case engine dataset schema."""
    spaces = []
    occupancy_by_space = _occupancy_lookup(features)
    for space in building.spaces.values():
        occupancy, occupancy_confidence, occupancy_note = _dataset_occupancy(space, occupancy_by_space)
        spaces.append({
            "id": space.id,
            "name": space.name,
            "type": _dataset_space_type(space.space_type),
            "floor": space.level or "unknown",
            "occupancy": occupancy,
            "area_m2": round(space.area, 2),
            "default_growth_class": _growth_class_for_space(space.space_type),
            "source": "ifc_space" if building.extraction_mode != "geometry_derived" else "ifc_geometry_element",
            "area_confidence": space.area_confidence,
            "occupancy_confidence": occupancy_confidence,
            "data_quality_flags": space.data_quality_flags,
            "assumptions": {**space.assumptions, **({"occupancy": occupancy_note} if occupancy_note else {})},
        })

    for door in building.exits.values():
        exit_id = _exit_node_id(door.id)
        spaces.append({
            "id": exit_id,
            "name": door.name,
            "type": "exit",
            "floor": "unknown",
            "occupancy": 0,
            "area_m2": 0,
            "default_growth_class": "slow",
            "source": "ifc_exit" if not door.connection_source.startswith("inferred") else "inferred_exit",
            "width_confidence": door.width_confidence,
            "data_quality_flags": door.data_quality_flags,
            "assumptions": door.assumptions,
        })

    connections = []
    for door in building.doors.values():
        connected = [space_id for space_id in door.connected_spaces if space_id in building.spaces]
        if door.is_exit:
            for space_id in connected:
                connections.append(_connection_row(
                    connection_id=f"{door.id}__{space_id}__EXIT",
                    source=space_id,
                    target=_exit_node_id(door.id),
                    door=door,
                    distance=_distance_from_graph(graph_builder, space_id, door.id),
                ))
        elif len(connected) >= 2:
            for index, source in enumerate(connected):
                for target in connected[index + 1:]:
                    connections.append(_connection_row(
                        connection_id=f"{door.id}__{source}__{target}",
                        source=source,
                        target=target,
                        door=door,
                        distance=_distance_from_graph(graph_builder, source, door.id)
                        + _distance_from_graph(graph_builder, target, door.id),
                    ))

    if not connections and graph_builder and graph_builder.graph:
        for source, target, data in graph_builder.graph.edges(data=True):
            if source in building.spaces and target in building.spaces:
                connections.append({
                    "id": f"GRAPH_{source}_{target}",
                    "from": source,
                    "to": target,
                    "type": data.get("edge_type", "graph_connection"),
                    "width_m": 0.9,
                    "distance_m": round(float(data.get("weight", 1.0)), 2),
                    "door_state": "unknown",
                    "source": "graph_edge",
                    "inferred": bool(data.get("inferred")),
                    "confidence": 0.4 if data.get("inferred") else 0.8,
                })

    hazard_scenarios = _hazard_scenarios(spaces, connections)
    dataset = {
        "building_id": building.id,
        "building_name": building.name,
        "dataset_kind": "ifc_derived_requires_review",
        "provenance": {
            "source_file_name": source_file_name,
            "ifc_schema": ifc_schema,
            "extraction_mode": building.extraction_mode,
            "geometry_source_types": building.geometry_source_types,
            "warning": (
                "Dataset was converted from IFC-derived graph data. Inferred topology, "
                "assumed widths or inferred exits require expert review before use."
            ),
        },
        "version": "ifc-derived-v1",
        "description": "IFC-derived graph export for Fire/Worst Case Testing pages.",
        "storeys": [{"id": value, "name": value} for value in sorted({s["floor"] for s in spaces if s.get("floor")})],
        "spaces": spaces,
        "connections": connections,
        "hazard_scenarios": hazard_scenarios,
        "fire_model_defaults": {
            "walking_speed_mps": 1.2,
            "travel_distance_threshold_m": 45.0,
            "narrow_door_threshold_m": 0.8,
        },
    }
    return dataset


def _occupancy_lookup(features: Optional[ExtractedFeatures]) -> Dict[str, int]:
    if not features:
        return {}
    return {row["id"]: int(row.get("occupancy", 0)) for row in features.space_features}


def _dataset_occupancy(space: Any, occupancy_by_space: Dict[str, int]) -> tuple[int, float, str]:
    occupancy = int(occupancy_by_space.get(space.id, 0))
    if occupancy > 0:
        return occupancy, 0.75 if space.area_confidence < 1 else 0.9, ""
    if space.space_type in {"structural_proxy", "structural_element", "unknown"} and space.area > 0:
        estimated = max(1, int(space.area * 0.05))
        return (
            estimated,
            0.25,
            "Low-confidence review occupancy estimated for IFC-derived fire/worst-case screening because no usable occupancy was available.",
        )
    return 0, 0.4, "No occupancy data was available; expert review required."


def _dataset_space_type(space_type: str) -> str:
    if space_type in {"corridor", "lobby"}:
        return "corridor"
    if space_type in {"stair"}:
        return "stair"
    if space_type in {"structural_proxy", "structural_element"}:
        return "unknown"
    if space_type in {"toilet"}:
        return "service"
    return space_type or "room"


def _growth_class_for_space(space_type: str) -> str:
    if space_type in {"kitchen", "service", "structural_proxy", "structural_element"}:
        return "fast"
    if space_type in {"corridor", "lobby", "stair"}:
        return "slow"
    return "medium"


def _exit_node_id(door_id: str) -> str:
    return f"EXIT_{door_id}"


def _connection_row(connection_id: str, source: str, target: str, door: Any, distance: float) -> Dict[str, Any]:
    inferred = door.connection_source.startswith("inferred")
    return {
        "id": connection_id,
        "from": source,
        "to": target,
        "type": "exit" if door.is_exit else "door",
        "width_m": round(float(door.width), 2),
        "distance_m": round(max(float(distance), 0.1), 2),
        "door_state": "mixed",
        "source": door.connection_source,
        "inferred": inferred,
        "confidence": round(min(door.width_confidence, 0.45 if inferred else 1.0), 2),
        "data_quality_flags": door.data_quality_flags,
        "assumptions": door.assumptions,
    }


def _distance_from_graph(graph_builder: Optional[SpatialGraphBuilder], source: str, target: str) -> float:
    if graph_builder and graph_builder.graph and graph_builder.graph.has_edge(source, target):
        return float(graph_builder.graph.edges[source, target].get("weight", 1.0))
    return 1.0


def _hazard_scenarios(spaces: List[Dict[str, Any]], connections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    occupied = [space for space in spaces if space.get("type") != "exit" and int(space.get("occupancy", 0)) > 0]
    if not occupied:
        occupied = [space for space in spaces if space.get("type") != "exit"][:3]
    scenarios = []
    for index, space in enumerate(occupied[:5], 1):
        related_connections = [
            connection["id"] for connection in connections
            if connection.get("from") == space["id"] or connection.get("to") == space["id"]
        ]
        scenarios.append({
            "scenario_id": f"IFC_WC{index:02d}",
            "scenario_name": f"IFC-derived fire origin at {space['name']}",
            "fire_origin": space["id"],
            "fire_origin_name": space["name"],
            "fire_severity": "high",
            "room_type": space.get("type", "unknown"),
            "growth_class": space.get("default_growth_class", "medium"),
            "detection_time": 45,
            "alarm_time": 15,
            "pre_movement_delay": 60,
            "pre_movement_delay_seconds": 60,
            "ventilation_factor": 1.0,
            "smoke_spread_speed": 1.0,
            "suppression_enabled": False,
            "sprinkler_activation_time_seconds": 180,
            "smoke_spread_nodes": [],
            "blocked_nodes": [space["id"]],
            "blocked_edges": related_connections[:1],
            "high_risk_edges": related_connections[1:3],
            "affected_exit": None,
            "occupancy_multiplier": 1.0,
            "expected_risk": "High",
            "expected_outcome_category": "ifc-derived_requires_review",
        })
    return scenarios
