# Proposal, Product and Report Alignment Audit

Audit date: 16 August 2026

Inputs reviewed:

- approved project proposal `PgProposalTemplate.docx`;
- final report draft `msc final report .pdf` (71 PDF pages);
- `MScProject_Marking Scheme 2025_26.docx`;
- repository state starting from `main` commit `67aeaad` (PR 25);
- executable tests, a practical Montebello run and the 23-path IFC corpus.

## Final Decision

The project meets the approved aim at **academic research-prototype level**, but
not at professional fire-engineering validation level. All five approved
objectives have implemented deliverables. Objective 5 is achieved only within
the declared researcher-led software and controlled-prototype evaluation scope:
controlled parser/route ground truth, grouped ML comparison, retrieval metrics,
scenario repeatability and UI tests are implemented. Engineering correctness,
professional relevance and usability remain unvalidated by a qualified reviewer.

The product is credible for a demonstration when presented as deterministic,
AI/NLP-assisted evacuation **screening**. The current report PDF is not ready to
submit: it contains visible supervisor comments and revision markup,
placeholders, inconsistent numbering and claims that exceed the evidence.

## Approved Title Alignment

The immutable approved title is:

> AI-Driven Generation of Evacuation Scenarios from Building Information Models

The report cover, README, Streamlit browser title, visible application header and
package metadata now use that exact title. The adjacent subtitle defines the
implemented boundary as an AI-assisted research prototype using deterministic
IFC/graph analysis and NLP evidence retrieval. This preserves proposal identity
without implying an autonomous LLM, learned route planner or certified safety
decision-maker.

## Approved Aim And Objectives (Verbatim)

**Aim:** To design, develop, and critically evaluate an AI-assisted system
capable of suggesting evacuation scenarios from BIM data.

1. To conduct a critical review of the relevant literature related to BIM-based
   evacuation planning, AI-assisted decision-support systems, Machine Learning,
   NLP, and relevant building safety regulations.
2. To analyse the requirements of the proposed system, focusing on the
   identification of evacuation-relevant elements and regulatory constraints.
3. To design a system that meets the identified requirements, integrating BIM
   data analysis with regulation-informed reasoning.
4. To develop and implement the proposed system and a user-friendly interface
   for expert users.
5. To evaluate the system through testing.

These statements must appear verbatim in the report before any refined research
tasks or implementation-specific sub-objectives.

## Approved-Objective Traceability

| Objective | Evidence in the product/report | Status | Required final wording/action |
|---|---|---|---|
| O1: critically review BIM evacuation, AI decision support, ML, NLP and safety regulations | Literature chapter, comparison table and current references | Mostly achieved | Deepen critical synthesis, explicitly derive the research gap and evaluation criteria; do not merely describe sources. |
| O2: identify exits, doors, areas, spatial relations, functional/non-functional requirements and ML/NLP features | IfcOpenShell parser, readiness diagnostics, feature extractor, requirements/design chapters | Achieved with IFC-data limitations | Distinguish verified IFC semantics from inferred geometry. State that missing semantics cannot be reconstructed as fact. |
| O3: design BIM plus regulation reasoning, select algorithms and define JSON/XML outputs | Layered architecture, NetworkX routing, deterministic rule checks, JSON/CSV/XML exports and evidence trace | Achieved for a prototype | Describe JSON/XML as output schemas and retrieval as evidence support, not autonomous regulatory reasoning. |
| O4: implement backend, scenario logic and expert review/selection/export UI | Streamlit app, scenario details, corrections, exports, fire and worst-case pages | Achieved for a prototype | Demonstrate the complete workflow and keep fire/worst-case outputs labelled as screening models. |
| O5: evaluate relevance, correctness, explainability and critically compare against objectives | 136 tests, 85.44% `src/` line coverage, controlled ground truth, grouped ML/retrieval/scenario evaluations, multi-IFC diagnostics, provenance and decision traces | Achieved at controlled research-prototype scope | Say controlled software correctness, behaviour, bounded relevance and explainability were evaluated. Say engineering correctness/relevance remain unvalidated without qualified review or independent real-building ground truth. |

