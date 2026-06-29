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
from src.nlp.document_loader import extract_regulation_text
from src.scenario.compliance_checker import ComplianceChecker
from src.scenario.scenario_generator import ScenarioGenerator, classify_route_reliability
from src.scenario.risk_classifier import RiskClassifier, RiskFactors
from src.scenario.ifc_dataset_exporter import building_to_worst_case_dataset
from src.scenario.worst_case_engine import validate_scenario_dataset
from src.pipeline.evacuation_pipeline import EvacuationPipeline, PipelineResult
from src.pipeline.manual_corrections import apply_manual_corrections


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
        connection_source="inferred_geometry",
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
    assert payload["evacuation_route"]["inferred_edge_count"] == 1
    assert payload["compliance_status"] == ComplianceStatus.REQUIRES_REVIEW.value


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


def test_rule_application_summary_reports_defaults_and_unsupported_rules():
    checker = ComplianceChecker()
    checker.update_regulation_rules([
        RegulationRule(
            rule_id="2.1-R1",
            source_section="2.1",
            source_text="Travel distance must not exceed 30 metres.",
            applies_to="route",
            condition="general",
            metric="max_travel_distance",
            operator="<=",
            value=30.0,
            unit="metres",
        ),
        RegulationRule(
            rule_id="2.2-R1",
            source_section="2.2",
            source_text="Smoke reservoirs shall be provided where required.",
            applies_to="general",
            condition="general",
            metric="smoke_reservoir_required",
            operator="==",
            value=1.0,
            unit="boolean",
        ),
    ])

    summary = checker.get_rule_application_summary()

    assert summary["uploaded_rule_count"] == 1
    assert summary["unsupported_rule_count"] == 1
    assert any(row["rule_key"] == "max_travel_distance" and row["source"] == "uploaded_regulation_rule" for row in summary["active_thresholds"])


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


def test_corridor_width_check_uses_bounding_box():
    checker = ComplianceChecker()
    corridor = SpaceData(
        id="C1",
        name="Narrow Corridor",
        area=12,
        space_type="corridor",
        bounding_box=(Point3D(0, 0, 0), Point3D(0.9, 10, 3)),
    )

    result = checker.check_corridor(corridor)[0]

    assert result.status == ComplianceStatus.NON_COMPLIANT
    assert result.regulation_id == "min_corridor_width"
    assert result.measured_value == 0.9


def test_stair_dimension_checks_flag_unsafe_values():
    checker = ComplianceChecker()
    stair = StairData(
        id="ST1",
        name="Tight Stair",
        width=0.8,
        riser_height=0.22,
        tread_length=0.2,
    )

    checks = checker.check_stair(stair)
    statuses = {check.regulation_id: check.status for check in checks}

    assert statuses["min_stair_width"] == ComplianceStatus.NON_COMPLIANT
    assert statuses["max_riser_height"] == ComplianceStatus.NON_COMPLIANT
    assert statuses["min_tread_length"] == ComplianceStatus.NON_COMPLIANT


def test_low_confidence_topology_cannot_be_low_risk():
    classifier = RiskClassifier()
    factors = RiskFactors(
        travel_distance=5.0,
        evacuation_time=4.0,
        compliance_score=1.0,
        exit_capacity_ratio=1.0,
        graph_confidence=0.35,
        data_quality_confidence=0.4,
        inferred_edge_ratio=1.0,
    )

    assert classifier.classify(factors) == RiskLevel.MEDIUM


def test_practical_route_weaknesses_prevent_low_risk():
    classifier = RiskClassifier()
    factors = RiskFactors(
        travel_distance=5.0,
        evacuation_time=4.0,
        compliance_score=1.0,
        exit_capacity_ratio=1.0,
        graph_confidence=1.0,
        data_quality_confidence=1.0,
        narrow_door_count=1,
        no_alternative_route_count=1,
    )

    assert classifier.classify(factors) == RiskLevel.MEDIUM
    breakdown = classifier.risk_contribution_breakdown(factors)
    assert breakdown["practical_data_penalty"] > 0


