# Montebello Technical Verification

Verification date: 8 August 2026

Test subject: `11134_V_Motebello_Heistopp_Rev.ifc`

## Defensible Conclusion

The application processes the exact IFC payload successfully and does not use
the demonstration dataset as a fallback. All eight operational acceptance
gates pass: payload opening, provenance, extraction, graph construction,
scenario traceability, regulation application, export reconciliation and
explicit inference labelling.

The same result must not be described as a verified evacuation model. The IFC
contains no semantic rooms, doors or space boundaries. Its geometry can support
an interactive exploratory diagram, but it cannot prove real room-to-door
connectivity or final exits. The software now reports these two facts separately:

- **Operational processing readiness: 100/100**
- **Engineering evidence quality: 0/100**

That separation is intentional. It proves the code path works while preventing
an unsafe or academically weak claim about evidence that does not exist in the
source file.

## Exact Source Evidence

| Property | Measured result |
|---|---:|
| File size | 109,324 bytes |
| SHA-256 | `d0dd573388317907e6aa59f86319b5408306f0dbe9feea99cb7b83ed1d62ba3a` |
| Schema | IFC2X3 |
| IFC entities | 1,624 |
| Raw `IfcBuildingElementProxy` | 19 |
| Raw `IfcBuildingStorey` | 1 |
| Raw `IfcSpace` | 0 |
| Raw `IfcDoor` | 0 |
| Raw `IfcRelSpaceBoundary` | 0 |
| Unique geometry nodes screened | 16 |
| Inferred connectors / egress | 17 / 2 |
| Graph nodes / edges | 33 / 32 |
| Verified / inferred graph edges | 0 / 32 |
| Nodes without route to egress | 0 |
| Generated exploratory scenarios | 16 |
| Scenario confidence | 0.15 |

The element labels in the scenarios come from the uploaded IFC, including
`Betonfertigteil`, `Evt type` and numbered `IfcBuildingElementProxy` objects.
They are not synthetic office-room names.

## Acceptance Gates

| ID | Requirement | Result |
|---|---|---|
| G1 | Real IFC payload opens in IfcOpenShell | PASS |
| G2 | Filename and SHA-256 survive the pipeline | PASS |
| G3 | Uploaded IFC produces analyzable geometry | PASS |
| G4 | NetworkX graph produces routes to egress | PASS |
| G5 | Every scenario exports path, reliability and decision trace | PASS |
| G6 | Uploaded regulation text is parsed and applied | PASS |
| G7 | Pipeline, JSON and CSV scenario counts reconcile | PASS |
| G8 | Every inferred route is explicitly bounded and review-labelled | PASS |

Generated local evidence:

```text
outputs/montebello_hardening/verification/verification_report.json
outputs/montebello_hardening/verification/verification_report.md
outputs/montebello_hardening/verification/exports/scenarios.json
outputs/montebello_hardening/verification/exports/scenarios.csv
```

## Regulation Verification

The practical ADB input produced:

- 15 parsed clauses;
- 10 extracted numeric rules;
- 5 supported rule candidates;
- 3 active uploaded thresholds;
- 5 explicitly unsupported scope-dependent rules.

The active rules are 18 m for single-direction travel, 45 m for alternative
travel and a conservative 1.05 m fixed exit-width screening candidate. Values
converted from millimetres are now exported with the normalized unit `m`.

Direct-distance rules are not applied to graph travel distance. Small-premises
rules are not applied until the building scope is confirmed. Those five rules
remain visible as unsupported instead of silently changing the calculation.

Format checks in the clean Python 3.10 environment also verified:

| Input | Extracted text | Clauses | Numeric rules |
|---|---:|---:|---:|
| Practical ADB TXT | 9.7 KB source | 15 | 10 |
| ADB PDF | 486,358 characters | 426 | 12 |
| FAQ DOCX | 8,444 characters | 8 | 0 |

The zero-rule DOCX result is a safety behavior: the text loads, but the parser
does not invent thresholds when it cannot identify supported numeric rules.

## Requirement Traceability

| Project requirement | Implementation evidence | Status |
|---|---|---|
| Real uploaded IFC only | filename + SHA-256 in result/export | Implemented |
| IFC2X3/IFC4/IFC4X3 parsing | multi-file compatibility matrix | Implemented with per-file limitations |
| Spatial route graph | NetworkX node/edge and route diagnostics | Implemented |
| Regulation TXT/PDF/DOCX | document loader and real-file checks | Implemented |
| Explainable scenarios | deterministic decision trace and factor breakdown | Implemented |
| Black-box control | rule source, route evidence, confidence and assumptions | Implemented |
| Scenario details UI | executable open/close/inline rendering test | Implemented |
| Manual expert corrections | apply/reset interaction and provenance tests | Implemented |
| JSON/CSV exports | count and provenance reconciliation | Implemented |
| Fire and worst-case pages | executable Streamlit interaction tests | Implemented as simplified screening |
| CFD/certified legal approval | outside prototype scope | Explicitly not claimed |

## Review Answers

### Why does it run so quickly?

It does not call an LLM, CFD solver or agent. IfcOpenShell opens 1,624 IFC
entities, the bounded geometry routine keeps 16 unique proxy bounds, NetworkX
searches a 33-node/32-edge graph, and deterministic formulas calculate route,
compliance, risk and confidence. The measured end-to-end runtime is about 0.2
seconds on the test machine.

### What AI is used?

spaCy supports regulation sentence/clause analysis. Stable keyword retrieval
grounds checks in uploaded text; optional SentenceTransformers/FAISS retrieval
is disabled in the deployment by default. Route search, compliance, risk and
confidence are deterministic algorithms, not neural predictions.

### How is the black box handled?

There is no hidden model making the final decision. Every scenario records the
source hash, extraction mode, route path, edge sources, verified/inferred edge
counts, selected regulation thresholds, evidence snippets, score factors,
assumptions, confidence cap and expert review state.

### Why is Montebello not a verified evacuation model?

Because its IFC payload has zero `IfcSpace`, zero `IfcDoor` and zero
`IfcRelSpaceBoundary` entities. Software cannot recover authoritative room and
door semantics that were never exported. Treating the inferred spanning graph
as legal evacuation evidence would be technically wrong.

### How do we prove the demo dataset was not substituted?

The result and exports retain the exact uploaded filename and SHA-256. Scenario
origin labels match real IFC proxy names. The practical verifier compares the
pipeline fingerprint with a fresh hash of the source and fails G2 on mismatch.

## Reproduction

```bash
python scripts/verify_practical_workflow.py \
  /path/to/11134_V_Motebello_Heistopp_Rev.ifc \
  --regulations /path/to/Practical_ADB_Volume2_Regulation_Input_for_BIM_Evacuation.txt \
  --output outputs/montebello_hardening/verification \
  --max-scenarios 20
```

This is an academic, expert-reviewed screening workflow. It is not legal advice,
certified evacuation modelling or fire-strategy approval.
