# Fire Model Design Note

## Purpose

This note documents the fire-safety layer in the MSc research prototype
**AI-Driven Generation of Evacuation Scenarios from Building Information
Models**. The runtime boundary remains AI-assisted and deterministic; this layer
does not claim CFD or professional fire-engineering validation.

The project now uses a simplified, explainable fire-origin scenario layer based on:

- t-squared fire growth approximation
- graph-based smoke spread over BIM-derived spaces and connections
- ASET/RSET-inspired evacuation screening
- indicative life-safety impact reporting
- optional export skeletons for professional validation workflows

The prototype remains an academic decision-support tool. It does **not** perform certified fire engineering, CFD, final evacuation certification, toxic gas/FED modelling or legal compliance approval.

## Recognised tools and concepts reviewed

The following recognised fire-safety and evacuation modelling approaches guided the design:

1. **FDS and Smokeview** — NIST's Fire Dynamics Simulator is a CFD model for fire-driven fluid flow, with Smokeview used to visualise output. FDS is appropriate for detailed smoke, heat and fire transport analysis, but it is too computationally and geometrically demanding for the real-time core of this Streamlit prototype.
2. **CFAST** — NIST's CFAST is a zone fire model used to estimate fire/smoke conditions across connected compartments. It is faster and simpler than CFD, but still requires careful fire engineering input and validation.
3. **Pathfinder, MassMotion and STEPS** — These are specialist evacuation or pedestrian movement tools. They are suitable for detailed occupant movement and crowd simulation, whereas this project performs early-stage route and risk screening using graph algorithms.
4. **ASET/RSET** — Performance-based fire safety commonly compares Available Safe Egress Time (ASET) against Required Safe Egress Time (RSET). This project uses that concept as a screening framework: rooms/routes are flagged when the estimated RSET exceeds the graph-derived ASET.
5. **t-squared fire growth** — A simplified t-squared HRR approximation is used to generate an explainable fire growth curve for early-stage scenario exploration.
6. **IFC/openBIM** — IFC2x3, IFC4 and IFC4x3-style BIM models can support extraction of spatial and egress-relevant elements when they contain sufficient IfcSpace, IfcDoor, IfcStair, IfcBuildingStorey and placement/property information.

## Why the prototype should not replace FDS, CFAST or Pathfinder

The system is intentionally positioned as a decision-support and scenario-generation tool rather than a specialist simulator. FDS/Smokeview and CFAST are fire models used by trained practitioners to estimate smoke, heat and untenable conditions. Pathfinder, MassMotion and STEPS are specialised evacuation tools for more detailed movement/crowd analysis.

Replacing those tools inside a Streamlit MSc prototype would be unrealistic and academically unsafe because:

- CFD requires precise geometry, mesh, combustion, material, ventilation and boundary condition assumptions.
- Zone modelling still requires validated compartment and fire input assumptions.
- Agent-based evacuation modelling requires behavioural parameters and calibration.
- Real casualty modelling would require toxicity, FED, visibility, heat exposure, occupant characteristics and behavioural modelling.

Therefore, the implementation only generates **indicative fire-origin scenarios** and exports data/skeletons for later professional validation.

## Why t-squared fire growth is suitable for early-stage screening

The t-squared relationship:

```text
HRR(t) = alpha * t^2
```

is simple, transparent and widely recognisable in fire-safety engineering as an approximation for growing fires. The prototype uses configurable growth classes:

| Growth class | alpha |
|---|---:|
| slow | 0.0029 |
| medium | 0.0117 |
| fast | 0.0469 |
| ultra_fast | 0.1876 |

This is suitable for the prototype because it gives a time-based hazard curve without claiming detailed physical simulation. Users can vary growth class, ventilation factor, suppression assumptions and HRR cap to test sensitivity.

## Why graph-based smoke spread is used

The project already transforms BIM spaces, doors, corridors and exits into a NetworkX graph. This graph is a natural structure for early smoke-route screening because:

- rooms/corridors become nodes;
- doors/corridor links become edges;
- exits are special nodes;
- smoke can be approximated as spreading through graph connectivity;
- blocked nodes/edges can be removed from the route graph;
- smoke-affected nodes can be penalised or marked as high risk;
- evacuation routes can be recalculated using the same graph.

This provides explainable, fast and demo-friendly behaviour. It also fits the dissertation focus on BIM-to-scenario generation.

## How ASET/RSET comparison is used

The prototype calculates:

```text
RSET = detection time + alarm time + pre-movement delay + travel time + congestion delay
```

The graph-based smoke spread module assigns heuristic time-to-untenable values to nodes. The minimum value across a room's evacuation route is treated as model-internal ASET. Nodes not reached during the selected simulation use the simulation horizon as an explicit substitute. The model margin is:

```text
Model margin = graph-derived ASET - assumption-based RSET
```

The classification is:

- positive heuristic margin
- reduced margin
- unsafe
- no route / trapped

This supports transparent sensitivity screening. A positive model margin does not prove tenable conditions or fire safety.

## Professional validation workflow

The prototype can export:

- fire scenario JSON
- ASET/RSET CSV
- hazard timeline CSV
- evacuation result JSON
- FDS skeleton file for expert completion

The FDS skeleton is not a valid final FDS input. It only provides a structured starting point with fire origin, HRR preview and placeholders for mesh, geometry, vents, devices and outputs. Professional validation should be performed separately using specialist software and expert judgement.

## IFC compatibility targets

The prototype targets IFC-based BIM models that contain sufficient evacuation-relevant information.

Target schema families:

- IFC2x3
- IFC4
- IFC4x3 where relevant building elements are available

Required/preferred data:

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
- fire safety property sets where available

Recommended wording:

> Compatible with IFC-based BIM models containing sufficient spatial and egress-related information.

The system should not claim it works with every IFC file.

## Limitations

The fire-safety layer has the following limitations:

- no CFD simulation;
- no validated CFAST zone modelling;
- no toxic gas/FED exposure model;
- no detailed visibility model;
- no agent-based pedestrian behaviour model;
- no panic or disability modelling;
- no guarantee of IFC completeness;
- outputs depend on modelling assumptions;
- all outputs require qualified fire-safety expert review.

## Sources for further validation

- NIST Fire Dynamics Simulator and Smokeview documentation: https://pages.nist.gov/fds-smv/
- NIST CFAST documentation: https://pages.nist.gov/cfast/
- Thunderhead Engineering Pathfinder: https://www.thunderheadeng.com/pathfinder/
- buildingSMART IFC standards: https://technical.buildingsmart.org/standards/ifc/
- buildingSMART IFC4x3 documentation: https://ifc43-docs.standards.buildingsmart.org/
