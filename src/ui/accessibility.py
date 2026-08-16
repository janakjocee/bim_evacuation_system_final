"""Accessibility checks and structured manual-audit records."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Mapping, Optional


THEME_PAIRS = {
    "light_text": ("#172033", "#ffffff"),
    "light_muted": ("#526071", "#ffffff"),
    "light_info": ("#172033", "#e8f3ff"),
    "light_warning": ("#172033", "#fff6db"),
    "light_danger": ("#172033", "#ffe9ec"),
    "light_success": ("#172033", "#e7f6ed"),
    "light_primary_button": ("#ffffff", "#0B5F6B"),
    "light_status_pass": ("#147A50", "#ffffff"),
    "light_status_fail": ("#b42318", "#ffffff"),
    "light_status_warn": ("#8A4B08", "#ffffff"),
    "risk_low_badge": ("#ffffff", "#147A50"),
    "risk_medium_badge": ("#ffffff", "#8A4B08"),
    "risk_high_badge": ("#ffffff", "#B42318"),
    "review_badge": ("#ffffff", "#0E7490"),
    "insufficient_badge": ("#ffffff", "#6941C6"),
    "dark_text": ("#F3F6FA", "#182230"),
    "dark_muted": ("#B8C5D4", "#182230"),
    "dark_info": ("#F3F6FA", "#153653"),
    "dark_warning": ("#F3F6FA", "#4a3c13"),
    "dark_danger": ("#F3F6FA", "#4a2028"),
    "dark_success": ("#F3F6FA", "#153d2b"),
}

MANUAL_ACCESSIBILITY_CHECKS = {
    "keyboard_traversal": "Keyboard-only traversal and logical focus order",
    "focus_visibility": "Visible focus indicators in light and dark modes",
    "zoom_200_percent": "Usable layout at 200% browser zoom",
    "screen_reader_names": "Understandable screen-reader control names",
    "chart_text_equivalents": "Text equivalents adjacent to route and 3D charts",
    "message_semantics": "Status messages do not rely on colour alone",
    "mobile_width": "No hidden critical controls at a mobile-width viewport",
}

MANUAL_OUTCOMES = {"not_tested", "pass", "fail", "not_applicable"}


def _rgb(hex_colour: str) -> tuple[float, float, float]:
    value = hex_colour.lstrip("#")
    if len(value) != 6:
        raise ValueError(f"Expected six-digit hex colour, got {hex_colour}")
    return tuple(int(value[index:index + 2], 16) / 255 for index in (0, 2, 4))


def relative_luminance(hex_colour: str) -> float:
    channels = []
    for channel in _rgb(hex_colour):
        channels.append(channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4)
    red, green, blue = channels
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast_ratio(foreground: str, background: str) -> float:
    first = relative_luminance(foreground)
    second = relative_luminance(background)
    lighter, darker = max(first, second), min(first, second)
    return (lighter + 0.05) / (darker + 0.05)


def palette_contrast_report() -> dict[str, float]:
    return {
        name: round(contrast_ratio(foreground, background), 2)
        for name, (foreground, background) in THEME_PAIRS.items()
    }


def build_manual_accessibility_record(
    *,
    browser: str,
    operating_system: str,
    outcomes: Mapping[str, str],
    notes: str = "",
    evidence_reference: str = "",
    tested_at: Optional[str] = None,
) -> dict:
    """Build a transparent manual-check record without claiming WCAG conformance."""
    normalised = {}
    for check in MANUAL_ACCESSIBILITY_CHECKS:
        outcome = str(outcomes.get(check, "not_tested")).strip().lower().replace(" ", "_")
        if outcome not in MANUAL_OUTCOMES:
            raise ValueError(f"Unsupported accessibility outcome for {check}: {outcome}")
        normalised[check] = outcome

    tested = [value for value in normalised.values() if value != "not_tested"]
    passes = [value for value in normalised.values() if value == "pass"]
    failures = [check for check, value in normalised.items() if value == "fail"]
    required = [value for value in normalised.values() if value != "not_applicable"]
    missing_metadata = [
        field
        for field, value in {
            "browser": browser,
            "operating_system": operating_system,
            "evidence_reference": evidence_reference,
        }.items()
        if not value.strip()
    ]

    if not tested:
        status = "not_executed"
    elif failures:
        status = "executed_issues_found"
    elif not passes:
        status = "executed_incomplete"
    elif "not_tested" in required or missing_metadata:
        status = "executed_incomplete"
    else:
        status = "completed_author_accessibility_check"

    return {
        "audit_version": 1,
        "execution_status": status,
        "tested_at": tested_at or datetime.now(timezone.utc).isoformat(),
        "browser": browser.strip(),
        "operating_system": operating_system.strip(),
        "outcomes": normalised,
        "failed_checks": failures,
        "missing_metadata": missing_metadata,
        "notes": notes.strip(),
        "evidence_reference": evidence_reference.strip(),
        "wcag_conformance_claim_allowed": False,
        "scope": "bounded_manual_project_author_check_not_wcag_certification",
    }
