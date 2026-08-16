"""
Basic tests for BIM Evacuation System.
"""
import pytest
import hashlib
import io
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.config_loader import ConfigLoader
from src.utils.helpers import RiskLevel, ComplianceStatus, generate_id, sha256_file
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
from src.ui.export_helpers import build_scenarios_csv, build_scenarios_xml, safe_uploaded_filename


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


def test_semantic_graph_connects_storeys_through_geometry_inferred_stair():
    building = BuildingData(id="B1", name="Two Storey Test")
    building.spaces["GROUND"] = SpaceData(
        id="GROUND",
        name="Ground Lobby",
        area=20,
        bounding_box=(Point3D(0, 0, 0), Point3D(4, 4, 3)),
    )
    building.spaces["UPPER"] = SpaceData(
        id="UPPER",
        name="Upper Lobby",
        area=20,
        bounding_box=(Point3D(0, 0, 3), Point3D(4, 4, 6)),
    )
    building.stairs["STAIR1"] = StairData(
        id="STAIR1",
        name="Main Stair",
        width=1.2,
        riser_height=0.17,
        tread_length=0.25,
        connected_spaces=["GROUND", "UPPER"],
        bounding_box=(Point3D(1, 1, 0), Point3D(3, 3, 6)),
        connection_source="inferred_stair_geometry",
    )
    exit_door = DoorData(
        id="EXIT",
        name="Final Exit",
        width=1.2,
        height=2.1,
        location=Point3D(0, 2, 0),
        is_exit=True,
        connected_spaces=["GROUND"],
    )
    building.doors = {"EXIT": exit_door}
    building.exits = {"EXIT": exit_door}

    graph = SpatialGraphBuilder(building)
    assert graph.build()
    route = graph.find_shortest_path("UPPER", "EXIT")

    assert route is not None
    assert route.path == ["UPPER", "STAIR1", "GROUND", "EXIT"]
    assert route.inferred_edge_count == 2


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

    assert payload["screening_index"] >= 0
    assert payload["screening_priority"] == payload["risk_level"]
    assert payload["risk_score"] == payload["screening_index"]
    assert payload["implemented_checks_passed"] == payload["compliance_score"]
    assert payload["evidence_confidence"] == payload["confidence_score"]
    assert payload["score_semantics"]["direction"] == "higher_is_lower_screening_priority"
    assert payload["risk_factors"]["weighted_breakdown"]["screening_index"] == payload["screening_index"]
    assert payload["assumption_registry"]["calibration_status"] == "unvalidated_research_assumption"
    assert payload["decision_trace"]
    assert payload["decision_trace"][-1]["method"] == "Weighted deterministic score, not an opaque machine-learning prediction."
    assert payload["data_quality_notes"]
    assert payload["evacuation_route"]["inferred_edge_count"] == 1
    assert payload["compliance_status"] == ComplianceStatus.REQUIRES_REVIEW.value


def test_evidence_confidence_is_independent_from_compliance_outcome():
    building = BuildingData(id="B1", name="Evidence Confidence Test")
    building.spaces["S1"] = SpaceData(id="S1", name="Room A", area=20)
    exit_door = DoorData(
        id="E1",
        name="Verified Exit",
        width=0.5,
        height=2.1,
        location=Point3D(),
        is_exit=True,
        connected_spaces=["S1"],
        connection_source="IfcRelSpaceBoundary",
    )
    building.doors = {"E1": exit_door}
    building.exits = {"E1": exit_door}
    graph = SpatialGraphBuilder(building)
    assert graph.build()

    scenario = ScenarioGenerator(building, graph).generate(max_scenarios=1)[0]

    assert scenario.compliance_score < 1.0
    assert scenario.confidence_score == 1.0
    assert scenario.compliance_status == ComplianceStatus.REQUIRES_REVIEW
    checks = scenario.decision_trace[2]["output"]["checks"]
    exit_width = next(check for check in checks if check["regulation_id"] == "min_exit_width")
    assert exit_width["status"] == ComplianceStatus.NON_COMPLIANT.value


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


def test_parser_normalizes_length_units_to_metres():
    parser = RegulationParser()
    parser.parse(
        "2.1 Exit width\n"
        "Final exit doors shall have a minimum clear opening width of 1050mm."
    )

    rule = next(item for item in parser.rules if item.metric == "min_exit_width")

    assert rule.value == 1.05
    assert rule.unit == "m"


def test_parser_distinguishes_alternative_escape_from_one_direction():
    parser = RegulationParser()
    parser.parse(
        "2.1 Travel distance\n"
        "Maximum travel distance in one direction is 18 metres. "
        "Maximum travel distance in more than one direction is 45 metres."
    )

    values = {(item.metric, item.value) for item in parser.rules}
    conditions = {item.metric: item.condition for item in parser.rules}

    assert ("max_single_direction_travel_distance", 18.0) in values
    assert ("max_alternative_travel_distance", 45.0) in values
    assert conditions["max_single_direction_travel_distance"] == "single_direction_escape"
    assert conditions["max_alternative_travel_distance"] == "alternative_escape"


