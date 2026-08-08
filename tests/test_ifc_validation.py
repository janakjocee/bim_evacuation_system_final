"""Tests for IFC compatibility/readiness validation."""

import json
import subprocess
import sys

import numpy as np

import src.bim_processing.ifc_parser as ifc_parser_module
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


def test_parser_reads_space_planned_area_properties():
    parser = IFCParser()

    class Space:
        IsDefinedBy = []

    parser._get_properties = lambda element: {"NetPlannedArea": 18.5}
    area, source, confidence, flags = parser._extract_space_area(Space())

    assert area == 18.5
    assert source == "IFC space property area"
    assert confidence == 1.0
    assert flags == []


def test_parser_uses_long_name_for_space_type():
    parser = IFCParser()

    class Space:
        Name = "207"
        LongName = "Bedroom"
        Description = ""
        PredefinedType = "INTERNAL"

    assert parser._get_space_type(Space()) == "residential"


def test_parser_resolves_nested_object_placement_to_world_coordinates(monkeypatch):
    parser = IFCParser()
    matrix = np.eye(4)
    matrix[:3, 3] = [8.383, -15.553, 3.1]

    class Element:
        ObjectPlacement = object()

    monkeypatch.setattr(
        ifc_parser_module.ifcopenshell.util.placement,
        "get_local_placement",
        lambda placement: matrix,
    )

    assert parser._get_location(Element()) == Point3D(8.383, -15.553, 3.1)


def test_parser_does_not_treat_placeholder_properties_as_true():
    parser = IFCParser()

    assert parser._property_bool({"IsExternal": "INTERNAL"}, "IsExternal") is False
    assert parser._property_bool({"IsExternal": "unexpected label"}, "IsExternal") is False
    assert parser._property_has_rating({"FireRating": "Fire Rating"}, "FireRating") is False
    assert parser._property_has_rating({"FireRating": "FD60"}, "FireRating") is True


def test_box_distance_detects_touching_stair_and_space_geometry():
    stair_bounds = (Point3D(1, 1, 0), Point3D(3, 3, 6))
    upper_space_bounds = (Point3D(0, 0, 3), Point3D(4, 4, 6))
    distant_space_bounds = (Point3D(10, 10, 3), Point3D(14, 14, 6))

    assert IFCParser._box_to_box_distance(stair_bounds, upper_space_bounds) == 0
    assert IFCParser._box_to_box_distance(stair_bounds, distant_space_bounds) > 9


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


def test_batch_ifc_diagnostics_writes_csv_and_json(tmp_path):
    pointer = tmp_path / "pointer.ifc"
    pointer.write_text(
        "version https://git-lfs.github.com/spec/v1\n"
        "oid sha256:0123456789abcdef\n"
        "size 12345\n"
    )
    output_dir = tmp_path / "diagnostics"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/batch_ifc_diagnostics.py",
            str(pointer),
            "--output-dir",
            str(output_dir),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    summary = json.loads(result.stdout)
    assert summary["status_counts"]["fail"] == 1
    rows = json.loads((output_dir / "compatibility_matrix.json").read_text())
    assert rows[0]["pass_partial_fail_status"] == "fail"
    assert rows[0]["file_name"] == "pointer.ifc"
    assert rows[0]["opens_with_ifcopenshell"] is False
    assert rows[0]["scenarios_generated"] == 0
    assert rows[0]["failure_reason"]
    csv_text = (output_dir / "compatibility_matrix.csv").read_text()
    assert "pass_partial_fail_status" in csv_text
    assert "ifc_schema" in csv_text
    assert "Git LFS pointer" in csv_text
    per_file = output_dir / "per_file" / "pointer.diagnostic.json"
    assert per_file.exists()
    assert json.loads(per_file.read_text())["failure_reason"]


def test_batch_ifc_diagnostics_supports_input_output_flags(tmp_path):
    pointer = tmp_path / "flagged.ifc"
    pointer.write_text(
        "version https://git-lfs.github.com/spec/v1\n"
        "oid sha256:0123456789abcdef\n"
        "size 12345\n"
    )
    output_dir = tmp_path / "matrix"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/batch_ifc_diagnostics.py",
            "--input",
            str(tmp_path),
            "--output",
            str(output_dir),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    summary = json.loads(result.stdout)
    assert summary["input_count"] == 1
    assert summary["per_file_json_dir"].endswith("per_file")
    rows = json.loads((output_dir / "compatibility_matrix.json").read_text())
    required_fields = {
        "file_name",
        "ifc_schema",
        "opens_with_ifcopenshell",
        "extraction_mode",
        "source_mode",
        "geometry_elements_available",
        "geometry_elements_used",
        "space_count",
        "door_count",
        "exit_count",
        "verified_edges_count",
        "inferred_edges_count",
        "scenarios_generated",
        "pass_partial_fail_status",
        "failure_reason",
        "reliability_notes",
    }
    assert required_fields.issubset(rows[0])
