# Submission Claim Boundary and Assumption Register

## Defensible project description

This project is a deterministic BIM and NLP-assisted research screening prototype.
It extracts evidence from an uploaded IFC, builds a traceable graph, applies a
limited set of configurable checks, generates review candidates and records a
session-scoped human review disposition.

It does not determine that a building is safe, issue statutory compliance,
authenticate a fire engineer, run CFD, provide certified evacuation modelling or
predict casualties.

## Score semantics

| Output | Direction | Meaning | Validation status |
|---|---|---|---|
| Standard screening index | Higher is lower screening priority | Weighted prototype prioritisation from implemented checks, capacity, time, bottlenecks and evidence quality | Uncalibrated research assumption |
| Standard screening-priority level | Low / Medium / High | Review priority derived from the screening index and evidence caps | Uncalibrated research assumption |
| Fire hazard-priority score | Higher is higher screening priority | Researcher-defined points for trapped occupants, model ASET/RSET findings, affected exits, rerouting and smoke-route exposure | Uncalibrated research assumption |
| Worst-case hazard-priority score | Higher is higher screening priority | Researcher-defined points for blocked routes, remaining exits, distance, occupancy, delay, smoke and bottlenecks | Uncalibrated research assumption |

The legacy JSON field `risk_score` remains for compatibility. In standard
evacuation scenarios it is a deprecated alias of `screening_index`; each export
states its direction.

## Core assumptions

The machine-readable source of truth is `config/settings.yaml` plus the
`assumption_registry` exported for each run.

| Assumption | Current default | Purpose |
|---|---:|---|
| Level walking speed | 1.2 m/s | Route travel-time estimate |
| Exit flow rate | 90 persons/min/m | Comparative exit-capacity indicator |
| Standard time reference | 300 s | Normalises one screening-index component; it is not ASET |
| Default door width | 0.9 m | Fallback when IFC width is unavailable |
| Default space area | 20 m2 | Fallback when IFC area/geometry is unavailable |
| Detection / alarm / pre-movement | Per dataset or run controls | Assumption-based RSET components |
| Smoke reach factors | Internal graph heuristics | Graph hazard propagation; not physical smoke modelling |

All assumption records carry `calibration_status:
unvalidated_research_assumption`.

## IFC interpretation

- Semantic IFC mode uses IfcSpace/IfcDoor evidence and verified relationships
  where available.
- Semantic-spaces/inferred-topology mode uses real IfcSpace geometry but infers
  route links or egress points.
- Geometry-derived mode uses real uploaded IFC elements as exploratory proxy
  nodes. It does not invent a hidden building dataset, but the nodes are not
  verified rooms and all edges are inferred.
- Schema readability does not prove evacuation suitability.

## Regulation interpretation

TXT, Markdown, PDF and DOCX text can be parsed. Only supported numeric rules are
mapped into active prototype checks. Unsupported clauses remain visible and are
not silently treated as enforced. Uploaded rules still require a qualified person
to confirm scope, conditions, edition and applicability.

## Verification versus validation

Automated tests verify that the software behaves according to its implemented
logic. The multi-IFC compatibility matrix verifies parsing and diagnostic
behaviour across the available corpus. Neither activity validates the heuristic
weights, smoke propagation, occupancy assumptions, tenability, legal compliance
or professional usefulness. Those require calibrated data, controlled studies and
qualified external review.

## Review and export governance

The UI review record is session-scoped and explicitly requires acknowledgement
that it is not professional approval or statutory sign-off. The complete JSON
evidence report contains source provenance, readiness, graph diagnostics,
regulation application, assumptions, score semantics, scenarios, errors and
research review records. CSV and XML exports are summary-only and are labelled as
such in the UI.
