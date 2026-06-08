"""Indicative life-safety impact estimation.

This module intentionally avoids real casualty prediction. It reports occupants
with viable routes, smoke-route exposure, RSET>ASET exposure and trapped status
as an academic decision-support summary requiring expert validation.
"""
from __future__ import annotations

from typing import Any, Dict, List

FORBIDDEN_WORDS = ["confirmed casualties", "certified casualty prediction", "final legal safety result"]


def _impact_level(trapped: int, exposed: int, total: int) -> str:
    if total <= 0:
        return "low"
    ratio = (trapped + exposed) / total
    if trapped > 0 or ratio >= 0.35:
        return "critical"
    if ratio >= 0.2:
        return "high"
    if ratio > 0:
        return "medium"
    return "low"


def estimate_life_safety_impact(aset_rset_results: List[Dict[str, Any]], smoke_result: Dict[str, Any]) -> Dict[str, Any]:
    smoke_nodes = set(smoke_result.get("final_smoke_affected_nodes", [])) | set(smoke_result.get("final_high_risk_nodes", []))
    rows: List[Dict[str, Any]] = []
    total = viable = smoke_exposure = rset_exceeded = trapped = high_risk = 0

    for row in aset_rset_results:
        occ = int(row.get("occupancy", 0))
        total += occ
        route = row.get("fire_route") or []
        route_smoke = bool(set(route).intersection(smoke_nodes))
        classification = row.get("classification", "requires review")
        margin = row.get("safety_margin_s")

        if classification == "no route / trapped":
            status = "trapped / critical"
            trapped += occ
        elif classification == "unsafe":
            status = "potentially affected occupants"
            rset_exceeded += occ
        elif classification == "reduced margin":
            status = "high risk"
            high_risk += occ
        elif route_smoke:
            status = "smoke-route exposure"
            smoke_exposure += occ
        else:
            status = "viable evacuation route"
            viable += occ

        rows.append({
            "room_id": row.get("room_id"),
            "room_name": row.get("room_name"),
            "occupancy": occ,
            "aset_s": row.get("aset_s"),
            "rset_s": row.get("rset_s"),
            "safety_margin_s": margin,
            "route_status": status,
            "requires_expert_validation": status != "viable evacuation route",
        })

    potentially_affected = smoke_exposure + rset_exceeded + trapped + high_risk
    level = _impact_level(trapped, rset_exceeded + high_risk, total)
    explanation = (
        f"Indicative life-safety impact is {level}. The screening identified {trapped} trapped occupants, "
        f"{rset_exceeded} occupants where RSET exceeds ASET, {high_risk} occupants with reduced safety margin, "
        f"and {smoke_exposure} occupants using smoke-affected routes. These are potentially affected occupants "
        "for expert validation, not real casualty prediction."
    )

    return {
        "total_occupants": total,
        "viable_occupants": viable,
        "smoke_route_exposure_occupants": smoke_exposure,
        "rset_exceeds_aset_occupants": rset_exceeded,
        "trapped_occupants": trapped,
        "high_risk_reduced_margin_occupants": high_risk,
        "potentially_affected_occupants": potentially_affected,
        "overall_indicative_life_safety_impact": level,
        "room_by_room": rows,
        "explanation": explanation,
    }
