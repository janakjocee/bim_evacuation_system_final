"""Quantitative checks for the project-generated controlled IFC fixture."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple

from src.pipeline.evacuation_pipeline import EvacuationPipeline
from src.utils.helpers import sha256_file


def _pair_set(values: Iterable[Iterable[str]]) -> set[Tuple[str, str]]:
    return {tuple(value) for value in values}


def _ratio(matches: int, expected: int) -> float:
    return 1.0 if expected == 0 else matches / expected


def evaluate_controlled_ifc(ifc_path: Path, truth_path: Path) -> Dict[str, Any]:
    """Evaluate parsed output against the declared controlled ground truth."""
    ifc_path = Path(ifc_path)
    truth = json.loads(Path(truth_path).read_text(encoding="utf-8"))
    expected = truth["expected"]

    pipeline = EvacuationPipeline()
    result = pipeline.run(str(ifc_path), max_scenarios=100, enable_rag=False)
    if not result.success or not result.building or not pipeline.graph_builder:
        return {
            "fixture_id": truth["fixture_id"],
            "passed": False,
            "errors": result.errors,
            "source_sha256": sha256_file(ifc_path),
        }

    building = result.building
    graph_stats = pipeline.graph_builder.get_graph_stats()
    compatibility_status = (
        "pass"
        if building.extraction_mode == "semantic_ifc"
        and graph_stats.get("graph_confidence_score", 0) >= 0.8
        else "partial"
    )
    spaces = {space.name: space for space in building.spaces.values()}
    doors = {door.name: door for door in building.doors.values()}

    expected_space_names = {item["name"] for item in expected["spaces"]}
    expected_door_names = {item["name"] for item in expected["doors"]}
    actual_connections = {
        (building.spaces[space_id].name, door.name)
        for door in building.doors.values()
        for space_id in door.connected_spaces
        if space_id in building.spaces
    }
    expected_connections = _pair_set(expected["connections"])

    area_errors = {
        item["name"]: abs(spaces[item["name"]].area - item["area_m2"])
        for item in expected["spaces"]
        if item["name"] in spaces
    }
    width_errors = {
        item["name"]: abs(doors[item["name"]].width - item["width_m"])
        for item in expected["doors"]
        if item["name"] in doors
    }
    type_matches = sum(
        spaces[item["name"]].space_type == item["space_type"]
        for item in expected["spaces"]
        if item["name"] in spaces
    )
    exit_matches = sum(
        doors[item["name"]].is_exit == item["is_exit"]
        for item in expected["doors"]
        if item["name"] in doors
    )
    reachable = {
        space.name
        for space in building.spaces.values()
        if pipeline.graph_builder.find_paths_to_exits(space.id)
    }

    checks = {
        "schema": result.ifc_schema == expected["schema"],
        "building_name": building.name == expected["building_name"],
        "extraction_mode": building.extraction_mode == expected["extraction_mode"],
        "space_entities": set(spaces) == expected_space_names,
        "door_entities": set(doors) == expected_door_names,
        "space_areas": len(area_errors) == len(expected["spaces"]) and max(area_errors.values(), default=0) < 1e-6,
        "door_widths": len(width_errors) == len(expected["doors"]) and max(width_errors.values(), default=0) < 1e-6,
        "space_types": type_matches == len(expected["spaces"]),
        "exit_classification": exit_matches == len(expected["doors"]),
        "connections": actual_connections == expected_connections,
        "reachable_spaces": reachable == set(expected["reachable_spaces"]),
        "verified_edges": graph_stats.get("verified_edges_count") == expected["verified_edge_count"],
        "inferred_edges": graph_stats.get("inferred_edges_count") == expected["inferred_edge_count"],
        "scenario_count": len(result.scenarios) == expected["scenario_count"],
        "compatibility_status": compatibility_status == expected["compatibility_status"],
    }

    connection_intersection = actual_connections & expected_connections
    metrics = {
        "space_entity_recall": _ratio(len(set(spaces) & expected_space_names), len(expected_space_names)),
        "door_entity_recall": _ratio(len(set(doors) & expected_door_names), len(expected_door_names)),
        "space_type_accuracy": _ratio(type_matches, len(expected["spaces"])),
        "max_area_absolute_error_m2": max(area_errors.values(), default=0.0),
        "max_width_absolute_error_m": max(width_errors.values(), default=0.0),
        "connection_precision": _ratio(len(connection_intersection), len(actual_connections)),
        "connection_recall": _ratio(len(connection_intersection), len(expected_connections)),
        "exit_classification_accuracy": _ratio(exit_matches, len(expected["doors"])),
        "route_reachability_recall": _ratio(
            len(reachable & set(expected["reachable_spaces"])),
            len(expected["reachable_spaces"]),
        ),
    }
    return {
        "fixture_id": truth["fixture_id"],
        "source_sha256": sha256_file(ifc_path),
        "ground_truth_scope": truth["purpose"],
        "independent_ground_truth": truth["independent_ground_truth"],
        "passed": all(checks.values()),
        "checks": checks,
        "metrics": metrics,
        "observed": {
            "schema": result.ifc_schema,
            "building_name": building.name,
            "extraction_mode": building.extraction_mode,
            "spaces": len(building.spaces),
            "doors": len(building.doors),
            "exits": len(building.exits),
            "connections": len(actual_connections),
            "scenarios": len(result.scenarios),
            "compatibility_status": compatibility_status,
        },
    }
