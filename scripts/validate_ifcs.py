"""Run a concise compatibility and scenario-generation audit for IFC files."""
from __future__ import annotations

import argparse
import contextlib
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.pipeline.evacuation_pipeline import EvacuationPipeline
from src.pipeline.evacuation_pipeline import _looks_like_git_lfs_pointer
from src.nlp.document_loader import extract_regulation_text

try:
    import ifcopenshell
except ImportError:
    ifcopenshell = None


LOG_FORMAT = "{time:YYYY-MM-DD HH:mm:ss} | {level} | {name} | {message}"


def route_loguru_to_stderr_for_json() -> None:
    """Keep --json stdout machine-readable even when app modules log verbosely."""
    try:
        from loguru import logger as loguru_logger
    except Exception:
        return
    loguru_logger.remove()
    loguru_logger.add(sys.stderr, format=LOG_FORMAT, level="INFO", colorize=False)
    log_dir = Path("./outputs")
    log_dir.mkdir(parents=True, exist_ok=True)
    loguru_logger.add(
        log_dir / "bim_evacuation.log",
        format=LOG_FORMAT,
        level="DEBUG",
        rotation="10 MB",
        retention="7 days",
    )


def discover_ifcs(inputs: list[str]) -> list[Path]:
    files: list[Path] = []
    for value in inputs:
        path = Path(value).expanduser()
        if path.is_dir():
            files.extend(sorted(
                candidate
                for candidate in path.rglob("*")
                if candidate.is_file() and candidate.suffix.lower() in {".ifc", ".ifczip"}
            ))
        elif path.is_file() and path.suffix.lower() in {".ifc", ".ifczip"}:
            files.append(path)
    return list(dict.fromkeys(path.resolve() for path in files))


def _ifc_entity_counts(path: Path) -> dict:
    counts = {
        "ifcopenshell_open": False,
        "raw_schema": "UNKNOWN",
        "raw_ifcspace_count": 0,
        "raw_ifcdoor_count": 0,
        "raw_ifcstair_count": 0,
        "raw_ifcbuildingstorey_count": 0,
        "raw_ifcslab_count": 0,
        "raw_ifcwall_count": 0,
        "raw_ifcbuildingelementproxy_count": 0,
        "raw_ifcopeningelement_count": 0,
        "raw_ifcrelspaceboundary_count": 0,
    }
    if ifcopenshell is None or _looks_like_git_lfs_pointer(path):
        return counts
    try:
        model = ifcopenshell.open(str(path))
        counts["ifcopenshell_open"] = True
        counts["raw_schema"] = getattr(model, "schema", "UNKNOWN")
        for ifc_type, key in [
            ("IfcSpace", "raw_ifcspace_count"),
            ("IfcDoor", "raw_ifcdoor_count"),
            ("IfcStair", "raw_ifcstair_count"),
            ("IfcBuildingStorey", "raw_ifcbuildingstorey_count"),
            ("IfcSlab", "raw_ifcslab_count"),
            ("IfcWall", "raw_ifcwall_count"),
            ("IfcBuildingElementProxy", "raw_ifcbuildingelementproxy_count"),
            ("IfcOpeningElement", "raw_ifcopeningelement_count"),
            ("IfcRelSpaceBoundary", "raw_ifcrelspaceboundary_count"),
        ]:
            counts[key] = len(model.by_type(ifc_type))
    except Exception as exc:
        counts["open_error"] = str(exc)
    return counts


def _reliability(result, graph: dict) -> str:
    if not result.success:
        return "fail"
    if result.source_mode == "semantic_ifc" and graph.get("graph_confidence_score", 0) >= 0.8:
        return "reliable"
    if result.source_mode in {"semantic_spaces_inferred_topology", "geometry_derived"}:
        return "inferred_requires_review"
    return "partial_requires_review"


def _status(result, graph: dict) -> str:
    """Classify practical compatibility as pass, partial, or fail."""
    if not result.success:
        return "fail"
    if _reliability(result, graph) == "reliable":
        return "pass"
    return "partial"


