# Regulation Retrieval Benchmark Card

The benchmark contains researcher-authored queries and expected clause identifiers.
It stores no external regulation text.

- `sample_demo` targets the bundled simplified demonstration text. It is synthetic
  demo material and is not an authoritative regulation source.
- `practical_adb` targets the locally supplied, simplified ADB-derived input. The
  report records its SHA-256 but does not commit or reproduce its text.

The expected relevance judgements were authored with Codex assistance and require
project-author review. They are not fire-engineer judgements. Metrics evaluate
retrieval of a declared paragraph, not correctness of legal interpretation.

Query wording was created after viewing the documents, so results may overestimate
performance on unseen user queries. The runtime must continue to display source
text and require expert review.
