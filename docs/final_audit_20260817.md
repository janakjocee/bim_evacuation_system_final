# Final Repository Audit

Audit date: 17 August 2026

Audited candidate: `agent/production-hardening`, based on `8eddcbf` (`main`)

## Verdict

The repository is submission-ready as an academic research prototype and is
operationally suitable for a supervised demonstration. This hardening pass
removes known deployment defects and adds production-style controls, but it
does not turn the prototype into certified fire-engineering software, a CFD or
agent-based evacuation simulator, or a legal compliance approval service.

The honest deployment label is **production-hardened research prototype**. A
qualified fire engineer, independent validation data, accessibility testing and
an operating security process are still required before professional use.

## Executable Verification

- Full suite collected **165 tests**: **162 passed** and three optional-fixture
  tests were skipped because the optional Montebello fixture is not committed.
- Source coverage is enforced at **80%** in CI; the final local run reached
  **83.60%** across `src`.
- Python compilation covers all files under `src`, `pages`, `scripts` and
  `tests`.
- Streamlit AppTest covers the main application, Fire Scenario Testing and
  Worst Case Testing entry points.
- The interaction suites exercise scenario details, manual corrections,
  research review controls, JSON/CSV/XML downloads, IFC-derived fire dataset
  export, fire controls and worst-case controls.
- The reproducible research evaluation passes all implemented gates while
  retaining its stated evidence limitations.

## Production Hardening

The application now enforces these controls:

- uploads are streamed in 1 MiB chunks rather than copied into memory as one
  additional buffer;
- IFC/IFCZIP uploads are limited to 200 MiB and regulation uploads to 25 MiB on
  the server side, independent of the browser extension filter;
- partial uploads are atomically renamed only after size validation and SHA-256
  hashing, then removed with the per-run temporary workspace;
- PDF input is bounded by page and extracted-character limits;
- DOCX input is bounded by archive entry count, expanded size, compression
  ratio and extracted-character limits, and encrypted documents are rejected;
- unexpected exceptions receive an opaque run reference in the UI while full
  details remain in server logs;
- uploaded data and review records remain session-scoped unless a user
  explicitly downloads an evidence export;
- Streamlit CORS, XSRF, message-size and file-watcher settings are explicit;
- the Docker image runs as a non-root user and Compose drops Linux capabilities,
  enables `no-new-privileges`, uses a read-only root filesystem and provides a
  bounded writable `/tmp` filesystem;
- the former tokenless Jupyter Compose service has been removed;
- CI enforces test coverage, Bandit medium/high scanning and `pip-audit`;
- Dependabot monitors Python, GitHub Actions and Docker dependencies.

Local Bandit found no medium/high findings. `pip-audit` found no known runtime
vulnerabilities. The separately hosted `en-core-web-sm` wheel is not indexed on
PyPI and is therefore reported as unauditable by that advisory source.

## Regulation Applicability Safeguard

The real Approved Document B PDF exposed an important distinction between rule
extraction and legal applicability. A 1200 mm exit-width value tied to a
240-person table row was previously selected as a conservative global value.
It was disclosed as conditional, but automatic activation was still too strong.

Structured rules are now split into:

1. active thresholds whose condition the checker can evaluate;
2. context-deferred candidates that remain visible but do not override defaults;
3. unsupported metrics that are extracted but not enforced.

Uploaded thresholds are reset for every document, so a previous run cannot leak
into a later analysis. Empty structured-rule results no longer fall back to a
less precise legacy numeric parser. The Regulations tab and exports show active,
deferred and unsupported counts separately.

With the 3.5 MB Approved Document B PDF and Montebello IFC, the corrected run:

- extracted 426 clauses and 12 structured numeric rules;
- activated one general uploaded threshold;
- deferred the occupancy-specific exit-width candidate;
- kept ten unsupported metrics visible with reasons;
- generated 16 traceable scenarios in 9.6 seconds on the audit machine;
- passed operational gates G1-G8.

Parsing and retrieval do not decide jurisdiction, edition, amendments, building
type, transitional provisions or professional applicability.

## Practical IFC Results

### Seven public fixtures

The first audit contained three 132-133 byte Git LFS pointer files and four real
IFCs, producing three failures and four partial results. The exact external
buildingSMART payloads were then recovered and authenticated against their
pinned byte counts and SHA-256 object IDs.

The repeatable command is:

```bash
python scripts/recover_public_ifc_fixtures.py --output-dir data/test_ifc
python scripts/batch_ifc_diagnostics.py \
  --input data/test_ifc \
  --output outputs/ifc_diagnostics
```

After recovery, all seven real payloads opened and generated diagnostics:

- before: 3 fail, 4 partial;
- after: 0 fail, 7 partial;
- schemas exercised: IFC2X3, IFC4, IFC4X3_ADD2 and observed IFC4X1;
- no result was upgraded to a strict engineering pass because one or more files
  still depend on inferred topology/exits, assumed dimensions, or incomplete
  route connectivity.

Those partial results are correct safeguards, not parser failures. Missing BIM
semantics cannot be made verified by inventing them in code.

### Extended stress folder

The expanded local folder contained eleven unique IFC payloads, including four
large provenance-pending stress models. All eleven completed without a parser
failure and were labelled partial. The 342.7 MB `arc.ifc` was tested through the
CLI only because it intentionally exceeds the 200 MiB Streamlit deployment
limit. Stress files without documented source/licence remain excluded from the
claimed licensed evaluation corpus.

### Montebello

`11134_V_Motebello_Heistopp_Rev.ifc` remains an operational geometry-derived
case: 16 screened elements, 17 inferred links, two inferred exits and no
verified edges. Its processing readiness is 100/100, while engineering evidence
is 0/100. The correct verdict is **operational pass with review limitations,
exploratory only**.

## Research Boundary

The controlled semantic IFC, scenario benchmark and retrieval benchmark pass
their implemented gates. Two material limitations remain explicit:

- the controlled IFC ground truth is project-authored, not independently
  validated;
- the learned space-use classifier did not satisfy the promotion gate.

The deterministic classifier therefore remains the runtime default. The
scenario benchmark remains `demonstration_only`, and the regulation relevance
judgements remain project-author claims requiring independent review.

## Deployment Boundary

The public Streamlit URL is authentication-gated. Local and CI execution can
verify the app code and health endpoint, but unauthenticated external monitoring
cannot validate the rendered production DOM. Deployment verification must
therefore include the GitHub post-merge workflow plus an authenticated visual
check of the live application.

Docker is not installed on the local audit Mac, so this pass cannot honestly
claim a local image build. Docker and Compose configuration is covered by
regression tests; an image build remains a CI or Docker-enabled-host gate.

## Remaining External Work

These are not defects that can be closed by adding more code:

1. Qualified fire-safety review of assumptions, extracted rules, inferred
   routes and scenario interpretation.
2. Independent validation of space labels and model ground truth before any ML
   promotion or generalisation claim.
3. Manual accessibility checks with assistive technology and representative
   browsers.
4. Licensed, project-representative semantic IFCs with verified room, door,
   exit, width, occupancy and connectivity data for claims beyond exploratory
   screening.
5. A maintained operational process for access control, secrets, backups,
   dependency response, telemetry, incident handling and retention before use
   with confidential professional models.
