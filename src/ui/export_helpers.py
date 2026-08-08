"""Pure helpers for safe uploads and deterministic Streamlit exports."""
from __future__ import annotations

import csv
import io
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Iterable


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
            "compliance_score": scenario.compliance_score,
            "confidence_score": scenario.confidence_score,
            "distance": scenario.evacuation_route.distance,
            "estimated_time": scenario.evacuation_route.estimated_time,
            "violations": len(scenario.violated_regulations),
        })
    return output.getvalue()


def build_scenarios_xml(result, generated_at: str) -> str:
    """Build well-formed XML with user/IFC text escaped by ElementTree."""
    root = ET.Element("FireStrategyReport", {"generated": generated_at})
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
        ET.SubElement(scenario_node, "Compliance", {
            "score": f"{scenario.compliance_score:.3f}",
            "status": scenario.compliance_status.value,
        })
    ET.indent(root, space="    ")
    return ET.tostring(root, encoding="unicode", xml_declaration=True)