## What The System Actually Does

The default deployed workflow is deterministic:

1. IfcOpenShell reads IFC entities and properties.
2. NetworkX builds a graph and computes shortest available paths.
3. Regex-based parsing extracts supported numeric regulation candidates; spaCy
   provides sentence segmentation when its model is available.
4. Explicit formulas and checks create screening scenarios and evidence scores.
5. Evaluated TF-IDF retrieval attaches source clauses in the deployed configuration.
6. The UI exposes source mode, assumptions, rule provenance, score direction,
   decision traces and manual-review records.

There is now a genuine project-specific space-use ML experiment, but it is not
deployed: grouped macro-F1 was 0.0992 versus 0.8968 for the deterministic
baseline. There is no learned route prediction or LLM generating compliance
decisions. SentenceTransformers retrieval was compared with TF-IDF and remains
disabled because it did not improve the practical benchmark. "Evidence
retrieval" is more precise than autonomous RAG.

## Reproduced Evidence

| Check | Reproduced result | Meaning |
|---|---|---|
| Full pytest suite with real Montebello IFC | 136 passed, 0 failed, 0 skipped | Final expanded automated behavior suite is green. |
| Controlled IFC ground truth | Exact recovery across entities, areas, widths, connections, exits and routes | Project-declared software ground truth passes; it is not independent engineering validation. |
| Space-use classifier | ML macro-F1 0.0992; deterministic baseline 0.8968 | ML is implemented and honestly rejected as runtime default. |
| Regulation retrieval | Practical TF-IDF Recall@1 0.8421, Recall@3 0.9474, MRR 0.9000 | Bounded source-aware benchmark supports TF-IDF; relevance labels require author review. |
| Scenario benchmark | 6/6 cases pass twice with identical normalized outcomes | Deterministic expected behavior is repeatable, not physically calibrated. |
| Coverage | 85.44% line coverage for the production `src/` package (4,396/5,145 statements; 85% displayed) | Good prototype coverage; standalone scripts, external format variation and optional embedding error paths remain residual risk. |
| GitHub Actions | `main` workflow passed through PR 25 (`67aeaad`) | The checked-in deployment smoke workflow is green. |
| Hosted Streamlit access | `/` and `/_stcore/health` redirect unauthenticated clients to Streamlit login | Deployment is authentication-gated; this is not evidence of public availability or an app crash. |
| Montebello IFC2X3 | 8/8 workflow gates; 16 geometry proxies, 17 inferred connectors, 2 inferred exits, 16 scenarios | Operationally processable, but exploratory because room/door topology is absent. |
| Regulation text | 15 clauses, 10 candidate rules, 3 supported uploaded thresholds applied | Unsupported candidates are reported rather than silently treated as law. |
| Corpus by input path | 18 partial, 5 fail, 0 strict pass | Same path-level result as the report. |
| Corpus by SHA-256-unique payload | 12 partial, 4 fail, 0 strict pass across 16 unique payloads | The 23 paths are not 23 independent models. |

The full Duplex and Clinic payloads are useful semantic tests but remain
partial: bounded inferred recovery reduced Duplex to 1 space without an exit
route and Clinic to 55. The three
tiny IFC2X3 files are Git LFS pointers, not real IFC model contents. Two failed
wall/opening filenames contain the same minimal topology-free payload.

## Post-Audit Gap-Closure Workflows

The product now makes the three outstanding human-evidence activities
executable and auditable:

- `Structured Preliminary Domain Review` records governance reference,
  competence scope, cases, ratings, findings, corrections, disposition and
  sign-off reference;
- `Manual Accessibility Verification` records browser/OS, pass/fail/not-tested
  outcomes, notes and retained-evidence reference;
- `Independent ML Label Review` downloads a blinded 214-row CSV, validates a
  completed upload and prevents silver labels from satisfying the runtime
  promotion gate.

