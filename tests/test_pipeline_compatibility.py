"""Regression tests for geometry-only IFC compatibility behavior."""

from pathlib import Path

import pytest

from src.pipeline.evacuation_pipeline import EvacuationPipeline


IFC_PATH = Path(__file__).parent / "fixtures" / "11134_V_Motebello_Heistopp_Rev.ifc"
pytestmark = pytest.mark.skipif(
    not IFC_PATH.exists(),
    reason="Optional IFC regression fixture is not included in this checkout",
)


def test_geometry_only_ifc_uses_file_geometry():
    result = EvacuationPipeline().run(str(IFC_PATH), max_scenarios=3)

    assert result.success
    assert result.source_mode == "geometry_derived"
    assert result.building.name == "Villa Montebello"
    assert len(result.scenarios) == 3
    assert result.readiness["critical_issues"]
    assert all(not scenario.origin_space_name.startswith("Office") for scenario in result.scenarios)


def test_geometry_only_ifc_topology_comes_from_file_elements():
    pipeline = EvacuationPipeline()
    result = pipeline.run(str(IFC_PATH), max_scenarios=2)

    assert result.success
    assert result.source_mode == "geometry_derived"
    assert len(result.scenarios) == 2
    assert result.building.spaces
    assert all(
        space.space_type == "structural_proxy"
        for space in result.building.spaces.values()
    )
    assert result.building.geometry_elements_available == 19
    assert result.building.geometry_elements_used == len(result.building.spaces)
    assert pipeline.graph_builder.get_graph_stats()["is_connected"]
    assert all(scenario.confidence_score <= 0.5 for scenario in result.scenarios)
    assert result.source_file_name == IFC_PATH.name
    assert len(result.source_file_sha256) == 64
