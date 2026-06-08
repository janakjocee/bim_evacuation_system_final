"""Run a concise compatibility and scenario-generation audit for IFC files."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.pipeline.evacuation_pipeline import EvacuationPipeline


def discover_ifcs(inputs: list[str]) -> list[Path]:
    files: list[Path] = []
    for value in inputs:
        path = Path(value).expanduser()
        if path.is_dir():
            files.extend(sorted(path.rglob("*.ifc")))
        elif path.is_file() and path.suffix.lower() == ".ifc":
            files.append(path)
    return list(dict.fromkeys(path.resolve() for path in files))


def audit_file(path: Path, max_scenarios: int) -> dict:
    pipeline = EvacuationPipeline()
    result = pipeline.run(str(path), max_scenarios=max_scenarios)
    graph = pipeline.graph_builder.get_graph_stats() if pipeline.graph_builder else {}
    building = result.building
    return {
        "file": path.name,
        "schema": result.ifc_schema,
        "success": result.success,
        "mode": result.source_mode,
        "building": building.name if building else None,
        "screened_elements_or_spaces": len(building.spaces) if building else 0,
        "candidate_geometry_elements": building.geometry_elements_available if building else 0,
        "scenarios": len(result.scenarios),
        "graph_connected": graph.get("is_connected", False),
        "max_confidence": round(
            max((scenario.confidence_score for scenario in result.scenarios), default=0.0), 2
        ),
        "errors": result.errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", help="IFC files or folders to audit")
    parser.add_argument("--max-scenarios", type=int, default=5)
    parser.add_argument("--json", action="store_true", help="Print JSON instead of a table")
    args = parser.parse_args()

    files = discover_ifcs(args.inputs)
    if not files:
        parser.error("No IFC files found in the supplied inputs.")

    rows = [audit_file(path, args.max_scenarios) for path in files]
    if args.json:
        print(json.dumps(rows, indent=2))
    else:
        for row in rows:
            print(
                f"{row['file']} | {row['schema']} | success={row['success']} | "
                f"mode={row['mode']} | screened={row['screened_elements_or_spaces']} | "
                f"scenarios={row['scenarios']} | connected={row['graph_connected']} | "
                f"max_confidence={row['max_confidence']:.2f}"
            )
            for error in row["errors"]:
                print(f"  ERROR: {error}")
    return 0 if all(row["success"] for row in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
