# BIM Evacuation Scenario Generator

**AI-Driven Generation of Evacuation Scenarios from Building Information Models**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?logo=Streamlit&logoColor=white)](https://streamlit.io)
[![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)

---

## Overview

This MSc research prototype turns IFC/BIM building data into evacuation scenario suggestions for expert review. It combines openBIM parsing, spatial graph analysis, NLP/RAG-assisted regulation interpretation, compliance-oriented screening, explainable scenario generation, human-in-the-loop review and export.

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
- Regulation-oriented NLP/RAG workflow using spaCy, FAISS and SentenceTransformers.
- Evacuation scenario generation with distance, time, confidence, compliance and risk.
- Explainability panel for traceable AI reasoning.
- Human-in-the-loop expert review workflow.
- Fire-origin worst-case scenario testing.
- ASET/RSET fire scenario testing.
- Auto-ranking of worst fire origins.
- IFC readiness/compatibility validation helper.
- JSON, CSV, HTML and FDS-skeleton style export outputs.

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
| `aset_rset.py` | RSET and ASET/safety-margin screening |
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
Safety margin = ASET - RSET
```

The graph-based smoke model estimates time-to-untenable for nodes. The minimum time-to-untenable across a route is treated as the indicative ASET for that evacuation path.

Classifications:

- safe margin
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
scenario count, graph connectivity, confidence ceiling and errors.

The completed local multi-IFC audit is documented in:

```text
docs/local_ifc_validation.md
```

The practical feature benchmark and researched future-work boundary is documented in:

```text
docs/practical_benchmark.md
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
- safety margin table
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
Explainability + Human-in-the-Loop Expert Review
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
└── README.md
```

---

## Running Locally

```bash
git clone https://github.com/janakjocee/bim-evacuation-system-streamlit.git
cd bim-evacuation-system-streamlit
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
python -m spacy download en_core_web_sm
streamlit run src/ui/streamlit_app.py
```

Open:

```text
http://localhost:8501
```

---

## Testing

Run:

```bash
pytest
```

The geometry-only regression tests run when
`tests/fixtures/11134_V_Motebello_Heistopp_Rev.ifc` is present. Fresh GitHub
checkouts without that optional IFC fixture skip those two tests; use
`scripts/validate_ifcs.py` with local IFC files for the full real-model audit.

Test coverage includes:

- demo dataset loading
- graph building
- worst-case scenario behaviour
- blocked route/no-path handling
- t-squared HRR calculation
- suppression HRR reduction/capping
- graph-based smoke spread
- ASET/RSET safety-margin calculation
- trapped occupant detection
- forbidden casualty wording checks
- auto-ranking of worst fire origins
- IFC readiness validation
- export payload fields

---

## Suggested Dissertation Screenshots

Capture:

1. Main dashboard overview
2. BIM model insights / extracted spaces
3. Regulation intelligence / active constraints
4. Evacuation scenario list
5. Explainable AI reasoning chain
6. Risk heatmap / ASET-RSET concept
7. Expert review panel
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