def _failure_reason(result, building, graph: dict) -> str:
    """Return the primary practical reason for fail/partial status."""
    if not result.success:
        return "; ".join(result.errors) or "Pipeline did not generate scenarios."
    reasons = []
    if result.source_mode == "geometry_derived":
        reasons.append("No semantic IfcSpace/IfcDoor topology; geometry-derived screening only.")
    elif result.source_mode == "semantic_spaces_inferred_topology":
        reasons.append("IfcSpace data exists, but route topology/exits are inferred.")
    if building:
        if not building.exits:
            reasons.append("No exits detected.")
        assumed_doors = sum(1 for door in building.doors.values() if door.assumptions.get("width"))
        assumed_areas = sum(1 for space in building.spaces.values() if space.assumptions.get("area"))
        if assumed_doors:
            reasons.append(f"{assumed_doors} door width(s) assumed.")
        if assumed_areas:
            reasons.append(f"{assumed_areas} space area(s) assumed.")
    if graph.get("spaces_without_exit_route"):
        reasons.append(f"{len(graph['spaces_without_exit_route'])} space(s) lack an exit route.")
    if graph.get("disconnected_spaces"):
        reasons.append(f"{len(graph['disconnected_spaces'])} disconnected space(s).")
    if not reasons and _status(result, graph) == "pass":
        return ""
    if reasons:
        return "; ".join(reason.rstrip(".") for reason in reasons) + "."
    return "Usable with review warnings."


def _scenario_summary(result) -> dict:
    if not result.scenarios:
        return {
            "max_confidence": 0.0,
            "min_confidence": 0.0,
            "risk_levels": [],
            "risk_counts": {"high": 0, "medium": 0, "low": 0},
            "compliance_statuses": [],
            "route_reliabilities": [],
        }
    scenario_dicts = [scenario.to_dict() for scenario in result.scenarios]
    risk_counts = {"high": 0, "medium": 0, "low": 0}
    for scenario in result.scenarios:
        risk_counts[scenario.risk_level.value] = risk_counts.get(scenario.risk_level.value, 0) + 1
    return {
        "max_confidence": round(max(scenario.confidence_score for scenario in result.scenarios), 2),
        "min_confidence": round(min(scenario.confidence_score for scenario in result.scenarios), 2),
        "risk_levels": sorted({item.get("risk_level", "") for item in scenario_dicts if item.get("risk_level")}),
        "risk_counts": risk_counts,
        "compliance_statuses": sorted({item.get("compliance_status", "") for item in scenario_dicts if item.get("compliance_status")}),
        "route_reliabilities": sorted({
            item.get("evacuation_route", {}).get("route_reliability", "")
            for item in scenario_dicts
            if item.get("evacuation_route", {}).get("route_reliability")
        }),
    }


