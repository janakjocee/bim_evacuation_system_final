# Report Revision Pack

This pack supplies evidence-backed content for the dissertation source document.
It does not replace the mandatory clean export and full proofreading pass.

## Replace the AI implementation description

> The deployed prototype is deterministic and AI/NLP-assisted rather than an
> autonomous AI decision-maker. IfcOpenShell extracts BIM entities and quantities;
> NetworkX performs graph routing; spaCy and pattern rules segment and extract a
> supported subset of regulation constraints; evaluated TF-IDF retrieval attaches
> source evidence; and explicit formulas generate traceable screening outputs. No
> generative LLM, CFD solver, trained route predictor or statutory-compliance model
> makes the final decision.

## Add the ML experiment result

> A genuine space-use text-classification experiment was evaluated on 214 labelled
> IfcSpace metadata records from two building families. Related Duplex exports were
> held in the same family to prevent train-test leakage. Under leave-one-family-out
> validation, TF-IDF plus class-balanced logistic regression achieved 0.2897
> accuracy and 0.0992 macro-F1, below the expanded deterministic baseline (0.8364
> accuracy; 0.8968 macro-F1). The learned model was therefore not promoted to the
> runtime. Labels were rule-seeded silver labels, not independent expert ground
> truth, which further limits the claim.

## Add the retrieval comparison

> On 16 authored queries against the bundled demo document, TF-IDF retrieval
> achieved Recall@1/Recall@3/MRR of 1.000/1.000/1.000. On 19 queries against the
> supplied practical ADB-derived text, TF-IDF achieved 0.8421/0.9474/0.9000,
> compared with 0.7368/0.9474/0.8526 for sentence embeddings. These source-aware,
> Codex-assisted relevance judgements are not legal or expert validation. The
> evidence supports TF-IDF as the lightweight default for this prototype only.

## Add IFC and scenario evaluation

> A deterministic IFC4 fixture with three spaces, three doors and five declared
> door-space relationships achieved exact entity, measurement, connectivity, exit
> and route recovery. A six-case scenario benchmark passed all expected outcomes
> on repeated execution. Four real IFC payloads remained partial: parser recovery
> reduced disconnected spaces from 28 to 22 and spaces without exit routes from 62
> to 56, while every recovered relationship remained labelled inferred. Controlled
> fixture success demonstrates regression correctness, not real-building validity.

## Objective 5 conclusion

Use this wording unless qualified review is completed:

> Objective 5 is achieved within the declared researcher-led software and
> controlled-prototype evaluation scope. Software behavior, controlled
> parser/route correctness, deterministic repeatability, bounded retrieval
> relevance, robustness, explainability and selected UI accessibility properties
> were evaluated. Fire-engineering correctness, physical calibration, statutory
> interpretation and professional usability remain unvalidated because no
> qualified domain review or independent real-building ground truth was completed.

## Mandatory removal or qualification

- Remove claims of advanced ML in the deployed runtime.
- Replace autonomous RAG/regulatory reasoning with regulation evidence retrieval.
- Do not call partial IFC routes verified, real rooms when geometry-derived, or
  compliant because implemented checks passed.
- Do not claim expert validation, accessibility compliance, legal validity, CFD,
  casualty prediction or professional readiness.
- Preserve the proposal's five objectives verbatim and explain the evidence-driven
  change from proposed ML to a deterministic runtime.
- Export a clean PDF without comments, tracked-change balloons, placeholders or
  inconsistent figure/table numbering before submission.
