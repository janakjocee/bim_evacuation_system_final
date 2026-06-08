"""IFC compatibility and readiness validation helpers.

The validator is intentionally defensive: it does not claim that every IFC file is
usable. It reports whether the model appears to contain sufficient spatial and
egress-related information for early-stage evacuation screening.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


REQUIRED_ENTITY_NAMES = [
    "IfcProject",
    "IfcSite",
    "IfcBuilding",
    "IfcBuildingStorey",
    "IfcSpace",
    "IfcDoor",
]

PREFERRED_ENTITY_NAMES = [
    "IfcStair",
    "IfcSlab",
]

TARGET_SCHEMAS = {"IFC2X3", "IFC4", "IFC4X3", "IFC4X3_ADD2"}
SUPPORTED_SCHEMA_LABEL = "IFC2X3, IFC4, IFC4X3 and IFC4X3_ADD2"


def _count_by_type(ifc_model: Any, entity_name: str) -> int:
    try:
        return len(ifc_model.by_type(entity_name))
    except Exception:
        return 0


def _schema_name(ifc_model: Any) -> str:
    try:
        schema = ifc_model.schema
        return str(schema).upper()
    except Exception:
        return "UNKNOWN"


def validate_ifc_model(ifc_model: Any = None, extracted_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Validate IFC model readiness for evacuation/fire scenario screening.

    Args:
        ifc_model: Optional IfcOpenShell model object.
        extracted_data: Optional pre-extracted counts/fields for tests or fallback use.

    Returns:
        Readiness dictionary containing counts, warnings, critical issues and score.
    """
    extracted_data = extracted_data or {}
    schema = extracted_data.get("schema") or (_schema_name(ifc_model) if ifc_model is not None else "UNKNOWN")

    counts = {}
    for name in REQUIRED_ENTITY_NAMES + PREFERRED_ENTITY_NAMES:
        key = name.lower().replace("ifc", "") + "_count"
        counts[key] = int(extracted_data.get(key, _count_by_type(ifc_model, name) if ifc_model is not None else 0))

    possible_exits = int(extracted_data.get("possible_exits_count", extracted_data.get("exit_count", 0)))
    missing_door_widths = int(extracted_data.get("missing_door_widths", 0))
    missing_space_areas = int(extracted_data.get("missing_space_areas", 0))
    missing_storey_placement = int(extracted_data.get("missing_storey_placement", 0))
    missing_exit_identification = bool(extracted_data.get("missing_exit_identification", possible_exits == 0))
    missing_occupancy = int(extracted_data.get("missing_occupancy", 0))
    missing_fire_properties = bool(extracted_data.get("missing_material_fuel_fire_properties", True))
    graph_connected = bool(extracted_data.get("graph_connectivity_complete", False))

    warnings: List[str] = []
    critical_issues: List[str] = []

    if schema not in TARGET_SCHEMAS:
        warnings.append(
            f"IFC schema '{schema}' is not one of the documented targets: {SUPPORTED_SCHEMA_LABEL}."
        )
    if counts["space_count"] == 0:
        critical_issues.append("No IfcSpace entities detected; room-level evacuation screening is not reliable.")
    if counts["door_count"] == 0:
        critical_issues.append("No IfcDoor entities detected; route connectivity and door-width screening may fail.")
    if counts["buildingstorey_count"] == 0:
        warnings.append("No IfcBuildingStorey entities detected; floor/storey placement may need manual input.")
    if possible_exits == 0 or missing_exit_identification:
        warnings.append("Exit identification is missing or uncertain; exits should be manually confirmed.")
    if missing_door_widths:
        warnings.append(f"{missing_door_widths} door widths are missing; conservative fallback widths may be required.")
    if missing_space_areas:
        warnings.append(f"{missing_space_areas} space areas are missing; occupancy estimates may be unreliable.")
    if missing_storey_placement:
        warnings.append(f"{missing_storey_placement} elements have missing storey placement.")
    if missing_occupancy:
        warnings.append(f"{missing_occupancy} rooms have missing occupancy values; estimates or manual input are required.")
    if missing_fire_properties:
        warnings.append("Material/fuel/fire-safety properties are missing or incomplete; fire-growth assumptions are scenario based.")
    if not graph_connected:
        warnings.append("Graph connectivity completeness has not been verified; disconnected spaces may exist.")

    score = 100
    score -= 25 if counts["space_count"] == 0 else 0
    score -= 25 if counts["door_count"] == 0 else 0
    score -= 15 if possible_exits == 0 else 0
    score -= min(20, missing_door_widths * 3)
    score -= min(15, missing_space_areas * 2)
    score -= min(10, missing_occupancy * 2)
    score -= 10 if not graph_connected else 0
    score = max(0, score)

    if score >= 90:
        readiness = "Ready for scenario generation"
    elif score >= 70:
        readiness = "Usable with warnings"
    elif score >= 50:
        readiness = "Limited reliability"
    else:
        readiness = "Not safe for automated scenario generation"

    return {
        "schema": schema,
        "target_compatibility": (
            f"Documented schema targets: {SUPPORTED_SCHEMA_LABEL}. Successful analysis also "
            "depends on usable semantic entities or element geometry."
        ),
        "counts": counts,
        "possible_exits_count": possible_exits,
        "missing_door_widths": missing_door_widths,
        "missing_space_areas": missing_space_areas,
        "missing_storey_placement": missing_storey_placement,
        "missing_exit_identification": missing_exit_identification,
        "missing_occupancy": missing_occupancy,
        "missing_material_fuel_fire_properties": missing_fire_properties,
        "graph_connectivity_complete": graph_connected,
        "model_readiness_score": score,
        "readiness_label": readiness,
        "warnings": warnings,
        "critical_issues": critical_issues,
        "fallback_options": [
            "manual exit assignment",
            "conservative default door widths",
            "estimated occupancy from room type/area",
        ],
    }
