"""
Basic tests for BIM Evacuation System.
"""
import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.config_loader import ConfigLoader
from src.utils.helpers import RiskLevel, ComplianceStatus, generate_id
from src.bim_processing.ifc_parser import (
    BuildingData,
    DoorData,
    Point3D,
    SpaceData,
    StairData,
)
from src.bim_processing.spatial_graph import SpatialGraphBuilder


class TestConfigLoader:
    """Test configuration loader."""
    
    def test_load_config(self):
        """Test loading configuration."""
        config = ConfigLoader()
        assert config.config is not None
        assert config.get('app.name') is not None
    
    def test_get_nested_value(self):
        """Test getting nested configuration values."""
        config = ConfigLoader()
        value = config.get('paths.data_dir')
        assert value is not None
    
    def test_get_default(self):
        """Test getting default value for missing key."""
        config = ConfigLoader()
        value = config.get('nonexistent.key', 'default')
        assert value == 'default'


class TestHelpers:
    """Test helper functions."""
    
    def test_generate_id(self):
        """Test ID generation."""
        id1 = generate_id("TEST")
        id2 = generate_id("TEST")
        assert id1 != id2
        assert id1.startswith("TEST_")
    
    def test_risk_level_enum(self):
        """Test risk level enumeration."""
        assert RiskLevel.LOW.value == "low"
        assert RiskLevel.MEDIUM.value == "medium"
        assert RiskLevel.HIGH.value == "high"
    
    def test_compliance_status_enum(self):
        """Test compliance status enumeration."""
        assert ComplianceStatus.COMPLIANT.value == "compliant"
        assert ComplianceStatus.NON_COMPLIANT.value == "non_compliant"


class TestPipelineImports:
    """Test that pipeline components can be imported."""
    
    def test_import_ifc_parser(self):
        """Test importing IFC parser."""
        from src.bim_processing.ifc_parser import IFCParser
        assert IFCParser is not None
    
    def test_import_spatial_graph(self):
        """Test importing spatial graph."""
        from src.bim_processing.spatial_graph import SpatialGraphBuilder
        assert SpatialGraphBuilder is not None
    
    def test_import_regulation_parser(self):
        """Test importing regulation parser."""
        from src.nlp.regulation_parser import RegulationParser
        assert RegulationParser is not None
    
    def test_import_rag_engine(self):
        """Test importing RAG engine."""
        from src.nlp.rag_engine import RAGEngine
        assert RAGEngine is not None
    
    def test_import_scenario_generator(self):
        """Test importing scenario generator."""
        from src.scenario.scenario_generator import ScenarioGenerator
        assert ScenarioGenerator is not None
    
    def test_import_pipeline(self):
        """Test importing pipeline."""
        from src.pipeline.evacuation_pipeline import EvacuationPipeline
        assert EvacuationPipeline is not None


def test_geometry_derived_graph_does_not_add_disconnected_stair_nodes():
    building = BuildingData(id="B1", name="Geometry Test", extraction_mode="geometry_derived")
    building.spaces["S1"] = SpaceData(id="S1", name="Element 1", area=1)
    building.spaces["S2"] = SpaceData(id="S2", name="Element 2", area=1)
    building.stairs["STAIR1"] = StairData(
        id="STAIR1", name="Source stair", width=1.2, riser_height=0.17, tread_length=0.25
    )
    connection = DoorData(
        id="C1",
        name="Connection",
        width=0.9,
        height=2.1,
        location=Point3D(),
        connected_spaces=["S1", "S2"],
    )
    exit_door = DoorData(
        id="E1",
        name="Egress",
        width=1.2,
        height=2.1,
        location=Point3D(),
        is_exit=True,
        connected_spaces=["S2"],
    )
    building.doors = {"C1": connection, "E1": exit_door}
    building.exits = {"E1": exit_door}

    graph = SpatialGraphBuilder(building)
    assert graph.build()
    assert graph.get_graph_stats()["is_connected"]
    assert "STAIR1" not in graph.graph


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
