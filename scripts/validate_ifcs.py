"""Run a concise compatibility and scenario-generation audit for IFC files."""
from __future__ import annotations

import argparse
import contextlib
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
            files.extend(sorted(path.rglob("*.ifc")))
        elif path.is_file() and path.suffix.lower() == ".ifc":
            files.append(path)
    return list(dict.fromkeys(path.resolve() for path in files))


def _ifc_entity_counts(path: Path) -> dict:
    counts = {
        "ifcopenshell_open": False,
        "raw_schema": "UNKNOWN",
        "raw_ifcspace_count": 0,
        "raw_ifcdoor_count": 0,
        "raw_ifcstair_count": 0,
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


def audit_file(path: Path, max_scenarios: int, regulation_text: str | None = None) -> dict:
    pipeline = EvacuationPipeline()
    raw_counts = _ifc_entity_counts(path)
    result = pipeline.run(str(path), regulation_text=regulation_text, max_scenarios=max_scenarios)
    graph = pipeline.graph_builder.get_graph_stats() if pipeline.graph_builder else {}
    building = result.building
    row = {
        "file": path.name,
        "file_size_bytes": path.stat().st_size,
        "is_git_lfs_pointer": _looks_like_git_lfs_pointer(path),
        "schema": result.ifc_schema,
        "success": result.success,
        "mode": result.source_mode,
        "building": building.name if building else None,
        "screened_elements_or_spaces": len(building.spaces) if building else 0,
        "extracted_spaces": len(building.spaces) if building else 0,
        "extracted_doors": len(building.doors) if building else 0,
        "detected_exits": len(building.exits) if building else 0,
        "door_space_connections": sum(len(door.connected_spaces) for door in building.doors.values()) if building else 0,
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
        "max_confidence": round(
            max((scenario.confidence_score for scenario in result.scenarios), default=0.0), 2
        ),
        "reliability": _reliability(result, graph),
        "regulation_clause_count": result.regulation_clause_count,
        "regulation_rule_count": result.regulation_rule_count,
        "applied_uploaded_rules": result.regulation_application.get("uploaded_rule_count", 0),
        "unsupported_rules": result.regulation_application.get("unsupported_rule_count", 0),
        "errors": result.errors,
    }
    row.update(raw_counts)
    return row


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
