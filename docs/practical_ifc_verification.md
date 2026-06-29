# Practical IFC Verification Loop

Verification date: 29 June 2026

Branch:

```text
codex/final-completion-pass
```

## Commands Used

All uploaded/local IFC files were copied into:

```text
data/test_ifc
```

The batch diagnostic command was:

```bash
python3 scripts/batch_ifc_diagnostics.py \
  --input data/test_ifc \
  --regulations /Users/janakjocee/Downloads/Practical_ADB_Volume2_Regulation_Input_for_BIM_Evacuation.txt \
  --max-scenarios 10 \
  --output outputs/ifc_diagnostics
```

Generated local artifacts:

```text
outputs/ifc_diagnostics/compatibility_matrix.csv
outputs/ifc_diagnostics/compatibility_matrix.json
outputs/ifc_diagnostics/per_file/*.diagnostic.json
```

The IFC files themselves and generated diagnostic outputs are intentionally git-ignored.
The repeatable scripts and this report are tracked.

## Batch Result

| Result | Count | Meaning |
|---|---:|---|
| Pass | 0 | No uploaded IFC contains verified semantic spaces, doors, exits and connectivity sufficient for a full reliable claim. |
| Partial | 9 | The system parses the file and generates review-required screening scenarios using semantic spaces with inferred topology or geometry-derived topology. |
| Fail | 3 | The file is a Git LFS pointer stub, not a real IFC payload. |

## Compatibility Matrix Summary

| IFC | Schema | Status | Mode | Raw Spaces | Raw Doors | Extracted Spaces | Extracted Doors | Exits | Scenarios | Graph Confidence | Main Reason |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| 01_IFC2X3_Duplex_A_20110907.ifc | UNKNOWN | fail | uploaded_ifc | 0 | 0 | 0 | 0 | 0 | 0 | 0.00 | Git LFS pointer file, not the actual IFC model. |
| 02_IFC2X3_Duplex_Rooms_And_Spaces.ifc | UNKNOWN | fail | uploaded_ifc | 0 | 0 | 0 | 0 | 0 | 0 | 0.00 | Git LFS pointer file, not the actual IFC model. |
| 03_IFC2X3_Clinic_Architectural.ifc | UNKNOWN | fail | uploaded_ifc | 0 | 0 | 0 | 0 | 0 | 0 | 0.00 | Git LFS pointer file, not the actual IFC model. |
| 04_IFC4_buildingSMART_Building_Architecture.ifc | IFC4 | partial | semantic_spaces_inferred_topology | 2 | 0 | 2 | 3 | 2 | 2 | 0.55 | IfcSpace data exists, but route topology/exits are inferred; 3 door widths assumed. |
| 05_IFC4_buildingSMART_Building_HVAC.ifc | IFC4 | partial | geometry_derived | 0 | 0 | 2 | 3 | 2 | 2 | 0.35 | No semantic IfcSpace/IfcDoor topology; geometry-derived screening only; 3 door widths assumed. |
| 06_IFC4X3_ADD2_buildingSMART_Building_Architecture.ifc | IFC4X3 | partial | semantic_spaces_inferred_topology | 2 | 0 | 2 | 3 | 2 | 2 | 0.55 | IfcSpace data exists, but route topology/exits are inferred; 3 door widths and 2 space areas assumed. |
| 07_IFC4X1_Revit_Dormitory_Spaces.ifc | IFC4X1 | partial | semantic_spaces_inferred_topology | 20 | 0 | 20 | 21 | 2 | 10 | 0.55 | IfcSpace data exists, but route topology/exits are inferred; 21 door widths and 20 space areas assumed. |
| 11134_V_Motebello_Heistopp_Rev.ifc | IFC2X3 | partial | geometry_derived | 0 | 0 | 16 | 17 | 2 | 10 | 0.35 | No semantic IfcSpace/IfcDoor topology; geometry-derived screening only; 17 door widths assumed. |
| STRUC_NordicLCA_Housing_Concrete_BuildingPermit.ifc | IFC4 | partial | geometry_derived | 0 | 0 | 60 | 61 | 2 | 10 | 0.35 | No semantic IfcSpace/IfcDoor topology; geometry-derived screening only; 61 door widths assumed. |
| STRUC_NordicLCA_Housing_Timber_BuildingPermit.ifc | IFC4 | partial | geometry_derived | 0 | 0 | 60 | 61 | 2 | 10 | 0.35 | No semantic IfcSpace/IfcDoor topology; geometry-derived screening only; 61 door widths assumed. |
| STRUC_NordicLCA_Office_Concrete_BuildingPermit.ifc | IFC4 | partial | geometry_derived | 0 | 0 | 60 | 61 | 2 | 10 | 0.35 | No semantic IfcSpace/IfcDoor topology; geometry-derived screening only; 61 door widths assumed. |
| STRUC_NordicLCA_Office_Timber_BuildingPermit.ifc | IFC4 | partial | geometry_derived | 0 | 0 | 60 | 61 | 2 | 10 | 0.35 | No semantic IfcSpace/IfcDoor topology; geometry-derived screening only; 61 door widths assumed. |

