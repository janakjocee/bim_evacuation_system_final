# Proposal, Product and Report Alignment Audit

Audit date: 16 August 2026

Inputs reviewed:

- approved project proposal `PgProposalTemplate.docx`;
- final report draft `msc final report .pdf` (71 PDF pages);
- `MScProject_Marking Scheme 2025_26.docx`;
- repository `main` at `5975962` plus the audit changes described here;
- executable tests, a practical Montebello run and the 23-path IFC corpus.

## Final Decision

The project meets the approved aim at **academic research-prototype level**, but
not at professional fire-engineering validation level. Objectives 1-4 are
substantially met. Objective 5 is **partially met** because the software has
been tested for behaviour, robustness and traceability, but scenario relevance
and engineering correctness have not been validated against ground truth or by
a qualified fire engineer.

The product is credible for a demonstration when presented as deterministic,
AI/NLP-assisted evacuation **screening**. The current report PDF is not ready to
submit: it contains visible supervisor comments and revision markup,
placeholders, inconsistent numbering and claims that exceed the evidence.

## Approved-Objective Traceability

| Objective | Evidence in the product/report | Status | Required final wording/action |
|---|---|---|---|
| O1: critically review BIM evacuation, AI decision support, ML, NLP and safety regulations | Literature chapter, comparison table and current references | Mostly achieved | Deepen critical synthesis, explicitly derive the research gap and evaluation criteria; do not merely describe sources. |
| O2: identify exits, doors, areas, spatial relations, functional/non-functional requirements and ML/NLP features | IfcOpenShell parser, readiness diagnostics, feature extractor, requirements/design chapters | Achieved with IFC-data limitations | Distinguish verified IFC semantics from inferred geometry. State that missing semantics cannot be reconstructed as fact. |
| O3: design BIM plus regulation reasoning, select algorithms and define JSON/XML outputs | Layered architecture, NetworkX routing, deterministic rule checks, JSON/CSV/XML exports and evidence trace | Achieved for a prototype | Describe JSON/XML as output schemas and retrieval as evidence support, not autonomous regulatory reasoning. |
| O4: implement backend, scenario logic and expert review/selection/export UI | Streamlit app, scenario details, corrections, exports, fire and worst-case pages | Achieved for a prototype | Demonstrate the complete workflow and keep fire/worst-case outputs labelled as screening models. |
| O5: evaluate relevance, correctness, explainability and critically compare against objectives | 104 tests, 79.1% line coverage, CI, multi-IFC diagnostics, provenance and decision traces | Partially achieved | Say software behaviour and explainability were evaluated. Say domain correctness/relevance remain unvalidated without expert or ground-truth comparison. |

## What The System Actually Does

The default deployed workflow is deterministic:

1. IfcOpenShell reads IFC entities and properties.
2. NetworkX builds a graph and computes shortest available paths.
3. Regex-based parsing extracts supported numeric regulation candidates; spaCy
   provides sentence segmentation when its model is available.
4. Explicit formulas and checks create screening scenarios and evidence scores.
5. Keyword retrieval attaches source clauses in the deployed configuration.
6. The UI exposes source mode, assumptions, rule provenance, score direction,
   decision traces and manual-review records.

There is no trained project-specific machine-learning model, no learned route
prediction, no LLM generating compliance decisions and no measured predictive
accuracy. Optional SentenceTransformers/FAISS retrieval is disabled in the
deployed configuration and is not part of the evaluated default result. Calling
the default retriever "RAG" is acceptable only if immediately defined as
retrieval without generative answer production; "evidence retrieval" is more
precise.

## Reproduced Evidence

