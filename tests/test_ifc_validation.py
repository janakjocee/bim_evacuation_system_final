"""Tests for IFC compatibility/readiness validation."""

import json
import subprocess
import sys
from types import SimpleNamespace

import numpy as np

import src.bim_processing.ifc_parser as ifc_parser_module
from src.bim_processing.ifc_parser import BuildingData, DoorData, IFCParser, Point3D, SpaceData
from src.bim_processing.ifc_validation import validate_ifc_model
from src.bim_processing.spatial_graph import SpatialGraphBuilder
from scripts.validate_ifcs import _failure_reason


def test_ifc_failure_reason_uses_clean_sentence_separators():
    result = SimpleNamespace(success=True, source_mode="semantic_ifc")
    building = SimpleNamespace(exits={}, doors={}, spaces={})

    reason = _failure_reason(
        result,
        building,
        {
            "spaces_without_exit_route": ["S1"],
            "disconnected_spaces": ["S1"],
        },
    )

    assert reason == (
        "No exits detected; 1 space(s) lack an exit route; "
        "1 disconnected space(s)."
    )
    assert ".;" not in reason


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
    assert result["processing_readiness_score"] == 100
    assert result["engineering_evidence_score"] >= 90
    assert result["readiness_label"] == "Ready for semantic prototype screening"


def test_geometry_processing_can_pass_without_claiming_semantic_evidence():
    result = validate_ifc_model(extracted_data={
        "schema": "IFC2X3",
        "space_count": 0,
        "door_count": 0,
        "buildingstorey_count": 1,
        "possible_exits_count": 2,
        "analysis_space_count": 16,
        "analysis_door_count": 17,
        "analysis_mode": "geometry_derived",
        "missing_door_widths": 17,
        "missing_exit_identification": True,
        "inferred_exit_count": 2,
        "graph_connectivity_complete": True,
        "verified_edge_count": 0,
        "inferred_edge_count": 32,
        "graph_confidence_score": 0.35,
    })

    assert result["processing_readiness_score"] == 100
    assert result["engineering_evidence_score"] < 50
    assert result["analysis_scope"] == "ifc_element_geometry_screening"
    assert "exploratory" in result["readiness_label"].lower()


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


def test_parser_converts_millimetre_lengths_and_areas_to_si_units():
    parser = IFCParser()
    parser.length_unit_scale = 0.001
    parser.area_unit_scale = 0.000001
    door = SimpleNamespace(OverallWidth=900.0, OverallHeight=2100.0)

    width, height, _, confidence, flags = parser._extract_door_dimensions(door, {})
    parser._get_properties = lambda element: {"NetPlannedArea": 18_500_000.0}
    area, _, area_confidence, area_flags = parser._extract_space_area(SimpleNamespace(IsDefinedBy=[]))

    assert width == 0.9
    assert height == 2.1
    assert confidence == 1.0
    assert flags == []
    assert area == 18.5
    assert area_confidence == 1.0
    assert area_flags == []


def test_inference_recovers_spaces_when_existing_doors_have_no_connections():
    building = BuildingData(id="B1", name="Unconnected semantic doors")
    building.spaces = {
        "S1": SpaceData(
            id="S1",
            name="Room 1",
            area=10,
            bounding_box=(Point3D(0, 0, 0), Point3D(4, 4, 3)),
        ),
        "S2": SpaceData(
            id="S2",
            name="Room 2",
            area=10,
            bounding_box=(Point3D(5, 0, 0), Point3D(9, 4, 3)),
        ),
    }
    building.doors["UNCONNECTED"] = DoorData(
        id="UNCONNECTED",
        name="Source door without topology",
        width=0.9,
        height=2.1,
        location=Point3D(100, 100, 0),
    )

    IFCParser()._infer_space_topology(building)

    inferred = [door for door in building.doors.values() if door.connection_source == "inferred_geometry"]
    assert building.extraction_mode == "semantic_spaces_inferred_topology"
    assert inferred
    assert building.exits
    assert all(space.connected_doors for space in building.spaces.values())


def test_parser_uses_long_name_for_space_type():
    parser = IFCParser()

    class Space:
        Name = "207"
        LongName = "Bedroom"
        Description = ""
        PredefinedType = "INTERNAL"

    assert parser._get_space_type(Space()) == "residential"


def test_parser_classifies_realistic_space_names():
    parser = IFCParser()

    class Space:
        Name = "A103"
        Description = ""
        PredefinedType = "INTERNAL"

    expected = {
        "Kitchen": "kitchen",
        "Bathroom 1": "toilet",
        "Foyer": "lobby",
        "Physical Exam": "clinical",
        "Central Waiting": "assembly",
        "Mechanical Room": "industrial",
    }
    for long_name, space_type in expected.items():
        Space.LongName = long_name
        assert parser._get_space_type(Space()) == space_type