def audit_file(path: Path, max_scenarios: int, regulation_text: str | None = None) -> dict:
    pipeline = EvacuationPipeline()
    raw_counts = _ifc_entity_counts(path)
    result = pipeline.run(str(path), regulation_text=regulation_text, max_scenarios=max_scenarios)
    graph = pipeline.graph_builder.get_graph_stats() if pipeline.graph_builder else {}
    building = result.building
    scenario_summary = _scenario_summary(result)
    door_widths_found = 0
    door_widths_assumed = 0
    space_areas_found = 0
    space_areas_assumed = 0
    inferred_connections = 0
    inferred_exits = 0
    doors_without_connected_spaces = []
    if building:
        door_widths_found = sum(1 for door in building.doors.values() if not door.assumptions.get("width"))
        door_widths_assumed = sum(1 for door in building.doors.values() if door.assumptions.get("width"))
        space_areas_found = sum(1 for space in building.spaces.values() if not space.assumptions.get("area"))
        space_areas_assumed = sum(1 for space in building.spaces.values() if space.assumptions.get("area"))
        inferred_connections = sum(
            1
            for door in building.doors.values()
            for space_id in door.connected_spaces
            if str(door.connection_sources.get(space_id, door.connection_source)).startswith("inferred")
        )
        inferred_exits = sum(
            1
            for door in building.exits.values()
            if str(door.connection_source).startswith("inferred")
            or "exit_detection" in door.assumptions
            or "topology" in door.assumptions
        )
        doors_without_connected_spaces = sorted(
            door_id for door_id, door in building.doors.items() if not door.connected_spaces
        )
    row = {
        "file": path.name,
        "path": str(path),
        "file_size_bytes": path.stat().st_size,
        "source_file_sha256": result.source_file_sha256,
        "is_git_lfs_pointer": _looks_like_git_lfs_pointer(path),
        "schema": result.ifc_schema,
        "raw_schema": raw_counts.get("raw_schema", "UNKNOWN"),
        "success": result.success,
        "mode": result.source_mode,
        "geometry_source_types": building.geometry_source_types if building else [],
        "geometry_elements_available": building.geometry_elements_available if building else 0,
        "geometry_elements_used": building.geometry_elements_used if building else 0,
        "compatibility_status": _status(result, graph),
        "failure_reason": _failure_reason(result, building, graph),
        "building": building.name if building else None,
        "screened_elements_or_spaces": len(building.spaces) if building else 0,
        "extracted_spaces": len(building.spaces) if building else 0,
        "extracted_doors": len(building.doors) if building else 0,
        "extracted_stairs": len(building.stairs) if building else 0,
        "detected_exits": len(building.exits) if building else 0,
        "door_widths_found": door_widths_found,
        "door_widths_assumed": door_widths_assumed,
        "space_areas_found": space_areas_found,
        "space_areas_assumed": space_areas_assumed,
        "door_space_connections": sum(len(door.connected_spaces) for door in building.doors.values()) if building else 0,
        "inferred_connections": inferred_connections,
        "inferred_exits": inferred_exits,
        "doors_without_connected_spaces": doors_without_connected_spaces,
        "candidate_geometry_elements": building.geometry_elements_available if building else 0,
        "scenarios": len(result.scenarios),
        "graph_node_count": graph.get("node_count", 0),
        "graph_edge_count": graph.get("edge_count", 0),
        "graph_connected": graph.get("is_connected", False),
        "verified_edges": graph.get("verified_edges_count", 0),
        "inferred_edges": graph.get("inferred_edges_count", 0),
        "disconnected_spaces": graph.get("disconnected_spaces", []),
        "spaces_without_exit_route": graph.get("spaces_without_exit_route", []),
        "graph_confidence": graph.get("graph_confidence_score", 0),
        "max_confidence": scenario_summary["max_confidence"],
        "min_confidence": scenario_summary["min_confidence"],
        "risk_levels": scenario_summary["risk_levels"],
        "high_risk_count": scenario_summary["risk_counts"].get("high", 0),
        "medium_risk_count": scenario_summary["risk_counts"].get("medium", 0),
        "low_risk_count": scenario_summary["risk_counts"].get("low", 0),
        "compliance_statuses": scenario_summary["compliance_statuses"],
        "route_reliabilities": scenario_summary["route_reliabilities"],
        "reliability": _reliability(result, graph),
        "readiness_score": result.readiness.get("model_readiness_score", 0),
        "processing_readiness_score": result.readiness.get("processing_readiness_score", 0),
        "engineering_evidence_score": result.readiness.get("engineering_evidence_score", 0),
        "analysis_scope": result.readiness.get("analysis_scope", ""),
        "readiness_label": result.readiness.get("readiness_label", ""),
        "readiness_warnings": result.readiness.get("warnings", []),
        "readiness_critical_issues": result.readiness.get("critical_issues", []),
        "regulation_clause_count": result.regulation_clause_count,
        "regulation_rule_count": result.regulation_rule_count,
        "supported_uploaded_rule_candidates": result.regulation_application.get(
            "supported_uploaded_rule_candidate_count",
            result.regulation_application.get("uploaded_rule_count", 0),
        ),
        "applied_uploaded_rules": result.regulation_application.get("active_uploaded_threshold_count", 0),
        "unsupported_rules": result.regulation_application.get("unsupported_rule_count", 0),
        "errors": result.errors,
    }
    row.update(raw_counts)
    return row