| Check | Reproduced result | Meaning |
|---|---|---|
| Full pytest suite with real Montebello IFC | 104 passed, 0 failed, 0 skipped | Current automated behaviour is regression-tested. |
| Coverage | 79.1% line coverage (3,831/4,841 statements) | Good prototype coverage; optional retrieval and parser error/variation branches need more tests. |
| GitHub Actions | Latest `main` smoke test passed at `5975962` | The checked-in deployment smoke workflow is green. |
| Montebello IFC2X3 | 8/8 workflow gates; 16 geometry proxies, 17 inferred connectors, 2 inferred exits, 16 scenarios | Operationally processable, but exploratory because room/door topology is absent. |
| Regulation text | 15 clauses, 10 candidate rules, 3 supported uploaded thresholds applied | Unsupported candidates are reported rather than silently treated as law. |
| Corpus by input path | 18 partial, 5 fail, 0 strict pass | Same path-level result as the report. |
| Corpus by SHA-256-unique payload | 12 partial, 4 fail, 0 strict pass across 16 unique payloads | The 23 paths are not 23 independent models. |

The full Duplex and Clinic payloads are useful semantic tests but remain
partial: Duplex has 3 spaces without an exit route; Clinic has 59. The three
tiny IFC2X3 files are Git LFS pointers, not real IFC model contents. Two failed
wall/opening filenames contain the same minimal topology-free payload.

## Claims To Keep And Claims To Change

| Keep | Replace or qualify |
|---|---|
| "AI/NLP-assisted research prototype" | Do not say "AI-driven automated fire-safety solution" without defining the deterministic components. |
| "Generates traceable evacuation screening scenarios" | Do not say it predicts safe evacuation, certifies a route or proves compliance. |
| "Supports IFC2X3, IFC4, IFC4X1 and IFC4X3 syntax through IfcOpenShell" | Do not claim all models in those schema families are compatible; data content and topology determine usefulness. |
| "Montebello can be processed with geometry-derived fallback" | Do not present its proxy nodes, nearest-neighbour links or inferred exits as real rooms, doors or verified egress. |
| "Applies a supported subset of uploaded numeric rules with provenance" | Do not claim full Approved Document B interpretation or legal compliance. ADB scope is England and amendments have effective dates. |
| "Fire and worst-case pages are comparative screening tools" | Do not call them CFD, certified evacuation simulation, calibrated fire prediction or a substitute for professional judgement. |
| "Human review and correction are recorded" | Do not claim expert usability/domain validation; no external expert or participant study was completed. |

## Mandatory Report Corrections

1. Export a clean PDF with all comments, comment balloons, tracked-change marks
   and the grey markup area removed. The current PDF visibly contains supervisor
   comments on multiple pages, including an academic-integrity concern about
   AI-generated text.
2. Replace `XXXXXXXXXXXXX` and `XXXXXXXX` in Acknowledgements and proofread the
   surrounding grammar.
3. Reproduce the five approved objectives verbatim before any refined tasks.
   Mark O5 as partially achieved, not achieved-with-minor-limitations.
4. Replace broad "advanced ML" claims with the exact implementation boundary in
   this audit. Explain why deterministic and traceable methods were selected for
   a safety-critical prototype.
5. Change "23 IFC models" to "23 input paths representing 16 unique payloads";
   report both path-level and unique-payload results.
6. Separate software verification from engineering validation. Tests and
   coverage do not demonstrate scenario correctness, regulatory compliance or
   real-world safety.
7. Add the latest reproducibility facts: 104 tests, 79.1% coverage, current
   commit identifier and the duplicate-aware matrix output.
8. Correct figure/table references and regenerate both lists. Examples in the
   draft mix `Figure 4.1` with `Figure 1`, `Figures 7.1-7.3` with Figures 14-17,
   and `Tables 8.1-8.2` with Tables 11-12.
9. Make the contents-page heading match the chapter heading, fix duplicated
   Objective 3.3 text and `user..`, and standardise front-matter pagination.
10. Complete a consistent Harvard-reference pass and verify every author, title,
    year, DOI/URL and access date. State the exact ADB edition/amendment date used.
11. Add an actual-versus-planned schedule and a short change log explaining why
    the project moved from proposed ML/RAG ambitions to deterministic screening.