def test_missing_exit_forces_high_risk():
    classifier = RiskClassifier()
    factors = RiskFactors(
        travel_distance=5.0,
        evacuation_time=4.0,
        compliance_score=1.0,
        exit_capacity_ratio=1.0,
        graph_confidence=1.0,
        data_quality_confidence=1.0,
        missing_exit_count=1,
    )

    assert classifier.classify(factors) == RiskLevel.HIGH


def test_regulation_text_loader_supports_txt_docx_and_pdf(tmp_path):
    txt_path = tmp_path / "rules.txt"
    txt_path.write_text("Travel distance must not exceed 30 metres.", encoding="utf-8")
    assert "30 metres" in extract_regulation_text(txt_path)

    docx = pytest.importorskip("docx")
    docx_path = tmp_path / "rules.docx"
    document = docx.Document()
    document.add_paragraph("Final exit doors shall be 1200mm wide.")
    document.save(docx_path)
    assert "1200mm" in extract_regulation_text(docx_path)

    reportlab_canvas = pytest.importorskip("reportlab.pdfgen.canvas")
    pdf_path = tmp_path / "rules.pdf"
    canvas = reportlab_canvas.Canvas(str(pdf_path))
    canvas.drawString(72, 720, "Corridor width shall be at least 1200mm.")
    canvas.save()
    assert "1200mm" in extract_regulation_text(pdf_path)


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
        connection_source="inferred_geometry",
    )
    building.doors = {"E1": exit_door}
    building.exits = {"E1": exit_door}

    graph = SpatialGraphBuilder(building)
    assert graph.build()

    scenario = ScenarioGenerator(building, graph).generate(max_scenarios=1)[0]

    assert scenario.confidence_score <= 0.65
    assert scenario.risk_level != RiskLevel.LOW
    assert scenario.risk_factors["inferred_edge_ratio"] > 0
    assert "route links and exits were inferred" in " ".join(scenario.data_quality_notes)


def test_manual_corrections_update_exit_width_and_connectivity():
    building = BuildingData(id="B1", name="Manual Correction")
    building.spaces["S1"] = SpaceData(id="S1", name="Room", area=20)
    building.doors["D1"] = DoorData(
        id="D1",
        name="Door",
        width=0.9,
        height=2.1,
        location=Point3D(),
        assumptions={"width": "assumed"},
        width_confidence=0.25,
    )
    result = PipelineResult(
        success=False,
        building=building,
        regulation_application={
            "active_thresholds": [
                {"rule_key": "min_exit_width", "value": 1.1},
                {"rule_key": "max_travel_distance", "value": 30.0},
            ]
        },
    )

    corrected = apply_manual_corrections(
        result,
        {"doors": [{"id": "D1", "width": 1.2, "is_exit": True, "connected_spaces": "S1"}]},
        max_scenarios=1,
    )

    door = corrected.building.doors["D1"]
    assert door.is_exit
    assert door.width == 1.2
    assert door.width_confidence == 1.0
    assert door.connected_spaces == ["S1"]
    assert corrected.graph_stats["edge_count"] == 1
    assert corrected.scenarios
    assert corrected.scenarios[0].evacuation_route.destination == "D1"


def test_ifc_derived_worst_case_dataset_validates():
    building = BuildingData(id="B1", name="Dataset Export")
    building.spaces["S1"] = SpaceData(id="S1", name="Room", area=20, space_type="office")
    building.spaces["S2"] = SpaceData(id="S2", name="Corridor", area=10, space_type="corridor")
    exit_door = DoorData(
        id="E1",
        name="Exit",
        width=1.2,
        height=2.1,
        location=Point3D(),
        is_exit=True,
        connected_spaces=["S2"],
    )
    connector = DoorData(
        id="D1",
        name="Door",
        width=0.9,
        height=2.1,
        location=Point3D(),
        connected_spaces=["S1", "S2"],
    )
    building.doors = {"D1": connector, "E1": exit_door}
    building.exits = {"E1": exit_door}

    graph = SpatialGraphBuilder(building)
    assert graph.build()
    dataset = building_to_worst_case_dataset(building, graph_builder=graph, source_file_name="test.ifc")

    validate_scenario_dataset(dataset)
    assert dataset["dataset_kind"] == "ifc_derived_requires_review"
    assert any(space["type"] == "exit" for space in dataset["spaces"])
    assert dataset["connections"]