def write_csv(rows: list[dict], path: Path) -> None:
    """Write diagnostics rows to a CSV with stable columns."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "file",
        "path",
        "compatibility_status",
        "failure_reason",
        "schema",
        "raw_schema",
        "ifcopenshell_open",
        "file_size_bytes",
        "is_git_lfs_pointer",
        "raw_ifcspace_count",
        "raw_ifcdoor_count",
        "raw_ifcstair_count",
        "raw_ifcwall_count",
        "raw_ifcslab_count",
        "raw_ifcbuildingelementproxy_count",
        "raw_ifcopeningelement_count",
        "raw_ifcrelspaceboundary_count",
        "raw_ifcbuildingstorey_count",
        "extracted_spaces",
        "extracted_doors",
        "extracted_stairs",
        "door_widths_found",
        "door_widths_assumed",
        "space_areas_found",
        "space_areas_assumed",
        "detected_exits",
        "door_space_connections",
        "inferred_connections",
        "inferred_exits",
        "graph_node_count",
        "graph_edge_count",
        "graph_connected",
        "verified_edges",
        "inferred_edges",
        "disconnected_spaces",
        "spaces_without_exit_route",
        "doors_without_connected_spaces",
        "scenarios",
        "max_confidence",
        "min_confidence",
        "risk_levels",
        "compliance_statuses",
        "route_reliabilities",
        "graph_confidence",
        "processing_readiness_score",
        "engineering_evidence_score",
        "analysis_scope",
        "readiness_score",
        "readiness_label",
        "reliability",
        "mode",
        "candidate_geometry_elements",
        "regulation_clause_count",
        "regulation_rule_count",
        "supported_uploaded_rule_candidates",
        "applied_uploaded_rules",
        "unsupported_rules",
        "errors",
        "readiness_warnings",
        "readiness_critical_issues",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            serialised = {
                key: json.dumps(value) if isinstance(value, (list, dict)) else value
                for key, value in row.items()
            }
            writer.writerow(serialised)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", help="IFC files or folders to audit")
    parser.add_argument("--max-scenarios", type=int, default=5)
    parser.add_argument("--regulations", help="Optional TXT/MD/PDF/DOCX regulation file to apply")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of a table")
    args = parser.parse_args()

    files = discover_ifcs(args.inputs)
    if not files:
        parser.error("No IFC files found in the supplied inputs.")

    if args.json:
        route_loguru_to_stderr_for_json()
        with contextlib.redirect_stdout(sys.stderr):
            regulation_text = extract_regulation_text(args.regulations) if args.regulations else None
            rows = [audit_file(path, args.max_scenarios, regulation_text=regulation_text) for path in files]
        print(json.dumps(rows, indent=2))
    else:
        regulation_text = extract_regulation_text(args.regulations) if args.regulations else None
        rows = [audit_file(path, args.max_scenarios, regulation_text=regulation_text) for path in files]
        for row in rows:
            print(
                f"{row['file']} | {row['schema']} | success={row['success']} | "
                f"mode={row['mode']} | screened={row['screened_elements_or_spaces']} | "
                f"raw spaces/doors/stairs={row['raw_ifcspace_count']}/{row['raw_ifcdoor_count']}/{row['raw_ifcstair_count']} | "
                f"graph={row['graph_node_count']}n/{row['graph_edge_count']}e | "
                f"scenarios={row['scenarios']} | reliability={row['reliability']} | "
                f"graph_confidence={row['graph_confidence']:.2f} | max_confidence={row['max_confidence']:.2f}"
            )
            for error in row["errors"]:
                print(f"  ERROR: {error}")
    return 0 if all(row["success"] for row in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
