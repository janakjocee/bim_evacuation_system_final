"""Fire-safety-inspired scenario modelling package.

This package implements an academic decision-support layer for the BIM evacuation
prototype. It provides simplified t-squared fire growth, graph-based smoke spread,
ASET/RSET-inspired screening, indicative life-safety impact estimation and export
helpers. It is not CFD, certified evacuation modelling or final fire-safety approval.
"""

from .fire_growth import FireGrowthConfig, simulate_fire_growth
from .smoke_spread import SmokeSpreadConfig, simulate_smoke_spread
from .aset_rset import AsetRsetConfig, calculate_aset_rset
from .life_safety_impact import estimate_life_safety_impact
from .fire_scenario_engine import FireScenarioEngine

__all__ = [
    "FireGrowthConfig",
    "simulate_fire_growth",
    "SmokeSpreadConfig",
    "simulate_smoke_spread",
    "AsetRsetConfig",
    "calculate_aset_rset",
    "estimate_life_safety_impact",
    "FireScenarioEngine",
]
