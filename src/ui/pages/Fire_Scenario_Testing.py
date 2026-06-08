"""Multipage wrapper for the ASET/RSET Fire Scenario Testing page.

Streamlit discovers pages located beside the entrypoint script. The main app is
run with `streamlit run src/ui/streamlit_app.py`, so this wrapper exposes the
root-level page from `pages/Fire_Scenario_Testing.py` in the sidebar.
"""
from __future__ import annotations

import runpy
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

runpy.run_path(str(REPO_ROOT / "pages" / "Fire_Scenario_Testing.py"), run_name="__main__")
