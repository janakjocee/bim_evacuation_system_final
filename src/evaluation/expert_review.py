"""Structured records for bounded, preliminary domain review."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, Optional, Union


RATING_FIELDS = {
    "ifc_evidence_clarity": "IFC evidence clarity",
    "route_result_relevance": "Route result relevance",
    "regulation_trace_clarity": "Regulation trace clarity",
    "fire_model_limitations_clarity": "Fire-model limitations clarity",
    "overall_early_screening_usefulness": "Early-screening usefulness",
}


def _lines(value: Optional[Union[str, Iterable[str]]]) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        values = value.replace(";", "\n").splitlines()
    else:
        values = [str(item) for item in value]
    return [item.strip() for item in values if item.strip()]


def _rating(value: Any) -> int | None:
    if value in {None, "", "Not rated"}:
        return None
    rating = int(value)
    if rating not in range(1, 6):
        raise ValueError("Review ratings must be integers from 1 to 5")
    return rating


def build_preliminary_domain_review(
    *,
    source_file_sha256: str,
    ifc_schema: str,
    ethics_confirmation_reference: str,
    reviewer_competence_scope: str,
    cases_reviewed: Iterable[str],
    ratings: Mapping[str, Any],
    safety_critical_findings: Optional[Union[str, Iterable[str]]] = None,
    other_findings: Optional[Union[str, Iterable[str]]] = None,
    required_corrections: Optional[Union[str, Iterable[str]]] = None,
    reviewer_signoff_reference: str = "",
    project_author_disposition: Optional[Union[str, Iterable[str]]] = None,
    review_date: Optional[str] = None,
) -> dict[str, Any]:
    """Build a review record without treating self-entered data as validation."""
    normalised_ratings = {
        field: _rating(ratings.get(field))
        for field in RATING_FIELDS
    }
    cases = _lines(cases_reviewed)
    safety_findings = _lines(safety_critical_findings)
    corrections = _lines(required_corrections)
    dispositions = _lines(project_author_disposition)

    missing_fields = []
    required_text = {
        "ethics_confirmation_reference": ethics_confirmation_reference,
        "reviewer_competence_scope": reviewer_competence_scope,
        "reviewer_signoff_reference": reviewer_signoff_reference,
    }
    missing_fields.extend(
        field for field, value in required_text.items() if not str(value).strip()
    )
    if not cases:
        missing_fields.append("cases_reviewed")
    missing_fields.extend(
        f"ratings.{field}"
        for field, value in normalised_ratings.items()
        if value is None
    )
    if (safety_findings or corrections) and not dispositions:
        missing_fields.append("project_author_disposition")

    if not ethics_confirmation_reference.strip():
        status = "blocked_missing_ethics_or_supervisor_confirmation"
    elif missing_fields:
        status = "incomplete_preliminary_review"
    elif safety_findings or corrections:
        status = "preliminary_review_recorded_with_findings"
    else:
        status = "preliminary_review_recorded"

    return {
        "protocol_version": 2,
        "execution_status": status,
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "review_date": (review_date or "").strip(),
        "source_file_sha256": source_file_sha256,
        "ifc_schema": ifc_schema,
        "ethics_or_supervisor_confirmation_reference": ethics_confirmation_reference.strip(),
        "reviewer_competence_scope": reviewer_competence_scope.strip(),
        "cases_reviewed": cases,
        "ratings": normalised_ratings,
        "safety_critical_findings": safety_findings,
        "other_findings": _lines(other_findings),
        "required_corrections": corrections,
        "reviewer_signoff_or_consent_reference": reviewer_signoff_reference.strip(),
        "project_author_disposition": dispositions,
        "missing_fields": sorted(set(missing_fields)),
        "software_assurance": {
            "reviewer_identity_verified_by_software": False,
            "reviewer_qualification_verified_by_software": False,
            "professional_validation_claim_allowed_automatically": False,
            "scope": "preliminary_one-reviewer_evidence_not_generalizable_validation",
        },
    }
