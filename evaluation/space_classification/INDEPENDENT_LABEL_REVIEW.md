# Independent Space-Use Label Review

## Current status

Workflow available; independent labels not yet supplied.

The existing classifier experiment uses transparent rule-seeded silver labels.
Those labels cannot support runtime promotion because they are not independent
ground truth. The review pack removes the silver-label and matching-rule columns
before handoff.

## Browser workflow

1. Run an IFC analysis and open `Research Review`.
2. Expand `Independent ML Label Review`.
3. Download the blinded CSV.
4. Obtain any required supervisor/ethics confirmation before involving a person.
5. Have the reviewer complete `independent_label`, `reviewer_confidence`,
   `reviewer_confirmation_reference` and set `review_status` to
   `reviewer_confirmed` for every row.
6. Upload the completed CSV in the same panel and retain the validation result.

## Command-line workflow

```bash
python scripts/create_space_label_review_pack.py
python scripts/validate_space_label_review_pack.py \
  outputs/space_label_review/independent_label_review.csv
python scripts/evaluate_space_classifier.py \
  --dataset outputs/space_label_review/independent_label_review.csv \
  --label-field independent_label \
  --report outputs/space_label_review/independent_label_evaluation.json
```

The validator is expected to fail on the newly generated blank pack. Do not fill
the pack by copying the silver labels. Reviewer identity and competence are not
verified by software, and a strong metric alone does not establish
fire-engineering validity.
