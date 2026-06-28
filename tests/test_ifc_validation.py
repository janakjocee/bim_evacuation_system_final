"""Tests for IFC compatibility/readiness validation."""

import json
import subprocess
import sys

from src.bim_processing.ifc_parser import BuildingData, IFCParser, Point3D, SpaceData
from src.bim_processing.ifc_validation import validate_ifc_model


def test_ifc_validation_handles_missing_information():
    result = validate_ifc_model(extracted_data={
        "schema": "IFC4",
        "space_count": 0,
        "door_count": 0,
        "buildingstorey_count": 0,
        "possible_exits_count": 0,
        "graph_connectivity_complete": False,
    })
    assert result["model_readiness_score"] < 50
    assert result["critical_issues"]
    assert "IFC2X3" in result["target_compatibility"]


def test_ifc_validation_good_model_gets_high_score():
    result = validate_ifc_model(extracted_data={
        "schema": "IFC4X3",
        "space_count": 12,
        "door_count": 14,
        "buildingstorey_count": 2,
        "stair_count": 2,
        "possible_exits_count": 2,
        "missing_door_widths": 0,
        "missing_space_areas": 0,
        "missing_occupancy": 0,
        "missing_material_fuel_fire_properties": False,
        "graph_connectivity_complete": True,
    })
    assert result["model_readiness_score"] >= 90
    assert result["readiness_label"] == "Ready for scenario generation"


def test_parser_infers_topology_for_spaces_without_doors():
    building = BuildingData(id="B1", name="Space-only IFC")
    building.spaces = {
        "S1": SpaceData(
            id="S1",
            name="Room 1",
            area=20,
            bounding_box=(Point3D(0, 0, 0), Point3D(4, 4, 3)),
        ),
        "S2": SpaceData(
            id="S2",
            name="Room 2",
            area=20,
            bounding_box=(Point3D(6, 0, 0), Point3D(10, 4, 3)),
        ),
        "S3": SpaceData(
            id="S3",
            name="Room 3",
            area=20,
            bounding_box=(Point3D(12, 0, 0), Point3D(16, 4, 3)),
        ),
    }

    IFCParser()._infer_space_topology(building)

    assert building.extraction_mode == "semantic_spaces_inferred_topology"
    assert len(building.doors) >= 3
    assert len(building.exits) == 2
    assert all(door.connected_spaces for door in building.doors.values())


def test_validate_ifcs_json_stdout_is_parseable_on_failure(tmp_path):
    pointer = tmp_path / "pointer.ifc"
    pointer.write_text(
        "version https://git-lfs.github.com/spec/v1\n"
        "oid sha256:0123456789abcdef\n"
        "size 12345\n"
    )

    result = subprocess.run(
        [sys.executable, "scripts/validate_ifcs.py", str(pointer), "--json"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    rows = json.loads(result.stdout)
    assert rows[0]["is_git_lfs_pointer"] is True
    assert rows[0]["success"] is False
