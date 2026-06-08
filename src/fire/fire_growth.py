"""Simplified t-squared fire growth model.

The model uses HRR(t) = alpha * t^2 as an explainable screening approximation.
It is intended for early-stage ASET/RSET scenario exploration, not certified fire
engineering or CFD simulation.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


DEFAULT_ALPHA = {
    "slow": 0.0029,
    "medium": 0.0117,
    "fast": 0.0469,
    "ultra_fast": 0.1876,
}


@dataclass
class FireGrowthConfig:
    fire_origin: str
    room_type: str = "unknown"
    fire_growth_class: str = "medium"
    simulation_duration_seconds: int = 360
    time_step_seconds: int = 30
    suppression_enabled: bool = False
    sprinkler_activation_time_seconds: int = 180
    ventilation_factor: float = 1.0
    max_hrr_kw: float = 5000.0
    suppression_reduction_factor: float = 0.45


def classify_intensity(hrr_kw: float) -> str:
    if hrr_kw < 250:
        return "low"
    if hrr_kw < 1000:
        return "moderate"
    if hrr_kw < 2500:
        return "severe"
    return "critical"


def simulate_fire_growth(config: FireGrowthConfig | Dict[str, Any]) -> Dict[str, Any]:
    """Return HRR time series, peak HRR and intensity classes."""
    if isinstance(config, dict):
        config = FireGrowthConfig(**config)

    growth_class = config.fire_growth_class.lower().strip()
    alpha = DEFAULT_ALPHA.get(growth_class, DEFAULT_ALPHA["medium"])
    step = max(1, int(config.time_step_seconds))
    duration = max(step, int(config.simulation_duration_seconds))
    max_hrr = max(0.0, float(config.max_hrr_kw))
    ventilation_factor = max(0.1, float(config.ventilation_factor))

    series: List[Dict[str, Any]] = []
    for t in range(0, duration + step, step):
        hrr = alpha * (t ** 2) * ventilation_factor
        if config.suppression_enabled and t >= int(config.sprinkler_activation_time_seconds):
            # Simplified suppression representation: after activation, cap and reduce HRR.
            hrr = min(hrr, alpha * (config.sprinkler_activation_time_seconds ** 2) * ventilation_factor)
            hrr *= max(0.0, min(1.0, config.suppression_reduction_factor))
        hrr = min(hrr, max_hrr)
        series.append({
            "time_s": t,
            "hrr_kw": round(hrr, 3),
            "intensity": classify_intensity(hrr),
        })

    peak = max((row["hrr_kw"] for row in series), default=0.0)
    explanation = (
        f"A simplified t-squared fire growth curve was generated for {config.fire_origin} "
        f"using the {growth_class} growth class. HRR is capped at {max_hrr:.0f} kW. "
        "This is an indicative screening approximation and not a CFD fire model."
    )
    if config.suppression_enabled:
        explanation += (
            f" Suppression is modelled as a simplified HRR reduction after "
            f"{config.sprinkler_activation_time_seconds}s."
        )

    return {
        "fire_origin": config.fire_origin,
        "room_type": config.room_type,
        "growth_class": growth_class,
        "alpha": alpha,
        "time_series": series,
        "peak_hrr_kw": round(peak, 3),
        "peak_intensity": classify_intensity(peak),
        "explanation": explanation,
    }
