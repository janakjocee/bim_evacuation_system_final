"""Deployment packaging regression tests for Streamlit multipage entrypoints."""

import json
from pathlib import Path
import subprocess
import sys

from streamlit.testing.v1 import AppTest

import src


def test_deployed_pages_are_self_contained_inside_src():
    repo_root = Path(__file__).resolve().parents[1]
    for page in (
        repo_root / "src/ui/pages/Fire_Scenario_Testing.py",
        repo_root / "src/ui/pages/Worst_Case_Testing.py",
    ):
        source = page.read_text(encoding="utf-8")
        assert "runpy.run_path" not in source
        assert 'REPO_ROOT / "pages"' not in source
        assert "Path(__file__).resolve().parents[3]" in source
        compile(source, str(page), "exec")


def test_legacy_page_entrypoints_delegate_without_errors():
    repo_root = Path(__file__).resolve().parents[1]
    for page in (
        repo_root / "pages/Fire_Scenario_Testing.py",
        repo_root / "pages/🔥_Worst_Case_Testing.py",
    ):
        app = AppTest.from_file(str(page), default_timeout=30).run(timeout=30)
        assert not app.exception, [exception.value for exception in app.exception]


def test_main_page_survives_stale_streamlit_cloud_package(monkeypatch):
    """A hot-deployed worker may retain src from before metadata was added."""
    monkeypatch.delattr(src, "PROJECT_TITLE")
    monkeypatch.delattr(src, "PROJECT_SUBTITLE")

    page = Path(__file__).resolve().parents[1] / "src/ui/streamlit_app.py"
    app = AppTest.from_file(str(page), default_timeout=30).run(timeout=30)

    assert not app.exception, [exception.value for exception in app.exception]
    markup = "\n".join(str(element.value) for element in app.markdown)
    assert "AI-Driven Generation of Evacuation Scenarios" in markup


def test_landing_page_defers_ifc_and_nlp_analysis_imports():
    repo_root = Path(__file__).resolve().parents[1]
    probe = """
import json
import sys
import src.ui.streamlit_app
print(json.dumps({
    "spacy": "spacy" in sys.modules,
    "ifcopenshell": "ifcopenshell" in sys.modules,
    "pipeline": "src.pipeline.evacuation_pipeline" in sys.modules,
    "scenario_generator": "src.scenario.scenario_generator" in sys.modules,
}))
"""
    completed = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    loaded = json.loads(completed.stdout.strip().splitlines()[-1])

    assert loaded == {
        "spacy": False,
        "ifcopenshell": False,
        "pipeline": False,
        "scenario_generator": False,
    }
