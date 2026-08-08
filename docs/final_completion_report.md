# Final Completion and QA Report

Verification date: 8 August 2026

Repository: `janakjocee/bim_evacuation_system_final`

## Release Strategy Completed

1. Re-established the local, GitHub Actions and Streamlit deployment baseline.
2. Tested the IFC parser and scenario pipeline against all available local models.
3. Recovered two full public IFC2X3 models to replace unusable local Git LFS pointer copies.
4. Fixed defects found from real model evidence, then repeated the same batch diagnostic.
5. Tested uploaded TXT, PDF and DOCX regulations and corrected unsafe numeric-rule extraction.
6. Exercised the main app, Fire Scenario Testing and Worst Case Testing with executable Streamlit interactions.
7. Hardened exports, manual correction provenance, temporary uploads and custom HTML rendering.
8. Ran the complete automated regression suite and pushed each verified fix to `main`.

## Verified Fixes

### IFC parsing and routing

- Door coordinates now use the complete IFC placement hierarchy instead of a nested local origin.
- Placeholder property labels such as `Fire Rating` are no longer treated as actual fire ratings.
- Boolean IFC properties use strict parsing; unknown strings do not become `True` implicitly.
- Stair child geometry is combined and used to infer review-labelled inter-storey links.
- Doors are classified as exits only when the IFC evidence or boundary geometry supports that result.
- Disconnected topology remains visible in diagnostics instead of being hidden by invented links.

On the full public Duplex model, exit classification changed from 14 of 14 doors to the four actual external doors. Stair connectivity reduced spaces without an exit route from 15 to 3. On the full Clinic model, exit classification changed from 250 of 254 doors to 18 external doors, and spaces without an exit route reduced from 66 to 59.

### Regulations and compliance

- Each numeric measurement must now identify its own metric and comparison operator.
- Per-person width formulas are not misapplied as fixed global exit-width limits.
- When several uploaded rules target one metric, the conservative candidate is selected deterministically.
- Single-direction and alternative-route travel limits are applied using the actual route count.
- Uploaded regulation evidence survives manual IFC corrections and scenario regeneration.
- Built-in values are labelled as prototype defaults, not attributed to a fabricated regulation clause.

Observed regulation results:

| Input | Clauses | Structured rules | Result |
|---|---:|---:|---|
| Practical ADB TXT | 15 | 10 | Correctly retained 18 m, 12 m and 1.05 m screening thresholds. |
| GOV.UK ADB Volume 2 PDF | 426 | 12 | Applied focused 45 m travel, 1.2 m exit and 1.1 m stair candidates without section contamination. |
| DOCX FAQ | 8 | 0 | Extracted text but did not invent numeric constraints; defaults remained explicit. |

### UI, exports and operational safety

- Scenario `View Details` opens, closes and reopens against a stable scenario ID.
- The inspection workspace renders directly inside the selected scenario card; it is no longer hidden below the complete scenario list.
- Expert review decisions and comments persist in session state.
- Main JSON, CSV and XML exports are direct downloads; XML is generated with safe escaping.
- Manual correction and IFC-derived fire dataset exports are present and executable.
- Fire Scenario Testing runs and exports JSON plus an FDS starter skeleton.
- Worst Case Testing runs, auto-ranks origins and exports JSON, CSV and HTML.
- Uploaded IFC/regulation files use collision-resistant names and are removed after each analysis.
- IFC-derived labels are HTML-escaped before entering custom UI markup.
- The dashboard uses Streamlit's native dataframe path, avoiding a Linux PyArrow `Styler` crash found by CI.
- Fire and worst-case results are invalidated whenever a scenario, origin, route blockage or modelling assumption changes, preventing stale metrics from appearing under new controls.
- Root `pages/` entry points now delegate to the canonical `src/ui/pages/` implementations, eliminating two diverging copies of each fire workflow.
- Explanation, export and welcome panels consistently use adaptive theme variables in light and dark modes.
- Reusable UI components and the worst-case result card escape IFC/reviewer text before inserting it into custom HTML.

### Dependency and deployment hardening

- The default deployment no longer installs Torch, SentenceTransformers or FAISS when vector retrieval is disabled.
- Patched Python 3.10-compatible Streamlit, PyArrow, urllib3, Requests, Pillow and test dependencies replace vulnerable legacy pins.
- Optional vector retrieval remains available through `requirements-vector-rag.txt` and an explicit configuration switch.
- `pip-audit` reports no known vulnerabilities in either resolved PyPI dependency graph. The separately hosted spaCy model wheel is pinned but cannot be checked by PyPI's advisory database.