## Fix Applied During Loop

The baseline showed that `04_IFC4_buildingSMART_Building_Architecture.ifc`
had two real `IfcSpace` records with `GrossPlannedArea` / `NetPlannedArea`
properties, but the parser marked both areas as assumed.

Fix:

- `IFCParser._extract_space_area()` now reads area from `NetFloorArea`,
  `GrossFloorArea`, `NetPlannedArea`, `GrossPlannedArea`, `NetArea`,
  `GrossArea` and `Area` properties before falling back to quantities or geometry.
- `IFCParser._get_space_type()` now uses `Name`, `LongName`, `Description`
  and `PredefinedType`, so dormitory spaces such as bedroom/storage classify
  more usefully than plain `unknown`.

Before/after:

| IFC | Metric | Before | After |
|---|---|---:|---:|
| 04_IFC4_buildingSMART_Building_Architecture.ifc | Space areas found | 0 | 2 |
| 04_IFC4_buildingSMART_Building_Architecture.ifc | Space areas assumed | 2 | 0 |

## Remaining Failures and Partials

- The three Duplex/Clinic files are Git LFS pointer files of about 132 bytes.
  They cannot be parsed until the real LFS contents are downloaded.
- None of the usable IFC files contain real `IfcDoor` entities. Therefore no
  output is marked as fully reliable/pass.
- Structural NordicLCA files contain useful structural geometry, walls, slabs
  and stairs, but not semantic rooms/doors/exits. The app correctly produces
  geometry-derived screening scenarios with low confidence and review-required
  compliance.
- Several space-only IFCs lack area quantities and door topology. These remain
  partial because areas, route links, exits or connector widths are inferred.

## UI and Export Verification

Covered by local/browser checks and regression tests:

- Scenario `View Details` workspace: static regression guard verifies the stable
  selected-scenario details panel, decision trace and evidence download are wired.
- Manual corrections: regression test verifies exit/width/connectivity edits
  regenerate graph and scenarios, and the UI includes a reset path.
- Regulation upload formats: regression test verifies TXT, DOCX and PDF text
  extraction.
- Main JSON/CSV export: regression test verifies complete JSON evidence payload
  and CSV scenario export wiring.
- IFC-derived fire dataset export: regression test validates the exported
  dataset against the fire/worst-case schema.
- Fire Scenario Testing page: page can use the latest uploaded IFC-derived
  dataset, bundled demo dataset or uploaded JSON, and engine tests cover scenario
  execution/export.
- Worst Case Testing page: page can use the latest uploaded IFC-derived dataset,
  bundled demo dataset or uploaded JSON, and engine tests cover scenario
  execution/export.

## Interpretation

The system now handles every real uploaded IFC in a practical screening mode,
but it does not overclaim. Files without semantic doors remain partial by design.
For a full pass, the IFC must include enough semantic room, door, exit and
connectivity information for verified evacuation routing.
