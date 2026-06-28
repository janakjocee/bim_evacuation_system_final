# Local IFC Validation Matrix

Validation date: 28 June 2026

Command:

```bash
python3 scripts/validate_ifcs.py \
  /Users/janakjocee/Downloads/11134_V_Motebello_Heistopp_Rev.ifc \
  /Users/janakjocee/Downloads/STRUCTURAL/IFC

python3 scripts/validate_ifcs.py \
  /Users/janakjocee/Downloads/real_public_ifc_files \
  --max-scenarios 3 --json
```

| IFC | Schema | Mode | Screened elements | Scenarios tested | Connected graph | Max confidence | Result |
|---|---|---|---:|---:|---|---:|---|
| 11134_V_Motebello_Heistopp_Rev.ifc | IFC2X3 | geometry_derived | 16 | 20 available | Yes | 0.50 | Pass |
| STRUC_NordicLCA_Housing_Concrete_BuildingPermit.ifc | IFC4 | geometry_derived | 60 of 332 candidates | 20 | Yes | 0.50 | Pass |
| STRUC_NordicLCA_Housing_Timber_BuildingPermit.ifc | IFC4 | geometry_derived | 60 of 62 candidates | 20 | Yes | 0.50 | Pass |
| STRUC_NordicLCA_Office_Concrete_BuildingPermit.ifc | IFC4 | geometry_derived | 60 of 774 candidates | 20 | Yes | 0.50 | Pass |
| STRUC_NordicLCA_Office_Timber_BuildingPermit.ifc | IFC4 | geometry_derived | 60 of 162 candidates | 20 | Yes | 0.50 | Pass |
| 01_IFC2X3_Duplex_A_20110907.ifc | UNKNOWN | n/a | 0 | 0 | No | 0.00 | Blocked: Git LFS pointer |
| 02_IFC2X3_Duplex_Rooms_And_Spaces.ifc | UNKNOWN | n/a | 0 | 0 | No | 0.00 | Blocked: Git LFS pointer |
| 03_IFC2X3_Clinic_Architectural.ifc | UNKNOWN | n/a | 0 | 0 | No | 0.00 | Blocked: Git LFS pointer |
| 04_IFC4_buildingSMART_Building_Architecture.ifc | IFC4 | semantic_spaces_inferred_topology | 2 | 2 | Yes | 0.50 | Pass |
| 05_IFC4_buildingSMART_Building_HVAC.ifc | IFC4 | geometry_derived | 2 | 2 | Yes | 0.50 | Pass |
| 06_IFC4X3_ADD2_buildingSMART_Building_Architecture.ifc | IFC4X3 | semantic_spaces_inferred_topology | 2 | 2 | Yes | 0.50 | Pass |
| 07_IFC4X1_Revit_Dormitory_Spaces.ifc | IFC4X1 | semantic_spaces_inferred_topology | 20 | 3 | Yes | 0.50 | Pass |

The three blocked Duplex/Clinic files in `real_public_ifc_files` are not real
IFC payloads in this checkout; they are Git LFS pointer text files. They must be
downloaded with real LFS contents before professional validation can be claimed.

Files without reliable `IfcDoor` connectivity use inferred topology from
uploaded geometry or `IfcSpace` bounding boxes. The system does not treat
inferred connections or egress points as verified architectural evacuation
routes. Geometry-derived scenario confidence is capped at 50%, and low-risk
labels are capped when topology/data quality is insufficient.

Additional checks completed:

- 56 automated tests pass, 3 optional tests skip when local optional fixtures or
  PDF generation dependencies are unavailable.
- The five structural/Montebello IFCs generate valid JSON and CSV exports.
- The five structural/Montebello IFCs render network, risk, performance,
  route-comparison and heatmap figures.
- Fire Scenario Testing runs and exposes JSON/FDS downloads.
- Worst Case Testing runs and exposes JSON/CSV/HTML downloads.
- The bundled demo dataset is explicitly labelled and never substituted into main IFC analysis.
- Uploaded regulation text is parsed into structured numeric rules; compliance
  checks expose uploaded-rule/RAG/default evidence source in the decision trace.
