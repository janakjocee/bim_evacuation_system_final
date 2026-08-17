"""Regression tests for geometry-only IFC compatibility behavior."""

import os
from pathlib import Path
from zipfile import ZipFile

import pytest

from src.pipeline.evacuation_pipeline import EvacuationPipeline
from src.bim_processing.ifc_archive import (
    IFCArchiveError,
    MAX_IFCZIP_UNCOMPRESSED_BYTES,
    validate_ifczip,
)
from scripts.generate_controlled_ifc import build_controlled_ifc
from scripts.validate_ifcs import discover_ifcs
from scripts.verify_practical_workflow import verify


IFC_PATH = Path(os.environ.get(
    "BIM_TEST_IFC",
    Path(__file__).parent / "fixtures" / "11134_V_Motebello_Heistopp_Rev.ifc",
))
requires_optional_ifc = pytest.mark.skipif(
    not IFC_PATH.exists(),
    reason="Optional IFC regression fixture is not included in this checkout",
)


@requires_optional_ifc
def test_geometry_only_ifc_uses_file_geometry():
    result = EvacuationPipeline().run(str(IFC_PATH), max_scenarios=3)

    assert result.success
    assert result.source_mode == "geometry_derived"
    assert result.building.name == "Villa Montebello"
    assert len(result.scenarios) == 3
    assert result.readiness["critical_issues"]
    assert result.readiness["processing_readiness_score"] == 100
    assert result.readiness["engineering_evidence_score"] < 50
    assert all(scenario.name.startswith("Exploratory geometry route") for scenario in result.scenarios)
    assert all(not scenario.origin_space_name.startswith("Office") for scenario in result.scenarios)


@requires_optional_ifc
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


@requires_optional_ifc
def test_practical_verifier_reconciles_real_ifc_exports(tmp_path):
    report = verify(IFC_PATH, None, tmp_path / "verification", max_scenarios=4)

    assert report["operational_verdict"] == "PASS_WITH_REVIEW_LIMITATIONS"
    assert report["pipeline"]["scenario_count"] == 4
    assert all(gate["status"] == "PASS" for gate in report["gates"])
    assert (tmp_path / "verification" / "verification_report.json").exists()
    assert (tmp_path / "verification" / "verification_report.md").exists()


def test_git_lfs_pointer_upload_gets_clear_error(tmp_path):
    pointer = tmp_path / "model.ifc"
    pointer.write_text(
        "version https://git-lfs.github.com/spec/v1\n"
        "oid sha256:abc123\n"
        "size 12345\n"
    )

    result = EvacuationPipeline().run(str(pointer), max_scenarios=1)

    assert not result.success
    assert "Git LFS pointer" in result.errors[0]


def test_ifczip_runs_the_same_real_ifc_pipeline(tmp_path):
    ifc_path = build_controlled_ifc(tmp_path / "controlled.ifc")
    archive_path = tmp_path / "controlled.ifczip"
    with ZipFile(archive_path, "w") as archive:
        archive.write(ifc_path, arcname=ifc_path.name)

    archive = validate_ifczip(archive_path)
    result = EvacuationPipeline().run(str(archive_path), max_scenarios=3, enable_rag=False)

    assert archive["model_name"] == "controlled.ifc"
    assert archive["uncompressed_bytes"] > 0
    assert result.success
    assert result.ifc_schema == "IFC4"
    assert result.source_file_name == "controlled.ifczip"
    assert len(result.source_file_sha256) == 64
    assert len(result.scenarios) == 3
    assert discover_ifcs([str(tmp_path)]) == [ifc_path.resolve(), archive_path.resolve()]


def test_practical_verifier_reports_context_deferred_regulation_rules(tmp_path):
    ifc_path = build_controlled_ifc(tmp_path / "controlled.ifc")
    regulations = tmp_path / "regulations.txt"
    regulations.write_text(
        "2.1 Travel distance must not exceed 30 metres.\n"
        "2.2 The minimum exit width needed for 240 people is 1200mm.\n",
        encoding="utf-8",
    )

    report = verify(ifc_path, regulations, tmp_path / "verification", max_scenarios=2)

    assert report["regulations"]["active_uploaded_threshold_count"] == 1
    assert report["regulations"]["context_deferred_rule_count"] == 1
    deferred = report["regulations"]["context_deferred_rules"][0]
    assert deferred["metric"] == "min_exit_width"
    assert deferred["condition"] == "occupants_context:240"


def test_ifczip_uncompressed_payload_uses_streamlit_200_mb_limit():
    assert MAX_IFCZIP_UNCOMPRESSED_BYTES == 200 * 1024 * 1024


def test_ifczip_rejects_payload_above_uncompressed_limit(tmp_path, monkeypatch):
    archive_path = tmp_path / "oversized.ifczip"
    with ZipFile(archive_path, "w") as archive:
        archive.writestr("model.ifc", "ISO-10303-21;")

    monkeypatch.setattr(
        "src.bim_processing.ifc_archive.MAX_IFCZIP_UNCOMPRESSED_BYTES",
        4,
    )
    with pytest.raises(IFCArchiveError, match="exceeds the 200 MB"):
        validate_ifczip(archive_path)


def test_ifczip_rejects_multiple_payloads_and_reports_pipeline_error(tmp_path):
    archive_path = tmp_path / "ambiguous.ifczip"
    with ZipFile(archive_path, "w") as archive:
        archive.writestr("first.ifc", "ISO-10303-21;")
        archive.writestr("second.ifc", "ISO-10303-21;")

    with pytest.raises(IFCArchiveError, match="exactly one"):
        validate_ifczip(archive_path)

    result = EvacuationPipeline().run(str(archive_path), max_scenarios=1)
    assert not result.success
    assert "exactly one IFC model" in result.errors[0]
