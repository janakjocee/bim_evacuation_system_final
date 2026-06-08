"""Deployment packaging regression tests for Streamlit multipage entrypoints."""

from pathlib import Path


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
