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
from src.nlp.regulation_parser import RegulationClause, RegulationRule
from src.nlp.regulation_parser import RegulationParser
from src.scenario.compliance_checker import ComplianceChecker
from src.scenario.scenario_generator import ScenarioGenerator


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


def test_graph_does_not_fabricate_cyclic_connectivity():
    building = BuildingData(id="B1", name="No Connectivity")
    building.spaces["S1"] = SpaceData(id="S1", name="Room A", area=20)
    building.spaces["S2"] = SpaceData(id="S2", name="Room B", area=20)
    building.doors["D1"] = DoorData(
        id="D1",
        name="Unconnected Door",
        width=0.9,
        height=2.1,
        location=Point3D(),
    )

    graph = SpatialGraphBuilder(building)
    assert graph.build()
    stats = graph.get_graph_stats()

    assert stats["edge_count"] == 0
    assert set(stats["disconnected_spaces"]) == {"S1", "S2"}
    assert stats["doors_without_connected_spaces"] == ["D1"]
    assert stats["graph_confidence_score"] == 0.0


def test_generated_scenario_exports_explainability_trace():
    building = BuildingData(id="B1", name="Explainability Test")
    building.spaces["S1"] = SpaceData(id="S1", name="Room A", area=20)
    exit_door = DoorData(
        id="E1",
        name="Main Exit",
        width=1.2,
        height=2.1,
        location=Point3D(),
        is_exit=True,
        connected_spaces=["S1"],
    )
    building.doors = {"E1": exit_door}
    building.exits = {"E1": exit_door}

    graph = SpatialGraphBuilder(building)
    assert graph.build()

    scenarios = ScenarioGenerator(building, graph).generate(max_scenarios=1)
    assert scenarios
    payload = scenarios[0].to_dict()

    assert payload["risk_score"] >= 0
    assert payload["risk_factors"]["weighted_breakdown"]["total_score"] == payload["risk_score"]
    assert payload["decision_trace"]
    assert payload["decision_trace"][-1]["method"] == "Weighted deterministic score, not an opaque machine-learning prediction."
    assert payload["data_quality_notes"]


def test_uploaded_regulation_values_drive_compliance_rules():
    checker = ComplianceChecker()
    checker.update_regulations([
        RegulationClause(
            clause_id="R1",
            text="The travel distance to an exit must not exceed 30 metres.",
            applies_to="route",
            constraint_type="max_distance",
            value=30.0,
            unit="metres",
        ),
        RegulationClause(
            clause_id="R2",
            text="Final exit doors shall have a minimum clear opening width of 1200mm.",
            applies_to="door",
            constraint_type="min_width",
            value=1.2,
            unit="mm",
        ),
    ])

    route_check = checker.check_route(SpaceData(id="S1", name="Room", area=10), 35.0)[0]
    exit_check = checker.check_door(DoorData(
        id="E1",
        name="Final Exit",
        width=1.05,
        height=2.1,
        location=Point3D(),
        is_exit=True,
    ))[0]

    assert route_check.required_value == 30.0
    assert route_check.status == ComplianceStatus.NON_COMPLIANT
    assert route_check.evidence_source == "uploaded_regulation_rule"
    assert exit_check.required_value == 1.2
    assert exit_check.status == ComplianceStatus.NON_COMPLIANT
    assert exit_check.evidence_source == "uploaded_regulation_rule"


def test_structured_parser_extracts_multiple_rules_from_one_clause():
    parser = RegulationParser()
    parser.parse(
        "2.1 Means of Escape\n"
        "Travel distance to the nearest exit must not exceed 30 metres. "
        "Final exit doors shall have a minimum clear opening width of 1200mm."
    )

    metrics = {rule.metric: rule.value for rule in parser.rules}

    assert metrics["max_travel_distance"] == 30.0
    assert metrics["min_exit_width"] == 1.2


def test_structured_rules_override_defaults_and_attach_evidence():
    checker = ComplianceChecker()
    checker.update_regulation_rules([
        RegulationRule(
            rule_id="2.1-R1",
            source_section="2.1",
            source_text="Travel distance to the nearest exit must not exceed 30 metres.",
            applies_to="route",
            condition="general",
            metric="max_travel_distance",
            operator="<=",
            value=30.0,
            unit="metres",
        )
    ])

    check = checker.check_route(SpaceData(id="S1", name="Room", area=10), 35.0)[0]

    assert check.required_value == 30.0
    assert check.status == ComplianceStatus.NON_COMPLIANT
    assert check.evidence_source == "uploaded_regulation_rule"
    assert check.evidence[0]["rule_id"] == "2.1-R1"


def test_rag_evidence_is_attached_to_default_rule_checks():
    checker = ComplianceChecker()

    class Clause:
        clause_id = "A1"
        text = "Approved guidance discusses maximum travel distance to an exit."

    checker.set_evidence_provider(lambda query, top_k: [(Clause(), 0.82)])
    check = checker.check_route(SpaceData(id="S1", name="Room", area=10), 10.0)[0]

    assert check.evidence_source == "rag_uploaded_regulation"
    assert check.evidence[0]["clause_id"] == "A1"


def test_assumed_door_width_requires_review():
    checker = ComplianceChecker()
    result = checker.check_door(DoorData(
        id="D1",
        name="Assumed Door",
        width=0.9,
        height=2.1,
        location=Point3D(),
        assumptions={"width": "Assumed test width"},
        width_confidence=0.35,
    ))[0]

    assert result.status == ComplianceStatus.REQUIRES_REVIEW
    assert "requires expert confirmation" in result.message


def test_regulation_parser_recognizes_not_exceed_maximum_language():
    clauses = RegulationParser().parse(
        "1.1 Travel Distance\n"
        "The travel distance to the nearest exit must not exceed 30 metres."
    )

    assert clauses
    assert clauses[0].constraint_type == "max_distance"
    assert clauses[0].value == 30.0


def test_ifcspace_inferred_topology_caps_confidence():
    building = BuildingData(
        id="B1",
        name="Inferred Spaces",
        extraction_mode="semantic_spaces_inferred_topology",
    )
    building.spaces["S1"] = SpaceData(id="S1", name="Room A", area=20)
    exit_door = DoorData(
        id="E1",
        name="Inferred Exit",
        width=1.2,
        height=2.1,
        location=Point3D(),
        is_exit=True,
        connected_spaces=["S1"],
    )
    building.doors = {"E1": exit_door}
    building.exits = {"E1": exit_door}

    graph = SpatialGraphBuilder(building)
    assert graph.build()

    scenario = ScenarioGenerator(building, graph).generate(max_scenarios=1)[0]

    assert scenario.confidence_score <= 0.65
    assert "route links and exits were inferred" in " ".join(scenario.data_quality_notes)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
