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
    analysis_space_count = int(extracted_data.get("analysis_space_count", counts["space_count"]))
    analysis_door_count = int(extracted_data.get("analysis_door_count", counts["door_count"]))
    analysis_mode = str(extracted_data.get("analysis_mode", "semantic_ifc"))
    verified_edge_count = int(extracted_data.get("verified_edge_count", 0))
    inferred_edge_count = int(extracted_data.get("inferred_edge_count", 0))
    inferred_exit_count = int(extracted_data.get("inferred_exit_count", 0))
    missing_door_widths = int(extracted_data.get("missing_door_widths", 0))
    missing_space_areas = int(extracted_data.get("missing_space_areas", 0))
    missing_storey_placement = int(extracted_data.get("missing_storey_placement", 0))
    missing_exit_identification = bool(extracted_data.get("missing_exit_identification", possible_exits == 0))
    missing_occupancy = int(extracted_data.get("missing_occupancy", 0))
    missing_fire_properties = bool(extracted_data.get("missing_material_fuel_fire_properties", True))
    graph_connected = bool(extracted_data.get("graph_connectivity_complete", False))
    graph_confidence = float(extracted_data.get("graph_confidence_score", 1.0 if graph_connected else 0.0))

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

    if analysis_mode == "geometry_derived":
        warnings.append(
            "Geometry-derived nodes are IFC elements, not verified rooms; inferred connectors and egress points "
            "support exploratory visualization only."
        )
    elif analysis_mode == "semantic_spaces_inferred_topology":
        warnings.append(
            "Room geometry comes from IfcSpace entities, but route links or egress points are inferred."
        )
    if inferred_exit_count:
        warnings.append(f"{inferred_exit_count} egress point(s) are inferred and require manual confirmation.")

    processing_score = 100
    processing_score -= 40 if analysis_space_count == 0 else 0
    processing_score -= 25 if analysis_door_count == 0 else 0
    processing_score -= 20 if possible_exits == 0 else 0
    processing_score -= 15 if not graph_connected else 0
    processing_score = max(0, processing_score)

    score = 100
    score -= 20 if counts["space_count"] == 0 else 0
    score -= 20 if counts["door_count"] == 0 else 0
    score -= 15 if possible_exits == 0 else 0
    score -= 15 if possible_exits and inferred_exit_count >= possible_exits else 0
    score -= min(15, missing_door_widths * 3)
    score -= min(15, missing_space_areas * 2)
    score -= min(10, missing_occupancy * 2)
    score -= 10 if not graph_connected else 0
    if analysis_mode == "geometry_derived":
        score -= 15
    elif analysis_mode == "semantic_spaces_inferred_topology":
        score -= 10
    total_edges = verified_edge_count + inferred_edge_count
    if total_edges:
        score -= round(10 * inferred_edge_count / total_edges)
        score -= round(10 * max(0.0, 1.0 - min(1.0, graph_confidence)))
    score = max(0, score)

    if analysis_mode == "geometry_derived":
        readiness = "Geometry-derived exploratory screening only"
        analysis_scope = "ifc_element_geometry_screening"
    elif analysis_mode == "semantic_spaces_inferred_topology":
        readiness = "Semantic spaces with inferred routing; expert verification required"
        analysis_scope = "room_screening_with_inferred_routes"
    elif score >= 90:
        readiness = "Ready for scenario generation"
        analysis_scope = "semantic_evacuation_screening"
    elif score >= 70:
        readiness = "Usable with warnings"
        analysis_scope = "semantic_evacuation_screening"
    elif score >= 50:
        readiness = "Limited reliability"
        analysis_scope = "limited_evacuation_screening"
    else:
        readiness = "Not safe for automated scenario generation"
        analysis_scope = "insufficient_for_automated_evacuation_analysis"

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
        "analysis_mode": analysis_mode,
        "analysis_scope": analysis_scope,
        "analysis_space_count": analysis_space_count,
        "analysis_door_count": analysis_door_count,
        "verified_edge_count": verified_edge_count,
        "inferred_edge_count": inferred_edge_count,
        "inferred_exit_count": inferred_exit_count,
        "graph_confidence_score": round(graph_confidence, 2),
        "processing_readiness_score": processing_score,
        "engineering_evidence_score": score,
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