def test_direct_and_small_premises_distances_are_not_global_route_thresholds():
    parser = RegulationParser()
    clauses = parser.parse(
        "2.1 Scoped distances\n"
        "Direct distance should be no more than 12 metres for one-direction travel. "
        "Small premises maximum travel distance with one exit is 27 metres."
    )
    checker = ComplianceChecker()
    checker.update_regulation_rules(parser.rules)
    summary = checker.get_rule_application_summary()

    assert clauses
    assert summary["active_uploaded_threshold_count"] == 0
    assert summary["unsupported_rule_count"] == 2
    assert checker.check_route(SpaceData(id="S1", name="Room", area=10), 30.0)[0].required_value == 45.0


def test_parser_does_not_inherit_exit_metric_for_unrelated_measurement():
    parser = RegulationParser()
    parser.parse(
        "2.1 Exit widths\n"
        "Final exit doors shall have a minimum clear opening width of 1050mm.\n"
        "External walls should be 1000mm or more from the relevant boundary."
    )

    exit_rules = [rule for rule in parser.rules if rule.metric == "min_exit_width"]

    assert [rule.value for rule in exit_rules] == [1.05]


def test_parser_does_not_apply_per_person_formula_as_fixed_width():
    parser = RegulationParser()
    parser.parse(
        "2.2 Exit capacity\n"
        "For more than 220 occupants, the minimum exit width is 5 mm per person."
    )

    assert not [rule for rule in parser.rules if rule.metric == "min_exit_width"]


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


def test_uploaded_rule_candidates_use_conservative_selection():
    checker = ComplianceChecker()
    checker.update_regulation_rules([
        RegulationRule(
            rule_id="A",
            source_section="A",
            source_text="Travel distance must not exceed 45 metres.",
            applies_to="route",
            condition="general",
            metric="max_travel_distance",
            operator="<=",
            value=45.0,
            unit="metres",
        ),
        RegulationRule(
            rule_id="B",
            source_section="B",
            source_text="Travel distance must not exceed 30 metres.",
            applies_to="route",
            condition="general",
            metric="max_travel_distance",
            operator="<=",
            value=30.0,
            unit="metres",
        ),
    ])

    summary = checker.get_rule_application_summary()
    selected = next(item for item in summary["active_thresholds"] if item["rule_key"] == "max_travel_distance")

    assert selected["value"] == 30.0
    assert selected["candidate_count"] == 2
    assert selected["selection_strategy"] == "conservative uploaded candidate"


def test_non_evacuation_distances_and_specialist_stairs_are_not_activated():
    parser = RegulationParser()
    parser.parse(
        """
16.3 A dry fire main outlet should have a maximum hose distance of 45 metres.

3.22 At least one stair needs to be a firefighting stair, therefore a minimum width of 1100mm.

3.23 The minimum exit width needed for 240 people is 1200mm.
"""
    )

    metrics = {rule.metric: rule for rule in parser.rules}
    assert metrics["max_fire_hose_distance"].value == 45.0
    assert metrics["min_firefighting_stair_width"].value == 1.1
    assert metrics["min_exit_width"].condition == "occupants_context:240"

    checker = ComplianceChecker()
    checker.update_regulation_rules(parser.rules)
    summary = checker.get_rule_application_summary()
    assert summary["unsupported_rule_count"] == 2
    assert checker.regulations["max_travel_distance"] == checker.default_regulations["max_travel_distance"]
    assert checker.regulations["min_stair_width"] == checker.default_regulations["min_stair_width"]
    assert checker.regulations["min_exit_width"] == 1.2


def test_route_check_uses_single_and_alternative_escape_thresholds():
    checker = ComplianceChecker()
    checker.update_regulation_rules([
        RegulationRule(
            rule_id="SINGLE",
            source_section="T",
            source_text="Single direction travel must not exceed 18 metres.",
            applies_to="route",
            condition="single_direction_escape",
            metric="max_single_direction_travel_distance",
            operator="<=",
            value=18.0,
            unit="metres",
        ),
        RegulationRule(
            rule_id="ALT",
            source_section="T",
            source_text="Alternative travel must not exceed 45 metres.",
            applies_to="route",
            condition="alternative_escape",
            metric="max_alternative_travel_distance",
            operator="<=",
            value=45.0,
            unit="metres",
        ),
    ])
    space = SpaceData(id="S1", name="Room", area=10)

    assert checker.check_route(space, 30.0, route_count=1)[0].status == ComplianceStatus.NON_COMPLIANT
    assert checker.check_route(space, 30.0, route_count=2)[0].status == ComplianceStatus.COMPLIANT


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
    assert summary["supported_uploaded_rule_candidate_count"] == 1
    assert summary["active_uploaded_threshold_count"] == 1
    assert summary["extracted_uploaded_rule_count"] == 2
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