def test_pipeline_exports_json_and_csv_for_generated_scenarios(tmp_path):
    building = BuildingData(id="B1", name="Export Building")
    building.spaces["S1"] = SpaceData(id="S1", name="Room", area=20)
    exit_door = DoorData(
        id="E1",
        name="Exit",
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
    result = PipelineResult(
        success=True,
        building=building,
        scenarios=scenarios,
        source_file_name="synthetic.ifc",
        ifc_schema="SYNTHETIC",
        graph_stats=graph.get_graph_stats(),
    )

    exported = EvacuationPipeline().export_results(result, str(tmp_path), formats=["json", "csv"])

    assert Path(exported["json"]).exists()
    assert Path(exported["csv"]).exists()
    assert "synthetic.ifc" in Path(exported["json"]).read_text()
    assert scenarios[0].scenario_id in Path(exported["csv"]).read_text()


def test_ifc_dataset_exporter_adds_review_occupancy_for_geometry_spaces():
    building = BuildingData(id="B1", name="Geometry Dataset", extraction_mode="geometry_derived")
    building.spaces["G1"] = SpaceData(id="G1", name="Geometry Element", area=20, space_type="structural_element")
    exit_door = DoorData(
        id="E1",
        name="Inferred Exit",
        width=1.2,
        height=2.1,
        location=Point3D(),
        is_exit=True,
        connected_spaces=["G1"],
        connection_source="inferred_geometry",
        width_confidence=0.25,
    )
    building.doors = {"E1": exit_door}
    building.exits = {"E1": exit_door}

    dataset = building_to_worst_case_dataset(building)
    exported_space = next(space for space in dataset["spaces"] if space["id"] == "G1")

    assert exported_space["occupancy"] >= 1
    assert exported_space["occupancy_confidence"] == 0.25
    assert "Low-confidence review occupancy" in exported_space["assumptions"]["occupancy"]


def test_scenario_exports_alternative_routes_and_reliability():
    building = BuildingData(id="B1", name="Alternatives")
    building.spaces["S1"] = SpaceData(id="S1", name="Room", area=20)
    exit_a = DoorData(
        id="E1",
        name="Exit A",
        width=1.2,
        height=2.1,
        location=Point3D(x=0),
        is_exit=True,
        connected_spaces=["S1"],
        connection_source="IfcRelSpaceBoundary",
    )
    exit_b = DoorData(
        id="E2",
        name="Exit B",
        width=1.2,
        height=2.1,
        location=Point3D(x=10),
        is_exit=True,
        connected_spaces=["S1"],
        connection_source="IfcRelSpaceBoundary",
    )
    building.doors = {"E1": exit_a, "E2": exit_b}
    building.exits = {"E1": exit_a, "E2": exit_b}

    graph = SpatialGraphBuilder(building)
    assert graph.build()
    scenario = ScenarioGenerator(building, graph).generate(max_scenarios=1)[0]
    payload = scenario.to_dict()

    assert payload["evacuation_route"]["route_reliability"] == "verified"
    assert payload["alternative_routes"]
    assert payload["alternative_routes"][0]["route_reliability"] == "verified"


def test_route_reliability_classification_for_inferred_route():
    from src.bim_processing.spatial_graph import Route

    route = Route(
        origin="S1",
        destination="E1",
        path=["S1", "D1", "E1"],
        distance=10,
        estimated_time=8,
        verified_edge_count=0,
        inferred_edge_count=2,
        route_confidence=0.15,
    )

    assert classify_route_reliability(route) == "insufficient"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