Execution remains incomplete: no qualified review record, completed manual
accessibility record or independent label pack has been supplied. These
workflows close an implementation gap, not the external-evidence gap.

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
   State that O5 is achieved for researcher-led software and controlled-prototype
   evaluation, while professional and engineering validation remains incomplete.
4. Replace broad "advanced ML" claims with the exact implementation boundary in
   this audit. Explain why deterministic and traceable methods were selected for
   a safety-critical prototype.
5. Change "23 IFC models" to "23 input paths representing 16 unique payloads";
   report both path-level and unique-payload results.
6. Separate software verification from engineering validation. Tests and
   coverage do not demonstrate scenario correctness, regulatory compliance or
   real-world safety.
7. Add the latest reproducibility facts: 136 tests, 85.44% `src/` line coverage, current
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
| Build and evaluation | Working UI, real IFC diagnostics, 136 tests, controlled strict-pass fixture, grouped ML/retrieval/scenario evaluations, coverage, CI and limitations | No qualified expert evaluation, independent real-building ground truth, completed browser accessibility sign-off or engineering validation. |
| Conclusions and critical review | Limitations and future work are acknowledged | Must be more explicit about mistakes, changed plans, failed approaches and how evidence changed the claims. |
| Report presentation | Logical chapter structure and declared word count within the nominal band | Visible comments/markup, placeholders, numbering and residual language errors are submission blockers. |

These gaps make a distinction-level claim difficult to defend today. Correcting
the report can materially improve presentation and critical reflection, but it
cannot honestly replace missing external engineering validation.

## Immediate Evidence Work

- Use the official GOV.UK Approved Document B source with recorded URL, edition,
  jurisdiction, access date, SHA-256 and a human applicability decision. A
  collated PDF can contain future-dated or transitional provisions that the
  prototype does not resolve automatically.
- Add Hugging Face IFC models to the reported evaluation corpus only after the
  dataset revision, licence, attribution, model hash and source-family identity
  are recorded. Use unverified models for local robustness testing only.
- Prefer IFCZIP for compressible STEP-text models, but enforce the 200 MB limit
  on both the upload and its uncompressed IFC payload. Larger models require a
  deployment with memory measured under realistic parsing and geometry loads.
- The seven provenance-pending Hugging Face files now produce seven partial and
  zero failed diagnostics. This demonstrates parser robustness, not engineering
  correctness: all seven still depend on inferred topology or have unresolved
  disconnected spaces, and none is a strict verified pass.

## Recommended Demo Sequence

1. State the boundary: decision-support screening, not certification.
2. Sign in to Streamlit before the review and keep the tested local command as
   a fallback because the hosted app is authentication-gated.
3. Upload the full Duplex or Clinic IFC to show semantic spaces/doors and honest
   disconnected-route diagnostics.
4. Upload Montebello to demonstrate safe degradation; point out that geometry
   proxies and exits are visibly labelled inferred.
5. Upload the selected regulation file; show extracted, supported, applied and
   unsupported rule counts and one rule's source text.
6. Open Scenario View Details; explain route evidence, assumptions, score
   direction and confidence ceiling.
7. Apply a manual correction, regenerate and show the recorded before/after
   review information.
8. Download JSON, CSV, XML and the IFC-derived fire dataset, then reconcile one
   scenario ID and source hash across exports.
9. Open Fire Scenario Testing and Worst Case Testing; explain ASET/RSET and
   comparative ranking assumptions without calling either a certified model.
10. Finish with the 23-path/16-payload matrix and the remaining validation plan.

## Concise Viva Answers

**What is the AI?**  The delivered default is an AI/NLP-assisted but
deterministic pipeline. spaCy helps segment regulatory text, explicit parsers
extract supported rules, evaluated TF-IDF supplies evidence, and graph/rule
algorithms generate traceable screening results. A space-use ML experiment was
implemented but rejected after grouped validation; no generative LLM or trained
route-prediction model makes decisions.

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
