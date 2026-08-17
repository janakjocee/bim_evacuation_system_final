# Final Repository Audit

Audit date: 17 August 2026

Audited release: `8485250` (`main`, PR 31)

## Verdict

The repository is submission-ready as an academic research prototype and is
operationally ready for a supervised demonstration. It is not production-ready
fire-engineering software, a certified evacuation simulator, a CFD model, or a
legal compliance approval system.

This verdict is deliberately narrower than "everything is perfect". The code,
tests, deployment workflow and practical file paths are working, while the
remaining engineering and research limitations are explicitly recorded below.

## Executable Verification

- Full test suite: **139 passed, 3 skipped, 0 failed**. The skipped tests require
  an optional real Montebello IFC fixture that is intentionally not committed.
- Source coverage: **84%** across `src` (5,217 statements; 858 missed).
- Python compilation: all files under `src`, `pages`, `scripts` and `tests`
  compiled successfully.
- Streamlit AppTest: the main application, Fire Scenario Testing and Worst Case
  Testing entry points all started without exceptions.
- Streamlit control matrix: scenario details, manual corrections, review
  controls, exports, fire controls and worst-case controls passed.
- GitHub Actions: post-merge workflow
  [`32034743310`](https://github.com/janakjocee/bim_evacuation_system_final/actions/runs/32034743310)
  completed successfully for release commit `8485250`.

## Security And Dependency Checks

- `pip check`: no broken installed requirements.
- Bandit medium/high scan over `src`, `pages` and `scripts`: no findings.
- `pip-audit` using the project's required Python 3.10: no known
  vulnerabilities in `requirements.txt`.
- The separately hosted `en-core-web-sm` wheel could not be checked against the
  PyPI advisory index because it is not a PyPI dependency.
- No committed environment files, Streamlit secrets, private keys or common API
  token patterns were found.

## Practical IFC Results

### Montebello

`11134_V_Motebello_Heistopp_Rev.ifc` processed successfully with the practical
ADB text input:

- IFC schema: IFC2X3;
- extraction mode: `geometry_derived`;
- screened elements: 16;
- inferred route links: 17;
- inferred exits: 2;
- generated scenarios: 10;
- operational verification gates: G1-G8 passed;
- processing readiness: 100/100;
- engineering evidence: 0/100.

The correct interpretation is therefore **operational pass with review
limitations**, but **exploratory only, not a verified evacuation model**.
Montebello does not provide the semantic room/door topology needed to support a
professional evacuation-design claim.

### Local public-file folder

The seven entries in `Downloads/real_public_ifc_files` produced:

- 3 failures: the IFC2X3 Duplex/Clinic entries are 132-133 byte Git LFS pointer
  files, not IFC payloads;
- 4 partial results: the IFC4, IFC4X3_ADD2 and IFC4X1 files generated scenarios,
  but topology, exits, widths or areas were inferred;
- 0 full engineering passes in that seven-entry folder.

The application correctly explains these limitations instead of silently
substituting demonstration data.

The repository's committed compatibility matrix remains a reproducible evidence
snapshot containing one controlled semantic pass and four real partial models.
Historical 23-path results are retained as historical evidence, not presented
as the latest local-folder result.

## Regulation Document Verification

The 3.5 MB Approved Document B PDF in Downloads was read directly:

- extracted characters: 486,358;
- extracted words: 76,347;
- parsed clauses: 426;
- structured numeric rules: 12;
- retrieval mode: `tfidf_lexical`;
- Montebello scenarios generated with the PDF: 3;
- measured pipeline time: 8.5 seconds on the audit machine.

Parsing and retrieval do not determine legal applicability. Jurisdiction,
edition, amendments, building type and every applied rule still require expert
source verification.

## Research Evidence Boundary

The reproducible research evaluation passed its implemented gates, with two
material limitations preserved in the output:

- controlled IFC ground truth is not independently validated;
- the learned space-use classifier did not satisfy its runtime promotion gate.

The deterministic classifier therefore remains the runtime default. The
demonstration scenario dataset is labelled `demonstration_only`, and regulation
judgements remain project-author claims requiring review.

## Deployment Boundary

The Streamlit Cloud URL is authentication-gated. Unauthenticated requests to
both `/` and `/_stcore/health` redirect to Streamlit sign-in. GitHub CI and local
Streamlit execution are green, but an unauthenticated external audit cannot
inspect the rendered production DOM. Sign-in availability and a local fallback
must be checked before the live demonstration.

## Remaining External Work

These are not code defects that can honestly be marked complete without human
or third-party evidence:

1. Obtain the real Git LFS payloads for the three IFC2X3 pointer files before
   treating them as compatibility samples.
2. Complete independent space-label review; do not promote the ML classifier
   using project-authored silver labels.
3. Obtain qualified fire-safety domain review of assumptions, extracted rules,
   inferred routes and scenario interpretation.
4. Complete and record manual accessibility checks with assistive technology
   and representative browsers.
5. Use semantic IFC room, door, exit and connectivity data for any claim beyond
   exploratory geometry screening.

No further code change was justified by this audit after the stale evidence
wording was corrected. Adding features now would increase submission risk more
than it would improve the validated research claim.
