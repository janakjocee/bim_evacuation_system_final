"""Multipage wrapper for Fire-Origin Worst-Case Scenario Testing.

Streamlit discovers pages located beside the entrypoint script. The main app is
run with `streamlit run src/ui/streamlit_app.py`, so this wrapper exposes the
root-level page from `pages/🔥_Worst_Case_Testing.py` in the sidebar without
requiring an emoji filename in the discovered page path.
"""
from __future__ import annotations

import runpy
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

runpy.run_path(str(REPO_ROOT / "pages" / "🔥_Worst_Case_Testing.py"), run_name="__main__")
