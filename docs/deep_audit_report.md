# Deep IFC and Regulation Audit

Audit date: 28 June 2026

Branch used for this audit:

```text
codex/deep-ifc-regulation-audit
```

## What Currently Works

- Streamlit upload flow accepts IFC plus TXT, MD, PDF and DOCX regulation files.
- `EvacuationPipeline` rejects Git LFS pointer files before parsing.
- `IFCParser` can parse real IFC payloads through IfcOpenShell and extract:
  `IfcSpace`, `IfcDoor`, `IfcStair`, `IfcSlab`, `IfcWall`,
  `IfcBuildingElementProxy`, `IfcOpeningElement`, `IfcRelSpaceBoundary`,
  property sets and quantity values where present.
- Door-space connectivity uses:
  `IfcRelSpaceBoundary`, opening-fill relationships and a labelled geometric
  proximity fallback.
- Exit detection uses external/fire-exit properties, name keywords and perimeter
  location fallback.
- `SpatialGraphBuilder` no longer fabricates cyclic fallback connectivity.
  It records verified edges, inferred edges, disconnected spaces and spaces
  without exit routes.
- Scenario generation attaches route edge quality, route confidence, route
  reliability, alternative-route summaries, graph confidence, data-quality notes
  and compliance evidence to exported JSON.
- Compliance screening now includes practical review checks for route redundancy,
  route door width, corridor width when corridor geometry exists, stair
  width/riser/tread data when stair elements exist, and missing/assumed area
  measurements.
- Risk scoring includes actual exit-capacity estimates, graph confidence,
  inferred-route penalties, assumed-measurement penalties, narrow-door
  penalties, route-redundancy penalties and missing-area penalties.
- Uploaded regulation text is parsed into clauses and structured numeric rules.
- Compliance checks expose whether each threshold came from uploaded rules,
  keyword/RAG evidence or default config.
- RAG/evidence retrieval uses stable keyword search by default. Optional
  SentenceTransformer + FAISS vector retrieval is available only when explicitly
  enabled in config, because the native stack can crash the process in some
  local/cloud environments.
- Fire Scenario Testing and Worst Case Testing have automated regression tests.
- BIM Insights includes a manual correction layer for door widths, exits and
  door-space assignments. Applying corrections regenerates graph and scenarios.
- BIM Insights can export the uploaded IFC-derived graph as a Worst Case/Fire
  Scenario Testing JSON dataset. Inferred exits, assumed widths and review
  occupancy remain labelled in the exported file.

## What Is Partial

- Real professional evacuation routing requires verified `IfcDoor`/space
  connectivity. Several provided real IFCs contain spaces or geometry but no
  real `IfcDoor` entities, so the app produces inferred screening outputs only.
- Geometry-derived and space-inferred topology can support visual/practical
  review, but it is not a certified evacuation route model.
- Regulation parsing supports common numeric width/distance/stair patterns, but
  it is not a complete legal parser for all Approved Document B wording.
- Some parsed rule types may be reported as extracted but not enforceable if no
  deterministic checker exists for that metric.
- PDF extraction requires selectable text. Scanned image PDFs still need OCR
  before upload.

## What Fails or Is Blocked

- Three supplied IFC paths are Git LFS pointer text files, not real IFC payloads.
  They cannot be opened by IfcOpenShell or used for real validation until the
  actual LFS content is downloaded.
- None of the usable supplied IFC files contain verified `IfcDoor` semantics, so
  all successful scenario outputs are classified as inferred and require expert
  review.

## Multi-IFC Compatibility Matrix

Command:

```bash
python3 scripts/validate_ifcs.py \
  /Users/janakjocee/Downloads/real_public_ifc_files \
  /Users/janakjocee/Downloads/11134_V_Motebello_Heistopp_Rev.ifc \
  --regulations /Users/janakjocee/Downloads/Practical_ADB_Volume2_Regulation_Input_for_BIM_Evacuation.txt \
  --max-scenarios 5 --json
```

