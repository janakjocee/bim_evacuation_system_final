# Submission Readiness Reverification

Verification date: 16 August 2026

## Decision

The repository is operationally ready for an academic prototype demonstration.
It is not a validated fire-engineering tool, a legal compliance checker, CFD,
or a certified evacuation simulator. The current report PDF is not ready to
submit until its visible comments/markup, placeholders and overclaims are
corrected; see `docs/proposal_report_alignment_20260816.md`.

The merged GitHub workflow is green. The hosted Streamlit URL is
authentication-gated: unauthenticated requests to both `/` and
`/_stcore/health` redirect to Streamlit login. Treat this as a demo-access
condition, not evidence of public availability; sign in before the review and
keep the local run command available as a fallback.

## Automated Verification

The complete local suite was run with the real Montebello IFC enabled:

```bash
BIM_TEST_IFC="/Users/janakjocee/Downloads/11134_V_Motebello_Heistopp_Rev.ifc" \
  python3 -m pytest -q -rs
```

Result: **104 passed, 0 failed, 0 skipped**.

Measured line coverage: **79.1%** (3,831 of 4,841 statements). Coverage is a
software-test measure; it is not evidence of fire-engineering correctness.

Coverage includes:

- IFC parsing, validation, semantic and geometry-derived topology;
- TXT, PDF and DOCX regulation extraction;
- structured rule parsing and threshold provenance;
- scenario generation, score direction and evidence confidence;
- scenario View Details open, close and reopen;
- manual IFC corrections and scenario regeneration;
- JSON, CSV, XML, fire-dataset, FDS and HTML exports;
- Fire Scenario Testing and every tested control boundary;
- Worst Case Testing, origin ranking and every tested control boundary;
- plan, graph and 3D visualization helpers;
- canonical and compatibility Streamlit page entry points.

Python compilation and `git diff --check` also passed.

## Practical Montebello Run

Input SHA-256:

```text
d0dd573388317907e6aa59f86319b5408306f0dbe9feea99cb7b83ed1d62ba3a
```

The IFC2X3 payload opened and produced 16 geometry-derived screening nodes, 17 inferred connectors, 2 inferred egress points, a 33-node/32-edge graph and 16 traceable scenarios. The uploaded regulation text produced 15 clauses and 10 candidate rules; 3 supported uploaded thresholds were applied and 5 unsupported candidates were reported rather than silently enforced.

All eight practical workflow gates passed. The correct verdict is:

```text
Operational: PASS_WITH_REVIEW_LIMITATIONS
Engineering: EXPLORATORY_ONLY_NOT_A_VERIFIED_EVACUATION_MODEL
```

Evidence:

```text
outputs/submission_readiness_20260816/practical_montebello/verification_report.json
outputs/submission_readiness_20260816/practical_montebello/verification_report.md
outputs/submission_readiness_20260816/practical_montebello/exports/scenarios.json
outputs/submission_readiness_20260816/practical_montebello/exports/scenarios.csv
```

## 23-Path IFC Compatibility Run

The exact prior 23-path corpus was rerun with the same structural result and no
regression. SHA-256 comparison found 16 unique payloads and 7 renamed or
repeated copies.

| Result | Input paths | Unique payloads | Interpretation |
|---|---:|---:|---|
| Partial | 18 | 12 | Opens and generates scenarios, but topology or measurements require review. |
| Fail | 5 | 4 | Input does not contain a usable evacuation model payload. |
| Pass | 0 | 0 | Strict pass is reserved for verified semantic spaces, doors, exits and connected routes. |

The five path-level failures are three distinct 132-133 byte Git LFS pointer
files and two differently named copies of one minimal wall/opening reference
payload with no evacuation topology. They fail clearly and do not crash the
batch.

The recovered full IFC2X3 models run successfully but remain partial:

| IFC | Spaces | Doors | Exits | Spaces without exit route | Scenarios |
|---|---:|---:|---:|---:|---:|
| Duplex A | 21 | 14 | 4 | 3 | 12 |
| Clinic Architectural | 269 | 254 | 18 | 59 | 12 |

Evidence:

```text
outputs/submission_readiness_20260813/final_23_matrix/compatibility_matrix.csv
outputs/submission_readiness_20260813/final_23_matrix/compatibility_matrix.json
outputs/submission_readiness_20260813/final_23_matrix/per_file/
```

Current duplicate-aware diagnostics additionally write
`compatibility_summary.json`. Generated evidence under `outputs/` is local and
gitignored; the repository contains the scripts and tests required to recreate
it when the IFC corpus is available.

## Transparency Boundary

The primary workflow is deterministic: IfcOpenShell extraction, NetworkX path search, explicit rule checks and configured formulas. spaCy supports clause/rule parsing; optional local retrieval can attach evidence. The system now exports score direction, calibration status, assumptions, source provenance, decision traces and session-scoped review records.

The terms `risk_level`, `compliance_score` and `confidence_score` remain only as backward-compatible export keys. Preferred v2 names are `screening_priority`, `implemented_checks_passed` and `evidence_confidence`.

## Remaining Validation Work

- Confirm inferred exits, connections, widths and occupancy with a qualified reviewer.
- Resolve disconnected spaces in the full Duplex and Clinic models at source or through documented manual corrections.
- Validate fire and evacuation assumptions against calibrated specialist tools before any real building decision.
- Treat scanned regulation PDFs as unsupported until OCR has produced selectable text.

These are evidence and domain-validation limitations, not unresolved application crashes.