def test_graph_preserves_per_space_connection_provenance():
    building = BuildingData(id="B1", name="Mixed provenance")
    building.spaces = {
        "S1": SpaceData(id="S1", name="Verified", area=10),
        "S2": SpaceData(id="S2", name="Inferred", area=10),
    }
    building.doors = {
        "D1": DoorData(
            id="D1",
            name="Final Exit",
            width=1.1,
            height=2.1,
            location=Point3D(),
            is_exit=True,
            connected_spaces=["S1", "S2"],
            connection_source="IfcRelSpaceBoundary",
            connection_sources={
                "S1": "IfcRelSpaceBoundary",
                "S2": "inferred_proximity_supplement",
            },
        )
    }
    building.exits = dict(building.doors)

    graph = SpatialGraphBuilder(building)
    assert graph.build()
    assert graph.graph["S1"]["D1"]["inferred"] is False
    assert graph.graph["S2"]["D1"]["inferred"] is True


def test_parser_adds_bounded_supplement_for_disconnected_space():
    parser = IFCParser()
    building = BuildingData(id="B1", name="Boundary omission")
    building.spaces = {
        "S1": SpaceData(id="S1", name="Known room", area=10, connected_doors=["D1"]),
        "S2": SpaceData(
            id="S2",
            name="Omitted boundary room",
            area=10,
            bounding_box=(Point3D(0, 0, 0), Point3D(4, 4, 3)),
        ),
    }
    building.doors = {
        "D1": DoorData(
            id="D1",
            name="Nearby Door",
            width=0.9,
            height=2.1,
            location=Point3D(4.2, 2, 1),
            connected_spaces=["S1"],
            connection_source="IfcRelSpaceBoundary",
            connection_sources={"S1": "IfcRelSpaceBoundary"},
        )
    }

    parser._connect_doors_to_spaces_by_proximity(building)

    assert building.doors["D1"].connected_spaces == ["S1", "S2"]
    assert building.doors["D1"].connection_sources["S1"] == "IfcRelSpaceBoundary"
    assert building.doors["D1"].connection_sources["S2"] == "inferred_proximity_supplement"
    assert "connectivity" in building.spaces["S2"].assumptions


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
    assert (output_dir / "compatibility_summary.json").exists()
    assert json.loads((output_dir / "compatibility_summary.json").read_text())["input_count"] == 1
    rows = json.loads((output_dir / "compatibility_matrix.json").read_text())
    assert rows[0]["pass_partial_fail_status"] == "fail"
    assert rows[0]["file_name"] == "pointer.ifc"
    assert rows[0]["opens_with_ifcopenshell"] is False
    assert rows[0]["scenarios_generated"] == 0
    assert len(rows[0]["source_file_sha256"]) == 64
    assert rows[0]["is_duplicate_payload"] is False
    assert rows[0]["payload_occurrence_count"] == 1
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
        "source_file_sha256",
        "is_duplicate_payload",
        "duplicate_payload_of",
        "payload_occurrence_count",
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
        "processing_readiness_score",
        "engineering_evidence_score",
        "analysis_scope",
        "scenarios_generated",
        "pass_partial_fail_status",
        "failure_reason",
        "reliability_notes",
    }
    assert required_fields.issubset(rows[0])


def test_batch_ifc_diagnostics_reports_unique_and_duplicate_payloads(tmp_path):
    pointer_text = (
        "version https://git-lfs.github.com/spec/v1\n"
        "oid sha256:0123456789abcdef\n"
        "size 12345\n"
    )
    (tmp_path / "first.ifc").write_text(pointer_text)
    (tmp_path / "second.ifc").write_text(pointer_text)
    output_dir = tmp_path / "duplicates"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/batch_ifc_diagnostics.py",
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
    assert summary["input_count"] == 2
    assert summary["unique_payload_count"] == 1
    assert summary["duplicate_input_count"] == 1
    assert summary["unique_status_counts"] == {"fail": 1}
    assert len(summary["duplicate_payload_groups"]) == 1
    assert summary["summary_json"].endswith("compatibility_summary.json")

    rows = json.loads((output_dir / "compatibility_matrix.json").read_text())
    assert rows[0]["payload_occurrence_count"] == 2
    assert rows[0]["is_duplicate_payload"] is False
    assert rows[1]["is_duplicate_payload"] is True
    assert rows[1]["duplicate_payload_of"] == rows[0]["file_name"]