## Automated Verification

Complete local suite:

```text
94 tests collected
91 passed
3 skipped
```

This result was repeated in a clean Python 3.10.20 environment using Streamlit 1.61.1, PyArrow 24.0.0 and pytest 9.1.1. `pip check` found no broken requirements.

The component control matrix now executes:

- all 17 main and nested tab labels, including icon-bearing navigation labels;
- regulation search match/no-match, all four scenario sort options and five risk-filter states;
- scenario details close/reopen, manual correction apply/reset and all four review decisions;
- complete-report generation and all release-critical download URLs;
- all five fire scenarios, four growth classes, eight fire-slider boundaries and suppression mode;
- all five worst-case presets, all 12 custom origins, four slider boundaries, four empty multiselect states, exit blocking and auto-ranking;
- both fire pages using an IFC-derived dataset rather than the bundled demonstration dataset;
- canonical and backward-compatible page entry points.

The three skips are optional compatibility cases whose external model prerequisites are not bundled in the repository. No executed test failed.

Executable Streamlit interaction coverage includes:

- main scenario details close/reopen flow;
- expert review save flow;
- all release-critical main download controls;
- Fire Scenario Testing run and downloads;
- Worst Case Testing run, ranking and downloads.

All three Streamlit entry points also pass startup smoke tests without an application exception.

## Final IFC Matrix

Generated artifacts:

```text
outputs/release_hardening_20260808/final_matrix/compatibility_matrix.csv
outputs/release_hardening_20260808/final_matrix/compatibility_matrix.json
outputs/release_hardening_20260808/final_matrix/per_file/*.diagnostic.json
```

The same 23-file batch was rerun after the component audit and written to:

```text
outputs/component_audit_20260808/compatibility_matrix.csv
outputs/component_audit_20260808/compatibility_matrix.json
```

| Matrix | Inputs | Partial | Fail |
|---|---:|---:|---:|
| Baseline | 21 | 16 | 5 |
| Final | 23 | 18 | 5 |

The final matrix adds two real full IFC2X3 payloads and both generate scenarios:

| IFC | Spaces | Doors | Exits | No exit route | Scenarios | Status |
|---|---:|---:|---:|---:|---:|---|
| Duplex A | 21 | 14 | 4 | 3 | 12 | Partial: three disconnected spaces remain. |
| Clinic Architectural | 269 | 254 | 18 | 59 | 12 | Partial: incomplete exported space/door topology remains. |

The five final failures are explained rather than crashed:

- Three files are 132-133 byte Git LFS pointer text, not IFC model payloads.
- Two files are intentionally minimal wall/opening/window reference examples with no spaces, doors or evacuation topology.

All other 18 inputs open and generate scenarios. They remain `partial` when topology, exits, widths, areas or geometry require inference. A `pass` is intentionally reserved for fully verified semantic spaces, doors, exits and route connectivity.

## AI and Black-Box Position

Uploaded IFC analysis does not switch to the demonstration dataset. The source filename, schema, extraction mode and SHA-256 fingerprint are retained in the result and exports.

The workflow is primarily deterministic decision support:

- IfcOpenShell parses the BIM payload;
- NetworkX builds the route graph and calculates shortest paths;
- spaCy-assisted parsing identifies regulation clauses and candidate rules;
- optional retrieval supplies regulation evidence;
- explicit formulas calculate compliance, risk and confidence;
- every scenario exports route evidence, assumptions, thresholds, violations and a decision trace.

This is deliberately not presented as an autonomous regulatory approval model. The demonstration dataset is used only when the user explicitly selects demonstration mode on the fire-testing pages.

## Remaining Honest Limitations

- No software can recover room/door semantics that are absent from the uploaded IFC. Geometry-derived results are screening outputs and require expert review.
- The two recovered full IFC2X3 models still contain disconnected or incomplete evacuation topology, so they are correctly marked partial.
- IFC4X1 parsed successfully in local evidence but remains best-effort; documented target families are IFC2X3, IFC4, IFC4X3 and IFC4X3_ADD2.
- The 3D and plan views are interactive engineering schematics derived from IFC data, not certified photorealistic BIM viewers.
- ADB extraction supports traceable screening rules, not complete legal interpretation. A qualified fire engineer must verify the source document, project context and final strategy.
- Streamlit Cloud visibility is an account setting. An unauthenticated redirect to Streamlit sign-in does not demonstrate an application failure.

## Run Command

```bash
cd "/Users/janakjocee/Downloads/data visualisation sarjan/bim/bim_evacuation_system_final"
python3 -m streamlit run src/ui/streamlit_app.py
```