def test_regulation_text_loader_supports_txt(tmp_path):
    txt_path = tmp_path / "rules.txt"
    txt_path.write_text("Travel distance must not exceed 30 metres.", encoding="utf-8")
    assert "30 metres" in extract_regulation_text(txt_path)


def test_regulation_text_loader_supports_docx(tmp_path):
    import docx

    docx_path = tmp_path / "rules.docx"
    document = docx.Document()
    document.add_paragraph("Final exit doors shall be 1200mm wide.")
    document.save(docx_path)
    assert "1200mm" in extract_regulation_text(docx_path)


def test_regulation_text_loader_supports_pdf(tmp_path):
    from pypdf import PdfWriter
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

    pdf_path = tmp_path / "rules.pdf"
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject({
        NameObject("/Type"): NameObject("/Font"),
        NameObject("/Subtype"): NameObject("/Type1"),
        NameObject("/BaseFont"): NameObject("/Helvetica"),
    })
    font_ref = writer._add_object(font)
    page[NameObject("/Resources")] = DictionaryObject({
        NameObject("/Font"): DictionaryObject({NameObject("/F1"): font_ref})
    })
    content = DecodedStreamObject()
    content.set_data(
        b"BT /F1 12 Tf 72 720 Td (Corridor width shall be at least 1200mm.) Tj ET"
    )
    page[NameObject("/Contents")] = writer._add_object(content)
    with pdf_path.open("wb") as handle:
        writer.write(handle)

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
                {
                    "rule_key": "min_exit_width",
                    "value": 1.1,
                    "source": "uploaded_regulation_rule",
                    "rule_id": "UPLOADED-EXIT",
                    "source_text": "Final exits shall have a minimum width of 1.1 metres.",
                },
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
    checks = corrected.scenarios[0].decision_trace[2]["output"]["checks"]
    exit_width_check = next(check for check in checks if check["regulation_id"] == "min_exit_width")
    assert exit_width_check["evidence_source"] == "uploaded_regulation_rule"


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
        regulation_document={
            "name": "approved_document_b.pdf",
            "sha256": "b" * 64,
            "source_url": "https://www.gov.uk/government/publications/fire-safety-approved-document-b",
            "metadata_scope": "user_declared_not_legally_validated",
        },
    )

    exported = EvacuationPipeline().export_results(result, str(tmp_path), formats=["json", "csv"])

    assert Path(exported["json"]).exists()
    assert Path(exported["csv"]).exists()
    exported_json = json.loads(Path(exported["json"]).read_text())
    assert exported_json["source_file_name"] == "synthetic.ifc"
    assert exported_json["regulation_document"]["name"] == "approved_document_b.pdf"
    assert scenarios[0].scenario_id in Path(exported["csv"]).read_text()


def test_streaming_file_hash_matches_reference_digest(tmp_path):
    payload = (b"large-model-chunk" * 100_000) + b"end"
    source = tmp_path / "model.ifc"
    source.write_bytes(payload)

    assert sha256_file(source, chunk_size=4096) == hashlib.sha256(payload).hexdigest()


def test_uploaded_file_save_preserves_payload_without_bytes_copy(tmp_path):
    from src.ui.streamlit_app import save_uploaded_file

    class Upload(io.BytesIO):
        name = "large model.ifczip"

    payload = b"compressed-ifc-payload"
    saved = Path(save_uploaded_file(Upload(payload), str(tmp_path)))

    assert saved.suffix == ".ifczip"
    assert saved.read_bytes() == payload


def test_ui_export_helpers_produce_safe_names_and_well_formed_outputs():
    building = BuildingData(id="B1", name="Clinic & Lab <North>")
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
    scenarios[0].name = "Scenario <A&B>"
    result = PipelineResult(success=True, building=building, scenarios=scenarios)

    xml_text = build_scenarios_xml(result, "2026-08-08T14:00:00")
    xml_root = ET.fromstring(xml_text)
    csv_text = build_scenarios_csv(scenarios)

    assert xml_root.find("Building").attrib["name"] == building.name
    assert xml_root.find("./Scenarios/Scenario/Name").text == scenarios[0].name
    assert xml_root.find("ScoreSemantics").attrib["direction"] == "higher_is_lower_screening_priority"
    assert xml_root.find("./Scenarios/Scenario/ScreeningIndex") is not None
    assert scenarios[0].scenario_id in csv_text
    assert "screening_index" in csv_text
    assert "screening_priority" in csv_text
    assert "implemented_checks_passed" in csv_text
    assert "evidence_confidence" in csv_text
    assert "score_direction" in csv_text
    assert safe_uploaded_filename("../../unsafe/model.ifc") == "model.ifc"
    assert safe_uploaded_filename(r"C:\\uploads\\model.ifc") == "model.ifc"


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
