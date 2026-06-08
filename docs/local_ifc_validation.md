# Local IFC Validation Matrix

Validation date: 8 June 2026

Command:

```bash
./venv/bin/python scripts/validate_ifcs.py \
  /Users/janakjocee/Downloads/11134_V_Motebello_Heistopp_Rev.ifc \
  /Users/janakjocee/Downloads/STRUCTURAL/IFC
```

| IFC | Schema | Mode | Screened elements | Scenarios tested | Connected graph | Result |
|---|---|---|---:|---:|---|---|
| 11134_V_Motebello_Heistopp_Rev.ifc | IFC2X3 | geometry_derived | 16 | 20 available | Yes | Pass |
| STRUC_NordicLCA_Housing_Concrete_BuildingPermit.ifc | IFC4 | geometry_derived | 60 of 332 candidates | 20 | Yes | Pass |
| STRUC_NordicLCA_Housing_Timber_BuildingPermit.ifc | IFC4 | geometry_derived | 60 of 62 candidates | 20 | Yes | Pass |
| STRUC_NordicLCA_Office_Concrete_BuildingPermit.ifc | IFC4 | geometry_derived | 60 of 774 candidates | 20 | Yes | Pass |
| STRUC_NordicLCA_Office_Timber_BuildingPermit.ifc | IFC4 | geometry_derived | 60 of 162 candidates | 20 | Yes | Pass |

All five files contain no `IfcSpace` or `IfcDoor` entities. The system therefore
uses bounded geometry-derived structural screening from each uploaded file's own
elements. It does not treat inferred connections or egress points as verified
architectural evacuation routes. Geometry-derived scenario confidence is capped
at 50%, and occupancy is not inferred from structural elements.

Additional checks completed:

- 35 automated tests pass.
- All five IFCs generate valid JSON and CSV exports.
- All five IFCs render network, risk, performance, route-comparison and heatmap figures.
- Fire Scenario Testing runs and exposes JSON/FDS downloads.
- Worst Case Testing runs and exposes JSON/CSV/HTML downloads.
- The bundled demo dataset is explicitly labelled and never substituted into main IFC analysis.
