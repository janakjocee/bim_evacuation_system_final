"""Pure helpers for safe uploads and deterministic Streamlit exports."""
from __future__ import annotations

import csv
import io
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Iterable

from src.utils.model_transparency import ACADEMIC_USE_NOTICE, screening_index_semantics


def safe_uploaded_filename(name: str, fallback: str = "upload") -> str:
    """Return a basename safe for local temporary storage and downloads."""
    basename = Path(str(name).replace("\\", "/")).name.replace("\x00", "").strip()
    cleaned = re.sub(r"[^A-Za-z0-9._ -]+", "_", basename).strip(" .")
    return cleaned or fallback


def build_scenarios_csv(scenarios: Iterable) -> str:
    """Build the reviewer-facing scenario summary CSV."""
    output = io.StringIO()
    fieldnames = [
        "scenario_id",
        "name",
        "risk_level",
        "screening_priority",
        "screening_index",
        "score_direction",
        "implemented_checks_passed",
        "evidence_confidence",
        "compliance_score",
        "confidence_score",
        "distance",
        "estimated_time",
        "violations",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for scenario in scenarios:
        writer.writerow({
            "scenario_id": scenario.scenario_id,
            "name": scenario.name,
            "risk_level": scenario.risk_level.value,
            "screening_priority": scenario.risk_level.value,
            "screening_index": scenario.screening_index,
            "score_direction": "higher_is_lower_screening_priority",
            "implemented_checks_passed": scenario.compliance_score,
            "evidence_confidence": scenario.confidence_score,
            "compliance_score": scenario.compliance_score,
            "confidence_score": scenario.confidence_score,
            "distance": scenario.evacuation_route.distance,
            "estimated_time": scenario.evacuation_route.estimated_time,
            "violations": len(scenario.violated_regulations),
        })
    return output.getvalue()


def build_scenarios_xml(result, generated_at: str) -> str:
    """Build well-formed XML with user/IFC text escaped by ElementTree."""
    root = ET.Element("FireStrategyScreeningSummary", {
        "generated": generated_at,
        "schemaVersion": "submission-summary-v2",
    })
    ET.SubElement(root, "AcademicUseNotice").text = ACADEMIC_USE_NOTICE
    semantics = screening_index_semantics()
    ET.SubElement(root, "ScoreSemantics", {
        "name": semantics["name"],
        "direction": semantics["direction"],
        "calibrationStatus": semantics["calibration_status"],
    }).text = semantics["interpretation"]
    ET.SubElement(
        root,
        "Building",
        {"name": result.building.name if result.building else "Unknown"},
    )
    scenarios_node = ET.SubElement(root, "Scenarios", {"count": str(len(result.scenarios))})
    for scenario in result.scenarios:
        scenario_node = ET.SubElement(
            scenarios_node,
            "Scenario",
            {"id": scenario.scenario_id, "risk": scenario.risk_level.value},
        )
        ET.SubElement(scenario_node, "Name").text = scenario.name
        ET.SubElement(scenario_node, "Route", {
            "distance": f"{scenario.evacuation_route.distance:.2f}",
            "time": f"{scenario.evacuation_route.estimated_time:.1f}",
        })
        ET.SubElement(scenario_node, "ImplementedChecks", {
            "score": f"{scenario.compliance_score:.3f}",
            "status": scenario.compliance_status.value,
            "meaning": "prototype-check outcome, not statutory compliance",
        })
        ET.SubElement(scenario_node, "ScreeningIndex", {
            "value": f"{scenario.screening_index:.3f}",
            "direction": "higher_is_lower_screening_priority",
        })
    ET.indent(root, space="    ")
    return ET.tostring(root, encoding="unicode", xml_declaration=True)
