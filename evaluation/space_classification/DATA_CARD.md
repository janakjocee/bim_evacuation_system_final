# IFC Space Classification Dataset Card

## Purpose

This dataset supports a bounded MSc experiment comparing the current deterministic
IFC room-name classifier with a TF-IDF/logistic-regression classifier. It does not
train or validate an evacuation-safety decision model.

## Sources and licence

Rows are metadata extracted from three buildingSMART community sample models:

- `Duplex_A_20110907.ifc`
- `Duplex_Rooms_And_Spaces.ifc`
- `Clinic_Architectural.ifc`

The upstream repository is `buildingSMART/Sample-Test-Files` and declares the
sample files under CC BY 4.0. The source URLs and exact SHA-256 values are recorded
in `docs/ifc_corpus_provenance_20260816.md`. Raw IFC payloads are not committed.

## Labels

`silver_label` values were seeded by the explicit keyword codebook in
`src/evaluation/space_classification.py`. Their provenance is
`codex_assisted_rule_seeded_silver`; they are not independent human ground truth.
Every row remains `requires_project_author_review`.

The Research Review tab and `scripts/create_space_label_review_pack.py` create a
blinded CSV that omits the silver-label and matching-rule columns. The completed
pack must pass `scripts/validate_space_label_review_pack.py` before it can be
used as reviewer-supplied evaluation data.

## Leakage control

Both Duplex exports use the same `duplex` family. Evaluation holds out an entire
source-model family at a time, preventing the duplicate/related Duplex metadata
from appearing in both training and test folds.

## Limitations

- Two building families are insufficient for a generalisable model claim.
- Rule-seeded labels create construct-validity and confirmation-bias risk.
- Some room names are ambiguous; unmatched names are excluded.
- A qualified reviewer must approve or correct labels before they can be described
  as independently validated ground truth.
- Runtime promotion additionally requires validator-complete reviewer labels,
  at least three source-model families, macro-F1 of at least 0.70, performance
  above the deterministic baseline and no unseen test classes in any held-out
  family. Silver-label results can never pass this gate.