12. Use `docs/ifc_corpus_provenance_20260816.md` as the manifest and resolve its
    unverified Clinic, Dormitory and NordicLCA provenance before citing them as
    public/authorised evidence. Otherwise remove those payloads from the claimed
    evaluation corpus. Add equivalent provenance for the regulation input.

## Marking-Scheme Readiness

| Marking area | Current strength | Main risk before submission |
|---|---|---|
| Domain understanding | Relevant BIM/fire-safety sources, explicit scope and requirements | Literature is sometimes descriptive; research gap and comparison-derived criteria need stronger synthesis. |
| Product and ideas | Substantial multi-module implementation and defensible transparent architecture | Alternatives and project-plan changes are thin; proposed ML terminology does not match the delivered default. |
| Build and evaluation | Working UI, real IFC diagnostics, 104 tests, coverage, CI and limitations | No strict-pass model, qualified expert evaluation, ground truth, SUS/accessibility study or engineering validation. |
| Conclusions and critical review | Limitations and future work are acknowledged | Must be more explicit about mistakes, changed plans, failed approaches and how evidence changed the claims. |
| Report presentation | Logical chapter structure and declared word count within the nominal band | Visible comments/markup, placeholders, numbering and residual language errors are submission blockers. |

These gaps make a distinction-level claim difficult to defend today. Correcting
the report can materially improve presentation and critical reflection, but it
cannot honestly replace missing external engineering validation.

## Recommended Demo Sequence

1. State the boundary: decision-support screening, not certification.
2. Upload the full Duplex or Clinic IFC to show semantic spaces/doors and honest
   disconnected-route diagnostics.
3. Upload Montebello to demonstrate safe degradation; point out that geometry
   proxies and exits are visibly labelled inferred.
4. Upload the selected regulation file; show extracted, supported, applied and
   unsupported rule counts and one rule's source text.
5. Open Scenario View Details; explain route evidence, assumptions, score
   direction and confidence ceiling.
6. Apply a manual correction, regenerate and show the recorded before/after
   review information.
7. Download JSON, CSV, XML and the IFC-derived fire dataset, then reconcile one
   scenario ID and source hash across exports.
8. Open Fire Scenario Testing and Worst Case Testing; explain ASET/RSET and
   comparative ranking assumptions without calling either a certified model.
9. Finish with the 23-path/16-payload matrix and the remaining validation plan.

## Concise Viva Answers

**What is the AI?**  The delivered default is an AI/NLP-assisted but
deterministic pipeline. spaCy helps segment regulatory text, explicit parsers
extract supported rules, retrieval supplies evidence, and graph/rule algorithms
generate traceable screening results. It does not use a generative LLM or a
trained route-prediction model.

**Why is it fast?**  It parses structured IFC entities and runs graph algorithms
and formulas locally. It is not training a model or running CFD/agent-based
simulation on each upload.

**How is the black box handled?**  Each result carries input hashes, extraction
mode, verified/inferred edge sources, assumptions, rule provenance, score
components, confidence ceilings and a decision trace. Human corrections and
review state are recorded. The optional embedding retriever only ranks evidence;
it does not decide compliance.

**Why do IFC files behave differently?**  IFC schema compatibility does not
guarantee evacuation semantics. Some files contain `IfcSpace`, doors,
relationships and usable exits; others are structural/HVAC models, minimal
examples or LFS pointers. The system therefore reports strict, partial or failed
evidence instead of fabricating semantic certainty.

**Has correctness been proved?**  No. Software consistency, robustness and
explainability were tested. Fire-engineering relevance and correctness still
require a qualified reviewer and comparison with trusted reference cases or
specialist tools.

## Submission Gate

Do not submit the current PDF. The project demonstration can proceed with the
claim boundary above. Submit only after the twelve mandatory report corrections
are completed, the cleaned PDF is visually checked page by page, and the final
commit/test/evidence identifiers in the report match the repository.
