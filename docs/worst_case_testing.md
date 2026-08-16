# Fire-Origin Worst-Case Scenario Engine

This document explains the fire-origin-based worst-case scenario engine added to the BIM Evacuation Scenario Generator.

## Purpose

The engine supports **indicative decision-support screening** for evacuation planning. It tests how a building evacuation graph behaves when a fire starts at a selected location and causes smoke-affected routes, blocked evacuation routes, exit disruption, trapped rooms, bottlenecks and occupancy pressure.

It is designed for MSc prototype evaluation and human-in-the-loop review. It is **not** a certified fire engineering model, CFD solver, agent-based evacuation simulator or replacement for a qualified fire-safety engineer.

## Demo Dataset

The bundled dataset is stored at:

```text
data/demo_worst_case_building.json
```

It represents a single-floor academic building with:

- 8 occupied spaces/rooms
- 2 corridors
- 2 exits
- door/corridor connections with `width_m` and `distance_m`
- room occupancies
- a high-hazard Kitchen Store
- a high-occupancy Lecture Room
- narrow bottleneck door/corridor elements
- 4 predefined fire scenarios

## Predefined Fire Scenarios

| ID | Scenario | Purpose |
|---|---|---|
| WC01 | Kitchen fire affecting main corridor | Tests smoke-affected route and high-risk rerouting |
| WC02 | Kitchen fire blocks main exit route | Tests critical trapped-room/no-path handling |
| WC03 | Rear exit blocked with high lecture room occupancy | Tests high occupancy and exit loss |
| WC04 | Combined worst case | Tests fire + smoke + blocked route + high occupancy |

## Engine Logic

The engine is implemented in:

```text
src/scenario/worst_case_engine.py
```

For each selected scenario it:

1. Builds a NetworkX graph from the demo building dataset.
2. Marks the fire origin as blocked or critical.
3. Removes blocked nodes and blocked door/corridor edges.
4. Penalises smoke-affected nodes and high-risk edges.
5. Recalculates routes from every occupied room to available exits.
6. Detects trapped rooms where no route exists.
7. Detects rerouted rooms where the normal route changes.
8. Flags bottleneck elements below the configured width threshold.
9. Calculates evacuation time using distance, walking speed, occupancy and door-width penalty.
10. Scores risk using configurable weights.
11. Produces compliance-oriented screening checks and explainable text.

## Risk Scoring

Default risk triggers are:

| Trigger | Score |
|---|---:|
| No path to exit | +100 |
| Only one exit available | +25 |
| Nearest route blocked | +20 |
| Travel distance above threshold | +20 |
| Door width below 0.8 m | +15 |
| High occupancy above 50 people | +15 |
| Bottleneck encountered | +15 |
| Route passes smoke/high-risk area | +25 |
| Pre-movement delay above 90 seconds | +10 |

Risk classification:

| Score | Risk |
|---:|---|
| 0–25 | Low |
| 26–50 | Medium |
| 51–80 | High |
| 81+ | Critical |

## Streamlit UI

A new multipage Streamlit page is available:

```text
pages/🔥_Worst_Case_Testing.py
```

Run the main app as usual:

```bash
streamlit run src/ui/streamlit_app.py
```

Then open the **Fire-Origin Worst-Case Testing** page from the Streamlit sidebar.

The page provides:

- dropdown for predefined worst-case scenarios
- custom fire origin selector
- smoke affected node selector
- blocked node selector
- blocked edge selector
- high-risk edge selector
- occupancy multiplier slider
- pre-movement delay slider
- block nearest/affected exit toggle
- Run Worst-Case Simulation button
- Auto-rank Worst Fire Origins button
- room-by-room evacuation table
- route comparison table
- compliance-oriented screening table
- graph visualisation
- JSON, CSV and HTML report export

## Auto-ranking Worst Fire Origins

The engine can test each room/corridor as a possible fire origin and rank the results by:

- trapped rooms
- affected occupants
- unavailable exits
- average delay increase
- overall hazard-priority score (higher means higher screening priority)

This helps identify the most severe fire-origin assumptions in the demo building.

## Exports

The worst-case UI exports:

- JSON scenario result
- CSV room-by-room result
- HTML worst-case fire-origin report

The export includes:

- selected fire scenario
- fire origin
- smoke affected areas
- blocked nodes/edges
- affected exits
- trapped rooms
- room-by-room results
- hazard-priority score, direction metadata and screening-priority level
- auto-ranked worst fire origins, if generated
- session-scoped research review notes, if available
- limitations and disclaimer

## Limitations

This model is intentionally simplified:

- It does not perform CFD.
- It does not simulate smoke temperature, toxicity, visibility or FED exposure.
- It does not simulate detailed crowd behaviour or panic dynamics.
- It is not a replacement for FDS, CFAST, Pathfinder, MassMotion, STEPS or professional fire engineering judgement.
- It uses graph penalties and blocked nodes/edges as an indicative screening method.
- All outputs require qualified review; any saved UI disposition is a session-scoped research record, not approval.

Preferred academic wording:

> This prototype provides fire-origin-based worst-case evacuation screening using BIM-derived graph connectivity. It identifies smoke-affected routes, blocked evacuation routes, trapped rooms, alternative route availability and indicative decision-support risk levels. It does not provide certified evacuation design or final legal compliance approval.
