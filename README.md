# AI-Driven Generation of Evacuation Scenarios from Building Information Models

**AI-Assisted Research Prototype: Deterministic IFC/Graph Analysis + NLP Evidence Retrieval**

Developed by **Janak Raj Joshi**<br>
Email: [janakjocee@gmail.com](mailto:janakjocee@gmail.com)<br>
Repository: [janakjocee/bim_evacuation_system_final](https://github.com/janakjocee/bim_evacuation_system_final)

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?logo=Streamlit&logoColor=white)](https://streamlit.io)
[![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)

---

## Overview

This MSc research prototype turns IFC/BIM building data into evacuation screening suggestions for qualified review. It combines openBIM parsing, spatial graph analysis, NLP-assisted rule extraction and evidence retrieval, compliance-oriented checks, explainable scenario generation, session-scoped research review and export.

The heading above is the exact approved proposal title. In this implementation,
"AI-driven" means an AI/NLP-assisted research workflow; it does not mean that an
autonomous or generative model decides routes, legal compliance or building safety.

### What “AI” Means in This Prototype

This project does **not** use GPT, OpenAI, an autonomous agent, CFD, or a certified evacuation simulator to make fire-engineering decisions. The AI-assisted parts are:

- **spaCy NLP** to split uploaded regulation text into clauses and detect simple constraints such as widths and travel distances.
- **Evaluated TF-IDF lexical retrieval** for uploaded regulation evidence, with opt-in SentenceTransformers + FAISS vector retrieval for local research comparisons.
- **A genuine but non-deployed ML experiment** comparing TF-IDF/logistic-regression space-use classification against the deterministic parser using source-family holdouts. The learned model underperformed and remains disabled.
- **Deterministic graph/rule algorithms** for route search, compliance screening, prioritisation and explanation traces.

The system is fast because it performs lightweight BIM parsing, NetworkX shortest-path checks, simplified fire/smoke approximations and rule-based scoring. It is a screening and explanation prototype, not a final legal or professional fire-safety decision system.

The project now includes two fire-safety scenario layers:

1. **Fire-Origin Worst-Case Scenario Engine** — tests blocked nodes, blocked doors, smoke-affected routes, rerouting, trapped rooms, bottlenecks and affected occupants.
2. **ASET/RSET Fire Scenario Engine** — uses a simplified t-squared fire growth curve, graph-based smoke spread approximation, ASET/RSET-inspired screening and indicative life-safety impact reporting.

This is an academic decision-support tool. It does **not** perform CFD, certified evacuation modelling, toxic gas/FED exposure modelling or final fire-safety certification. All outputs require review by a qualified fire-safety professional.

---

## Key Features

- IFC/openBIM parsing for spaces, doors, stairs, exits and storeys where available.
- NetworkX spatial graph generation and evacuation routing.
- Interactive 3D IFC screening view using uploaded-file geometry, connections and exits.
- Interactive top-down IFC diagram with colored footprints, routes and exit markers.
- Clearly labelled 3D scenario schematics for demo fire and worst-case workflows.
- Working scenario inspection workspace with highlighted route diagram, practical
  readiness checklist, evidence display and per-scenario download.
- Regulation-oriented NLP workflow using spaCy, pattern extraction and evaluated TF-IDF evidence retrieval, with optional FAISS and SentenceTransformers.
- Evacuation scenario generation with distance, time, evidence confidence, implemented-check outcomes and screening priority.
- Alternative route summaries and route-reliability labels for each generated scenario.
- Practical compliance screening for travel distance, final/route door width,
  corridor width, stair width/riser/tread data where available, missing data,
  inferred topology and route redundancy.
- Explainability panel for traceable deterministic decision reasoning.
- Session-scoped human-in-the-loop research review workflow; this is not authenticated professional approval.
- Fire-origin worst-case scenario testing.
- ASET/RSET fire scenario testing.
- Auto-ranking of worst fire origins.
- IFC readiness/compatibility validation helper.
- JSON, CSV, HTML and FDS-skeleton style export outputs.

---

## Explainability and Black-Box Control

The project avoids treating the AI layer as an unexplained black box. Each
generated evacuation scenario exports:

- the IFC extraction basis used for the scenario;
- the route search method, selected path, distance and evacuation time;
- alternative escape routes where the IFC-derived graph contains more than one
  route to an exit;
- the compliance checks that passed or failed, including whether each threshold
  came from an uploaded structured rule, retrieved evidence or built-in default;
- the deterministic screening index and weighted factor breakdown, including IFC
  graph confidence, narrow-door penalties, route-redundancy penalties and
  data-quality caps;
- evidence-confidence score and data-quality notes;
- a human-readable explanation and qualified-review recommendations.

The Explainability tab and each scenario's **View Details** workspace show this
decision trace directly. Risk classification is rule/score based and
deterministic, not a hidden neural-network prediction. Evidence retrieval is used
only when a regulation document is uploaded and retrieval is enabled; otherwise
the app clearly states that built-in default screening constraints were used.
Low-risk labels are capped when route topology is mostly inferred, when critical
IFC measurements are assumed, or when no verified exit data is available.
Routes are labelled as `verified`, `partially_inferred`, `heavily_inferred` or
`insufficient` so the reviewer can see whether a path came from IFC semantic
connectivity or from geometry-derived screening.

The submission terminology, score directions, assumptions and validation
boundary are consolidated in [`docs/submission_claim_boundary.md`](docs/submission_claim_boundary.md).
The final executable evidence is summarized in
[`docs/submission_readiness_20260816.md`](docs/submission_readiness_20260816.md).
The new controlled, ML, retrieval and scenario results are summarized in
[`docs/research_evaluation_results_20260816.md`](docs/research_evaluation_results_20260816.md).

---

## Fire-Safety-Inspired Modelling Layer

The upgraded fire layer is located in:

```text
src/fire/
```

It contains:

| File | Purpose |
|---|---|
| `fire_growth.py` | Simplified t-squared HRR model: `HRR(t) = alpha * t^2` |
| `smoke_spread.py` | Graph-based smoke spread approximation over BIM-derived nodes/edges |
| `aset_rset.py` | RSET and graph-derived ASET/model-margin screening |
| `life_safety_impact.py` | Indicative life-safety impact summary, not casualty prediction |
| `fire_scenario_engine.py` | Combined fire growth + smoke + ASET/RSET + impact engine |
| `fds_exporter.py` | JSON/CSV rows and FDS skeleton for expert completion |

### Fire growth classes

| Growth class | Alpha |
|---|---:|
| slow | 0.0029 |
| medium | 0.0117 |
| fast | 0.0469 |
| ultra_fast | 0.1876 |

The HRR curve can be modified by ventilation factor, suppression/sprinkler assumption, sprinkler activation time and maximum HRR cap.

### ASET/RSET screening

The prototype uses:

```text
RSET = detection time + alarm time + pre-movement delay + travel time + congestion delay
Model margin = graph-derived ASET - assumption-based RSET
```

The graph-based smoke model assigns heuristic time-to-untenable values to nodes. The minimum across a route is treated as model-internal ASET; if a node is not reached, the simulation horizon is substituted and disclosed. These are not validated tenability predictions.

Classifications:

- positive heuristic margin
- reduced margin
- unsafe
- no route / trapped

---

## Demo Datasets and Scenarios

The demo dataset is stored at:

```text
data/demo_worst_case_building.json
```

It is a **synthetic demonstration dataset** and is never substituted into the
main uploaded-IFC analysis pipeline. The Fire Scenario Testing and Worst Case
Testing pages clearly show their active dataset source and provide controls to:

- download and inspect the bundled demo JSON;
- use the bundled demonstration dataset explicitly; or
- upload a structurally validated custom scenario JSON dataset.

Main IFC results include the uploaded filename, detected schema, analysis mode
and SHA-256 fingerprint for provenance.

The main uploader accepts plain `.ifc` and compressed `.ifczip`. IFCZIP is the
preferred route for large STEP-text models: it must contain exactly one IFC
file and is inspected before parsing. Both the uploaded file and the
uncompressed IFC inside an IFCZIP are limited to 200 MB. IFCZIP does not bypass
the Streamlit upload guardrail because uploads are held in memory and IFC
geometry parsing needs additional working memory. For example:

```bash
zip -j building.ifczip building.ifc
```

Do not raise the cloud limit merely to accept a large plain-text IFC. A model
whose uncompressed IFC is larger than 200 MB should be tested locally or on a
deployment with measured memory capacity.

The IFC under `tests/fixtures/` is used only by automated regression tests. The
Streamlit application does not load it automatically; main analysis always uses
the file selected by the user.

It includes:

- 8 occupied spaces/rooms
- 2 corridors
- 2 exits
- door/corridor connections with width and distance
- occupancies and room types
- Kitchen Store as a high-hazard room
- Plant Room as an ultra-fast fire source candidate
- Lecture Room as a high-occupancy room
- bottleneck doors and corridor single-point-of-failure assumptions

Predefined scenarios:

| Scenario | Description |
|---|---|
| WC01 | Kitchen/store fast fire affecting main corridor |
| WC02 | Kitchen fire blocks main exit route |
| WC03 | Plant/electrical ultra-fast fire affecting rear exit |
| WC04 | Classroom medium fire with high occupancy pressure |
| WC05 | Combined worst case: fire origin + smoke spread + exit unavailable + delayed pre-movement |

---

## Streamlit Pages

Run the app:

```bash
streamlit run src/ui/streamlit_app.py
```

Audit one IFC or a folder of IFC files from the command line:

```bash
python scripts/validate_ifcs.py /path/to/model.ifc /path/to/ifc-folder
```

The audit reports detected schema, analysis mode, screened elements/spaces,
scenario count, graph connectivity, confidence ceiling, Git LFS pointer files
and errors.

Generate the full practical compatibility matrix from local test IFCs:

```bash
python scripts/batch_ifc_diagnostics.py --input data/test_ifc --output outputs/ifc_diagnostics
```

This writes:

```text
outputs/ifc_diagnostics/compatibility_matrix.csv
outputs/ifc_diagnostics/compatibility_matrix.json
outputs/ifc_diagnostics/compatibility_summary.json
outputs/ifc_diagnostics/per_file/*.diagnostic.json
```

The summary distinguishes tested input paths from unique IFC payloads by
SHA-256. Repeated downloads or renamed copies remain visible in the matrix but
are not counted as independent models when reporting corpus diversity.

Run a strict end-to-end acceptance check for one real IFC and an optional
regulation document:

```bash
python scripts/verify_practical_workflow.py /path/to/model.ifc \
  --regulations /path/to/regulations.txt \
  --output outputs/practical_verification
```

The verifier checks the real payload and SHA-256 provenance, IFC opening,
extraction, graph routes, scenario decision traces, regulation application and
JSON/CSV reconciliation. It writes both `verification_report.json` and
`verification_report.md`. Its operational verdict is separate from engineering
evidence quality: a geometry-only IFC can be processed successfully without
being misrepresented as a verified room-and-door evacuation model.

`pass` means verified semantic spaces, doors, exits and route connectivity were
available. `partial` means the file was processed and scenarios were generated,
but some route, exit, width, area or geometry assumptions require qualified review.
`fail` means no usable IFC payload/topology was available, for example a Git LFS
pointer file instead of the real model.

The completed local multi-IFC audit is documented in:

```text
docs/local_ifc_validation.md
```

The deeper current audit, including raw IFC entity counts, graph diagnostics,
regulation application and reliability classification, is documented in:

```text
docs/deep_audit_report.md
```

The practical feature benchmark and researched future-work boundary is documented in:

```text
docs/practical_benchmark.md
```

The final 8 August release-hardening pass, 23-file compatibility matrix,
regulation evidence, executable UI tests and viva/review talking points are
documented in:

```text
docs/final_completion_report.md
```

The proposal, marking-scheme and final-report claim audit is documented in:

```text
docs/proposal_report_alignment_20260816.md
```

The duplicate-aware IFC source and licence audit is documented in:

```text
docs/ifc_corpus_provenance_20260816.md
```

The earlier June practical IFC verification loop is retained in:

```text
docs/practical_ifc_verification.md
```

Then use the sidebar pages:

```text
🔥 Worst Case Testing
Fire Scenario Testing
```

### Worst Case Testing page

Supports:

- predefined fire-origin worst-case scenario selection
- custom fire origin
- smoke-affected nodes
- blocked nodes and blocked edges
- occupancy multiplier
- pre-movement delay
- graph visualisation
- interactive 3D hazard-state schematic
- auto-ranking of worst fire origins
- JSON, CSV and HTML export

### ASET/RSET Fire Scenario Testing page

Supports:

- predefined fire scenario selection
- custom fire origin
- fire growth class
- simulation duration
- time step
- detection time
- alarm time
- pre-movement delay
- walking speed
- smoke spread speed factor
- ventilation factor
- suppression/sprinkler option
- sprinkler activation time
- door-state assumption: open, mixed, closed
- HRR chart
- smoke spread timeline
- ASET/RSET comparison table
- model-internal heuristic margin table
- indicative life-safety impact summary
- graph visualisation
- interactive 3D fire/smoke/exit schematic
- FDS skeleton export for expert completion

---

## IFC Compatibility

The system targets IFC-based BIM models that contain sufficient spatial and egress-related information.

Target schema families:

- IFC2X3
- IFC4
- IFC4X3
- IFC4X3_ADD2

These are documented targets, not a claim that every file in those schema
families will contain suitable evacuation data. Semantic analysis uses
`IfcSpace`, `IfcDoor`, storeys and exits where available. Geometry-derived mode
uses only geometry and properties from the uploaded IFC when those semantic
entities are absent. No demo building is used as an IFC fallback.
The latest local audit also successfully parsed IFC4X1 as a compatible
IfcOpenShell schema, but IFC4X1 remains a best-effort observed schema rather
than one of the headline documented targets.

Required or preferred data:

- IfcProject
- IfcSite
- IfcBuilding
- IfcBuildingStorey
- IfcSpace
- IfcDoor
- IfcStair
- IfcSlab/floor geometry where useful
- door width properties
- space area properties
- storey/floor placement
- exit identification where available or manually assigned
- occupancy where available or estimated
- material/fuel/fire-safety properties where available

Use the validator in:

```text
src/bim_processing/ifc_validation.py
```

Correct wording:

> Documented targets are IFC2X3, IFC4, IFC4X3 and IFC4X3_ADD2. Successful
> analysis also depends on usable semantic entities or element geometry.

Do **not** claim that the prototype works with every IFC version or every IFC file.

IFCs downloaded from Hugging Face or another public host may be used for local
robustness and compatibility testing. Before counting them as dissertation
evaluation evidence, record the exact dataset URL, revision/commit, model
filename, SHA-256, licence, attribution and any redistribution restriction in
`docs/ifc_corpus_provenance_20260816.md`. Hosting location alone is not evidence
of permission or independent ground truth.

---

## Regulation Source Evidence

The application accepts TXT, MD, PDF and DOCX regulation documents. For UK
Approved Document B work, use the official GOV.UK publication page and declare
the jurisdiction, edition/amendment status and source URL in the sidebar. The
export records those user-declared fields together with the uploaded filename,
file type and SHA-256 fingerprint.

Approved Document B is statutory guidance for England, not a machine-readable
legal approval API. The parser activates only supported numeric screening
metrics, identifies unsupported extracted candidates, and does not resolve
building classification, commencement dates or transitional provisions. See
`docs/regulation_source_protocol.md`.

---

## Professional Validation Workflow

The project can export structured scenario data for downstream expert validation:

- fire scenario JSON
- ASET/RSET CSV
- hazard timeline CSV
- evacuation result JSON
- HTML report from the worst-case page
- FDS skeleton file for expert completion

The FDS skeleton is only a starting template. It includes fire-origin and HRR preview comments plus placeholders for mesh, geometry, vents, devices, materials and outputs. It is **not** a complete or certified FDS input file.

The `Research Review` tab also provides three guarded evidence workflows:

- a structured preliminary domain-review record covering governance reference,
  competence scope, ratings, safety findings, corrections and sign-off;
- a manual accessibility record covering keyboard, focus, zoom, screen-reader,
  chart-equivalent, message and mobile-width checks;
- a blinded independent-label CSV handoff for the space-use ML experiment.

The forms make evidence collection reproducible, but they do not verify a
reviewer's identity or qualifications, grant ethics permission, certify WCAG
conformance or establish professional fire-engineering validation.

Specialist tools that may be used for professional validation include:

- NIST FDS/Smokeview
- NIST CFAST
- Thunderhead Pathfinder
- MassMotion
- STEPS

---

## System Architecture

```text
IFC / Demo Building Data
        ↓
BIM Parser and IFC Validation
        ↓
Spatial Graph Builder
        ↓
Scenario Generator and Compliance-Oriented Screening
        ↓
Fire-Origin Worst-Case Engine
        ↓
ASET/RSET Fire Scenario Engine
        ↓
Explainability + Session-Scoped Research Review
        ↓
JSON / CSV / HTML / FDS Skeleton Export
```

---

## Project Structure

```text
bim-evacuation-system-streamlit/
├── config/
├── data/
│   └── demo_worst_case_building.json
├── docs/
│   ├── fire_model_design.md
│   └── worst_case_testing.md
├── pages/
│   ├── 🔥_Worst_Case_Testing.py
│   └── Fire_Scenario_Testing.py
├── src/
│   ├── bim_processing/
│   │   ├── ifc_parser.py
│   │   ├── ifc_validation.py
│   │   ├── feature_extractor.py
│   │   └── spatial_graph.py
│   ├── fire/
│   │   ├── fire_growth.py
│   │   ├── smoke_spread.py
│   │   ├── aset_rset.py
│   │   ├── life_safety_impact.py
│   │   ├── fire_scenario_engine.py
│   │   └── fds_exporter.py
│   ├── nlp/
│   ├── scenario/
│   │   └── worst_case_engine.py
│   ├── pipeline/
│   ├── ui/
│   └── utils/
├── tests/
│   ├── test_basic.py
│   ├── test_worst_case_engine.py
│   ├── test_fire_model.py
│   └── test_ifc_validation.py
├── requirements.txt
├── requirements-vector-rag.txt
└── README.md
```

---

## Running Locally

```bash
git clone https://github.com/janakjocee/bim_evacuation_system_final.git
cd bim_evacuation_system_final
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
streamlit run src/ui/streamlit_app.py
```

The public app uses deterministic TF-IDF lexical evidence retrieval. For an explicit
local vector-RAG experiment, install the optional native ML stack and enable
`rag.vector_enabled` in `config/settings.yaml`:

```bash
pip install -r requirements-vector-rag.txt
```

Open:

```text
http://localhost:8501
```

---

## Testing

Install test-only fixture tools and run:

```bash
pip install -r requirements-dev.txt
pytest
pytest --cov=src --cov=scripts --cov-report=term
```

Run the proposal-aligned research evidence suite:

```bash
python scripts/run_research_evaluation.py --output-dir outputs/research_evaluation
```

The suite generates a deterministic IFC4 fixture, checks exact parser/route
ground truth, evaluates the grouped space-use classifier, benchmarks regulation
retrieval and repeats declared evacuation/fire/worst-case outcomes. CI uploads
these reports as the `research-evaluation-evidence` artifact.

Create and validate the blinded human-label review pack with:

```bash
python scripts/create_space_label_review_pack.py
python scripts/validate_space_label_review_pack.py \
  outputs/space_label_review/independent_label_review.csv
```

The blank pack must fail validation until an authorised reviewer independently
supplies every label, confidence, confirmation reference and review status.
Silver-label evaluation can never promote the classifier into the runtime.

The geometry-only regression tests run when
`tests/fixtures/11134_V_Motebello_Heistopp_Rev.ifc` is present. Fresh GitHub
checkouts without that optional IFC fixture skip three real-model tests; use
`scripts/validate_ifcs.py` with local IFC files for the full real-model audit.

Test coverage includes:

- demo dataset loading
- graph building
- worst-case scenario behaviour
- blocked route/no-path handling
- t-squared HRR calculation
- suppression HRR reduction/capping
- graph-based smoke spread
- ASET/RSET model-margin calculation
- trapped occupant detection
- forbidden casualty wording checks
- auto-ranking of worst fire origins
- IFC readiness validation
- export payload fields
- controlled IFC entity, measurement, topology and route ground truth
- grouped deterministic-versus-ML space-use classification
- regulation Recall@1, Recall@3 and MRR
- scenario expected-case repeatability
- custom light/dark palette contrast
- preliminary domain-review record completeness and non-certification guards
- manual accessibility record completeness and non-certification guards
- blinded independent-label pack creation and validation

---

## Suggested Dissertation Screenshots

Capture:

1. Main dashboard overview
2. BIM model insights / extracted spaces
3. Regulation intelligence / active constraints
4. Evacuation scenario list
5. Deterministic decision trace
6. Screening-priority heatmap and assumption registry
7. Research review panel
8. Fire-Origin Worst-Case Testing page
9. WC02 or WC05 critical scenario summary
10. Room-by-room trapped/rerouted table
11. Graph visualisation showing fire, smoke, blocked nodes and exits
12. ASET/RSET Fire Scenario Testing page
13. HRR over time chart
14. Smoke spread timeline table
15. ASET/RSET comparison table
16. Indicative life-safety impact cards/table
17. Auto-ranked worst fire origins table
18. FDS skeleton export button

---

## Safety and Academic Disclaimer

This prototype is an academic decision-support tool. It does not perform CFD, certified evacuation modelling, toxic gas exposure modelling, detailed visibility modelling, real casualty prediction, final fire strategy approval, or legal compliance certification. It uses simplified BIM-derived spatial graphs, route analysis, t-squared fire growth, graph-based smoke spread approximation and ASET/RSET-inspired screening. All outputs must be reviewed by a qualified fire-safety professional.
