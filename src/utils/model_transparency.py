"""Shared model-boundary, score-semantic and assumption metadata."""
from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any, Dict, Iterable, Optional

from .config_loader import get_config


CALIBRATION_STATUS = "unvalidated_research_assumption"
ACADEMIC_USE_NOTICE = (
    "Deterministic research screening only. Outputs do not establish fire safety, "
    "statutory compliance, professional approval or a certified evacuation result."
)


def screening_index_semantics() -> Dict[str, Any]:
    """Describe the standard evacuation screening index without calling it risk."""
    config = get_config()
    return {
        "name": "screening_index",
        "range": [0.0, 1.0],
        "direction": "higher_is_lower_screening_priority",
        "interpretation": (
            "A deterministic prioritisation index. Higher values indicate fewer issues "
            "within the implemented prototype checks, not proven safety."
        ),
        "thresholds": config.get("scenario.risk_thresholds", {}),
        "calibration_status": CALIBRATION_STATUS,
    }


def hazard_priority_score_semantics() -> Dict[str, Any]:
    """Describe fire and worst-case point scores."""
    return {
        "name": "hazard_priority_score",
        "range": "unbounded_non_negative_points",
        "direction": "higher_is_higher_screening_priority",
        "interpretation": (
            "Researcher-defined points used to rank illustrative adverse scenarios. "
            "The score is not a probability, casualty forecast or calibrated engineering risk."
        ),
        "calibration_status": CALIBRATION_STATUS,
    }


def assumption_record(
    assumption_id: str,
    value: Any,
    unit: str,
    purpose: str,
    *,
    source: str = "prototype_configuration",
    editable: bool = False,
) -> Dict[str, Any]:
    """Create one consistently labelled assumption record."""
    return {
        "id": assumption_id,
        "value": value,
        "unit": unit,
        "purpose": purpose,
        "source": source,
        "editable_for_run": editable,
        "calibration_status": CALIBRATION_STATUS,
    }


def standard_assumption_registry() -> Dict[str, Any]:
    """Return assumptions used by standard IFC evacuation screening."""
    config = get_config()
    weights = config.get("scenario.screening_index.weights", {})
    penalties = config.get("scenario.screening_index.penalties", {})
    records = [
        assumption_record(
            "occupancy_density_by_space_type",
            config.get("bim.occupancy_density", {}),
            "persons/m2",
            "Estimate occupancy when project-specific occupant loads are unavailable.",
        ),
        assumption_record(
            "level_walking_speed",
            config.get("bim.travel_speed.level", 1.2),
            "m/s",
            "Estimate route travel time.",
        ),
        assumption_record(
            "exit_flow_rate",
            config.get("regulations.exit_capacity_per_minute", 90),
            "persons/min/m",
            "Create an assumption-based comparative exit-capacity indicator.",
        ),
        assumption_record(
            "screening_time_reference",
            config.get("scenario.screening_index.time_reference_s", 300),
            "s",
            "Normalise the evacuation-time component of the screening index.",
        ),
        assumption_record(
            "screening_index_weights",
            weights,
            "proportion",
            "Weight deterministic screening-index components.",
        ),
        assumption_record(
            "screening_index_penalties",
            penalties,
            "index points",
            "Reduce the screening index when topology or measurements are uncertain.",
        ),
    ]
    return {
        "registry_version": "submission-assumptions-v1",
        "scope": "standard_ifc_evacuation_screening",
        "calibration_status": CALIBRATION_STATUS,
        "records": records,
    }


def runtime_assumption_registry(
    scope: str,
    configs: Iterable[tuple[str, Any]],
    *,
    additional: Optional[Iterable[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Serialize actual per-run dataclass/config values for fire scenario exports."""
    records = []
    for name, config in configs:
        values = asdict(config) if is_dataclass(config) else dict(config)
        records.append(
            assumption_record(
                name,
                values,
                "mixed",
                f"Actual values used by the {name.replace('_', ' ')} component for this run.",
                source="user_or_dataset_with_prototype_fallbacks",
                editable=True,
            )
        )
    records.extend(additional or [])
    return {
        "registry_version": "submission-assumptions-v1",
        "scope": scope,
        "calibration_status": CALIBRATION_STATUS,
        "records": records,
    }
