# Research Evaluation Results

Evaluation date: 16 August 2026

## Result summary

| Evaluation | Result | Defensible conclusion |
|---|---:|---|
| Controlled IFC ground truth | All 15 checks pass; entity, area, width, connection, exit and route metrics = 1.000 | Parser and graph reproduce the project-declared controlled topology exactly. This is software ground truth, not independent engineering validation. |
| Real IFC compatibility | 1 controlled pass, 4 real partial, 0 fail | Real files process without crashing, but all retain source-evidence limitations. |
| Connectivity before/after | disconnected spaces 28 to 22; spaces without exit route 62 to 56 | Bounded proximity recovery improves coverage while retaining inferred provenance. |
| Space-use deterministic baseline | accuracy 0.8364; macro-F1 0.8968 | Transparent expanded keywords fit the silver-label taxonomy well. |
| Space-use ML experiment | accuracy 0.2897; macro-F1 0.0992 | The TF-IDF/logistic model does not generalise across the two model families and must not replace the deterministic default. |
| Demo regulation TF-IDF retrieval | Recall@1 1.000; Recall@3 1.000; MRR 1.000 | Works on the authored demo benchmark; likely optimistic because queries were source-aware. |
| Practical regulation TF-IDF retrieval | Recall@1 0.8421; Recall@3 0.9474; MRR 0.9000 | Outperforms sentence embeddings at rank 1 on this bounded input, supporting the lightweight deployed default. |
| Practical regulation embeddings | Recall@1 0.7368; Recall@3 0.9474; MRR 0.8526 | No evidence to enable embeddings by default. |
| Scenario expected cases | 6/6 pass, repeatable on duplicate execution | Declared deterministic behavior is stable; physical calibration is not established. |
| Custom UI contrast pairs | minimum 6.31:1 | Selected custom palette pairs exceed the 4.5:1 normal-text target; this is not full WCAG certification. |

## Research interpretation

The experiment implements the proposal's ML comparison without forcing ML into
the deployed system. The negative grouped-validation result is important: random
row splitting across related Duplex exports would create leakage and could make a
weak model appear stronger. Family-level holdout shows that two building families
are insufficient for generalisation.

Regulation processing is also bounded precisely. spaCy assists segmentation,
patterns extract supported numeric candidates, TF-IDF retrieves evidence, and
deterministic checks apply a supported subset. No LLM interprets law or generates
compliance decisions.

## Remaining limits

- Silver labels and retrieval relevance judgements require project-author review
  and are not independent expert ground truth.
- Qualified fire-engineering review is not executed.
- Real IFC partial results cannot be converted to verified routes without source
  semantics or documented human correction.
- Fire/smoke and ASET/RSET models are illustrative and uncalibrated.
- Browser-only keyboard, focus, zoom and screen-reader checks are not signed off.

Reproduction command:

```bash
python scripts/run_research_evaluation.py --output-dir outputs/research_evaluation
```

Add `--practical-regulations PATH --include-embeddings` to reproduce the local
practical-document comparison when the supplied file and optional dependencies
are available.
