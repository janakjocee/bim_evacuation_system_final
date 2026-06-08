"""Tests for IFC compatibility/readiness validation."""

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
