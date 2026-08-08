"""Backward-compatible entry point for the canonical worst-case page."""
from pathlib import Path
import runpy


REPO_ROOT = Path(__file__).resolve().parents[1]
runpy.run_path(
    str(REPO_ROOT / "src" / "ui" / "pages" / "Worst_Case_Testing.py"),
    run_name="__main__",
)
