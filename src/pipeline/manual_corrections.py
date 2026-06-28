"""Manual correction support for IFC-derived building data."""
from __future__ import annotations

from typing import Any, Dict, List

from ..bim_processing.feature_extractor import FeatureExtractor
from ..bim_processing.spatial_graph import SpatialGraphBuilder
from ..scenario.scenario_generator import ScenarioGenerator
from .evacuation_pipeline import PipelineResult


def apply_manual_corrections(
    result: PipelineResult,
    corrections: Dict[str, Any],
    max_scenarios: int = 10,
) -> PipelineResult:
    """Apply reviewed door/exit/connectivity corrections and regenerate scenarios."""
    if not result.building:
        return result

    building = result.building
    door_corrections: List[Dict[str, Any]] = corrections.get("doors", [])
    for correction in door_corrections:
        door_id = correction.get("id")
        door = building.doors.get(door_id)
        if not door:
            continue

        if "width" in correction and correction["width"] not in {None, ""}:
            width = float(correction["width"])
            if width > 0:
                door.width = width
                door.width_confidence = 1.0
                door.assumptions.pop("width", None)
                door.assumptions["manual_width_review"] = "Door width manually confirmed or edited by reviewer."
                if "missing_door_width_assumed" in door.data_quality_flags:
                    door.data_quality_flags.remove("missing_door_width_assumed")
                door.data_quality_flags.append("manual_width_override")

        if "is_exit" in correction:
            door.is_exit = bool(correction["is_exit"])
            door.data_quality_flags.append("manual_exit_review")
            if door.is_exit:
                building.exits[door_id] = door
            else:
                building.exits.pop(door_id, None)

        if "connected_spaces" in correction:
            connected_spaces = _normalise_space_list(correction["connected_spaces"], building.spaces)
            for space in building.spaces.values():
                if door_id in space.connected_doors and space.id not in connected_spaces:
                    space.connected_doors.remove(door_id)
            door.connected_spaces = connected_spaces
            for space_id in connected_spaces:
                if door_id not in building.spaces[space_id].connected_doors:
                    building.spaces[space_id].connected_doors.append(door_id)
            door.connection_source = "manual_review"
            door.data_quality_flags.append("manual_connectivity_override")
            door.assumptions["manual_connectivity_review"] = "Door-space connectivity manually confirmed or edited by reviewer."

    building.data_quality_flags.append("manual_corrections_applied")
    features = FeatureExtractor().extract(building)
    graph_builder = SpatialGraphBuilder(building)
    graph_builder.build()
    scenario_generator = ScenarioGenerator(building, graph_builder)
    _restore_active_thresholds(scenario_generator, result.regulation_application)
    scenarios = scenario_generator.generate(max_scenarios=max_scenarios)

    result.features = features
    result.graph_stats = graph_builder.get_graph_stats()
    result.scenarios = scenarios
    result.success = bool(scenarios)
    if not scenarios and "No scenarios generated" not in result.errors:
        result.errors.append("No scenarios generated after manual corrections")
    return result


def _restore_active_thresholds(scenario_generator: ScenarioGenerator, regulation_application: Dict[str, Any]) -> None:
    """Keep uploaded/default active thresholds when scenarios are regenerated."""
    for row in regulation_application.get("active_thresholds", []):
        key = row.get("rule_key")
        value = row.get("value")
        if key and isinstance(value, (int, float)):
            scenario_generator.compliance_checker.regulations[key] = float(value)


def _normalise_space_list(value: Any, spaces: Dict[str, Any]) -> List[str]:
    if isinstance(value, str):
        parts = [item.strip() for item in value.replace(";", ",").split(",")]
    elif isinstance(value, list):
        parts = [str(item).strip() for item in value]
    else:
        parts = []
    return list(dict.fromkeys(part for part in parts if part in spaces))