| IFC | Size | Schema | Opens | Raw Spaces | Raw Doors | Raw Stairs | Slab/Wall/Proxy | Extracted Spaces | Extracted Doors | Exits | Connections | Graph | No Route | Scenarios | Mode | Reliability |
|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|---|---|
| 01_IFC2X3_Duplex_A_20110907.ifc | 132 B | UNKNOWN | No | 0 | 0 | 0 | 0/0/0 | 0 | 0 | 0 | 0 | 0n/0e | 0 | 0 | failed | Git LFS pointer |
| 02_IFC2X3_Duplex_Rooms_And_Spaces.ifc | 132 B | UNKNOWN | No | 0 | 0 | 0 | 0/0/0 | 0 | 0 | 0 | 0 | 0n/0e | 0 | 0 | failed | Git LFS pointer |
| 03_IFC2X3_Clinic_Architectural.ifc | 133 B | UNKNOWN | No | 0 | 0 | 0 | 0/0/0 | 0 | 0 | 0 | 0 | 0n/0e | 0 | 0 | failed | Git LFS pointer |
| 04_IFC4_buildingSMART_Building_Architecture.ifc | 225635 B | IFC4 | Yes | 2 | 0 | 0 | 3/4/5 | 2 | 3 inferred | 2 inferred | 4 | 5n/4e | 0 | 2 | semantic_spaces_inferred_topology | inferred_requires_review |
| 05_IFC4_buildingSMART_Building_HVAC.ifc | 179727 B | IFC4 | Yes | 0 | 0 | 0 | 0/0/2 | 2 derived | 3 inferred | 2 inferred | 4 | 5n/4e | 0 | 2 | geometry_derived | inferred_requires_review |
| 06_IFC4X3_ADD2_buildingSMART_Building_Architecture.ifc | 220789 B | IFC4X3 | Yes | 2 | 0 | 0 | 3/4/4 | 2 | 3 inferred | 2 inferred | 4 | 5n/4e | 0 | 2 | semantic_spaces_inferred_topology | inferred_requires_review |
| 07_IFC4X1_Revit_Dormitory_Spaces.ifc | 24555 B | IFC4X1 | Yes | 20 | 0 | 0 | 0/0/0 | 20 | 21 inferred | 2 inferred | 40 | 41n/40e | 0 | 5 | semantic_spaces_inferred_topology | inferred_requires_review |
| 11134_V_Motebello_Heistopp_Rev.ifc | 109324 B | IFC2X3 | Yes | 0 | 0 | 0 | 0/0/19 | 16 derived | 17 inferred | 2 inferred | 32 | 33n/32e | 0 | 5 | geometry_derived | inferred_requires_review |

## Regulation Test Result

The supplied regulation text:

```text
/Users/janakjocee/Downloads/Practical_ADB_Volume2_Regulation_Input_for_BIM_Evacuation.txt
```

produced:

- 15 parsed clauses
- 13 structured numeric rules
- 4 active uploaded-rule thresholds after duplicate metric overwrites
- 0 unsupported rules for this specific practical input

The active rule summary is available in the Regulation Intelligence tab and in
exported JSON under `regulation_application`.

## Test Result

```text
python3 -m pytest -q
70 passed, 3 skipped
```

The skipped tests are optional environment-dependent tests, such as PDF fixture
generation when the local PDF writer dependency is not present, or optional IFC
fixture tests when fixtures are not included in the checkout.

## Practical Interpretation

The app is stronger and safer after this audit, but the supplied IFC files still
do not prove fully reliable automated evacuation routing because the usable
files lack verified door semantics. The correct interpretation is:

- Pass for uploaded-file-derived screening and visualization.
- Partial pass for space/geometry-derived route exploration.
- Not safe as an automated compliance decision without expert review and a
  semantically rich IFC containing spaces, doors, exits and connectivity.

## Fire/Worst-Case Bridge

The uploaded IFC-derived graph can now be exported to the same JSON dataset
schema used by the Worst Case Testing page. For geometry-derived IFC files where
occupancy is unavailable, the exporter adds a low-confidence review occupancy so
the fire-origin engine can run practical screening instead of silently reporting
zero affected occupants. The exported dataset is labelled
`ifc_derived_requires_review` and must not be treated as a certified fire model.
