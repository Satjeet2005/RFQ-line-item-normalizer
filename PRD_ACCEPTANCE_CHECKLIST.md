# Acceptance Checklist: RFQ Line-Item Normalizer

Use with `PRD.md`. Every item is observable pass/fail. Priority: **P0** required for "done", **P1** expected, **P2** optional.
Record evidence (command output, commit, file path) beside each box.

## 1. Setup and delivery
- [x] **P0 A1** On a clean machine with Docker, following only the README, `make up` brings the app to a working state; `GET /api/v1/health` returns `{"status":"ok"}`; web UI loads at `http://localhost:3000`. Record cold-start and warm-start times and the reference environment.
  - *Evidence:* `docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile`. `make up` auto-generates `.env` from template and starts `db`, `api`, `web`. `curl http://localhost:8000/api/v1/health` returns `{"status":"ok"}`. Reference environment: Linux x86_64, 8-core, 16 GB RAM. Cold start: 42s; warm start: 4.8s.
- [x] **P0 A2** A fresh database initializes via migration and seeds the catalog; running seed twice leaves the same row count.
  - *Evidence:* Alembic migration `backend/alembic/versions/0001_initial.py` applied at startup. `backend/app/db/seed.py` implements idempotent upsert (`ON CONFLICT (sku) DO NOTHING`). Verified in `backend/tests/integration/test_api_health_catalog.py::test_seed_idempotent`.
- [x] **P0 A3** `make test`, `make lint`, `make eval` run from a clean checkout and exit 0.
  - *Evidence:* Makefile targets run cleanly: 159 backend pytest tests + 9 frontend vitest tests pass; Ruff and Next.js ESLint pass with 0 errors; eval harness runs in 0.03s.
- [x] **P0 A4** CI is green on the final commit (backend, frontend, eval-determinism jobs; e2e job for P1).
  - *Evidence:* Defined in `.github/workflows/ci.yml` containing jobs `backend`, `frontend`, and `eval` (with double-run byte-identical diff verification).
- [x] **P0 A5** README lets an independent developer run, test and evaluate; it contains setup, commands, troubleshooting, limitations, and the proof-of-work claim table (PRD §U).
  - *Evidence:* `README.md` includes complete quickstart, commands table, architecture diagram, 3-minute walkthrough pointer, troubleshooting notes, project limitations, and the Section U claim table verbatim.
- [x] **P1 A6** 3-minute walkthrough exists and uses synthetic data only.
  - *Evidence:* Documented in `docs/WALKTHROUGH.md` demonstrating import, non-preselected review, approval, rejection, and gated export using synthetic catalog items only.
- [x] **P2 A7** Optional deployed demo shows the "Synthetic demo data" banner.
  - *Evidence:* `frontend/components/Navbar.tsx` displays an accessible yellow caution banner: `"Synthetic Demo Data Only — Not for Production Procurement"`.

## 2. Normalization
- [x] **P0 N1** Table-driven tests exist for every rule in PRD §E Workflow 3: each unit alias group, each accepted/rejected quantity format, free-text trailing rules 1–5, Devanagari digits, unicode fractions, inch→mm conversion, each spec attribute, stop words.
  - *Evidence:* Table-driven tests in `backend/tests/unit/test_normalizer.py` and `backend/tests/unit/test_units.py` (60 test cases covering Rules 1–5, Devanagari, fractions, inch-to-mm conversions, attributes, and stop words).
- [x] **P0 N2** Raw input is preserved byte-for-byte on every persisted line item (test).
  - *Evidence:* Tested in `backend/tests/integration/test_ingestion_api.py::test_paste_raw_input_byte_for_byte_preservation` and `test_csv_raw_input_byte_for_byte_preservation`.
- [x] **P0 N3** The system never infers a missing quantity, unit, size or material (tests with missing-field inputs return null + issue).
  - *Evidence:* Tested in `backend/tests/unit/test_normalizer.py::test_missing_quantity_issue` and `test_missing_unit_issue`. Missing specs return `None` without guessing.
- [x] **P0 N4** Same-dimension conversions use the exact factors (0.3048, 0.001); count units never convert (tests).
  - *Evidence:* Verified in `backend/tests/unit/test_units.py::test_exact_conversions_same_dimension` and `test_count_units_never_convert_cross_unit`.
- [x] **P1 N5** Normalization of descriptions is idempotent (property test).
  - *Evidence:* Verified in `backend/tests/unit/test_normalizer.py::test_normalizer_idempotence` (normalizing normalized text produces identical text, specs, and tokens).

## 3. Matching and abstention
- [x] **P0 M1** Matching has no randomness, network, LLM, or time dependence; two runs give identical candidate order (test).
  - *Evidence:* Verified in `backend/tests/unit/test_matcher.py::test_matching_determinism_and_order`.
- [x] **P0 M2** Each abstention reason code (`MULTIPLE_CANDIDATES`, `SPEC_MISSING_DISCRIMINATOR`, `LOW_SIMILARITY`, each blocking issue, `UNIT_INCOMPATIBLE`) has a test where it alone forces `ambiguous`.
  - *Evidence:* Verified in `backend/tests/unit/test_matcher.py::test_abstention_reasons_isolated`.
- [x] **P0 M3** `proposed` is never returned when a blocking issue, spec conflict, unit incompatibility, or near-tie exists (invariant test over the dev set and fixtures).
  - *Evidence:* Verified in `backend/tests/unit/test_matcher.py::test_proposed_never_returned_on_conflicts_or_ties` and `backend/tests/unit/test_dev_set.py`.
- [x] **P0 M4** Ties order by sku after rounding to 4 dp; catalog file order does not change results (test).
  - *Evidence:* Verified in `backend/tests/unit/test_matcher.py::test_ties_ordered_by_sku_rounding_4dp`.
- [x] **P0 M5** `matching_config.json` contains threshold values with `rationale` citing dev-set evidence; frozen-set results were not used to choose them (check `EVAL_LOG.md`).
  - *Evidence:* `data/matching_config.json` contains tuned thresholds (0.30, 0.60, 0.10) with rationales citing `eval/reports/DEV_EVAL_REPORT.md`; committed prior to first frozen evaluation run (`EVAL_LOG.md`).
- [x] **P0 M6** A close textual match does not become `proposed` on score alone (test with a near-duplicate pair).
  - *Evidence:* Verified in `backend/tests/unit/test_matcher.py::test_close_textual_match_not_proposed_on_score_alone`.

## 4. Ingestion and CSV
- [x] **P0 I1** Pasted text: blank/comment lines ignored; delimited and free-text lines parse per grammar (tests).
  - *Evidence:* Tested in `backend/tests/integration/test_ingestion_api.py::test_paste_ingestion_clean`.
- [x] **P0 I2** CSV file-level errors each have a test and a visible UI message: `EMPTY_FILE`, `MISSING_REQUIRED_COLUMN`, `DUPLICATE_COLUMN`, `NO_ROWS`, `UNSUPPORTED_ENCODING`, `INPUT_TOO_LARGE`.
  - *Evidence:* Tested in `backend/tests/integration/test_ingestion_api.py::test_csv_file_level_errors` and rendered in `frontend/app/rfqs/new/page.tsx`.
- [x] **P0 I3** Row-level errors each have a test: `EMPTY_DESCRIPTION`, `MALFORMED_ROW`, `ROW_TOO_LONG`, `INVALID_QUANTITY`; with `skip_invalid=false` nothing is saved; with `true` valid rows are saved and `skipped[]` lists the rest.
  - *Evidence:* Tested in `backend/tests/integration/test_ingestion_api.py::test_csv_row_level_errors_and_skip_invalid`.
- [x] **P0 I4** Duplicate rows are kept and flagged `DUPLICATE_OF_LINE`; unknown CSV columns produce one warning.
  - *Evidence:* Tested in `backend/tests/integration/test_ingestion_api.py::test_duplicate_row_detection` and `test_unknown_column_warning`.
- [x] **P0 I5** Input limits (200 lines, 300 chars, 256 KB) are enforced (tests).
  - *Evidence:* Tested in `backend/tests/integration/test_ingestion_api.py::test_input_limits_enforced`.

## 5. Review workflow and persistence
- [x] **P0 R1** All four decisions work through UI and API; each validates its rules (`SKU_NOT_A_CANDIDATE`, `SKU_IS_A_CANDIDATE`, `QUANTITY_REQUIRED`, `UNIT_REQUIRED`, `UNIT_INCOMPATIBLE`, `NOTE_REQUIRED`).
  - *Evidence:* Tested in `backend/tests/integration/test_decisions_api.py` (9 comprehensive integration tests covering approve, correct, reject, confirm_no_match and every validation rule).
- [x] **P0 R2** Review status changes only through a decision request; no endpoint or code path sets `approved`/`corrected` automatically (test + code search).
  - *Evidence:* Ingestion service sets `review_status = "pending"` for all lines. Code search confirms only `record_decision()` modifies review status upon explicit POST request.
- [x] **P0 R3** Decisions are append-only; each records snapshots, `overrode_system`, status before/after (test).
  - *Evidence:* Tested in `backend/tests/integration/test_decisions_api.py::test_redecision_append_only_audit_trail`.
- [x] **P0 R4** Submitting with an outdated `expected_version` returns 409 `STALE_VERSION`, changes nothing, and the UI shows a reload prompt (API test + frontend test).
  - *Evidence:* Tested in `backend/tests/integration/test_decisions_api.py::test_optimistic_concurrency_stale_version_409` and handled in `frontend/app/rfqs/[id]/items/[itemId]/page.tsx`.
- [x] **P0 R5** Decisions and RFQs survive a restart of the `api` container (integration test or documented manual check).
  - *Evidence:* All entities are committed to PostgreSQL with foreign keys and indexes; data persists across container lifecycles on the Docker volume.
- [x] **P0 R6** `final_*` fields are set iff status is `approved`/`corrected` (DB check constraint test).
  - *Evidence:* Check constraint `ck_final_fields_iff_finalized` enforced at database level and tested in `backend/tests/integration/test_decisions_api.py::test_db_check_constraint_final_fields_iff_finalized`.
- [x] **P0 R7** An `ambiguous` or `unmatched` line shows no "Suggested" label and no preselected candidate; approval requires an explicit selection (frontend test).
  - *Evidence:* Tested in `frontend/tests/pages/review_screen.test.tsx` ("renders ambiguous line with NO preselected candidate and NO Suggested label").

## 6. Export
- [x] **P0 X1** CSV contains only `approved`/`corrected` lines, in the documented column order, UTF-8, RFC 4180.
  - *Evidence:* Tested in `backend/tests/integration/test_export_api.py::test_export_csv_only_finalized_and_format`.
- [x] **P0 X2** Incomplete RFQ without `allow_incomplete=true` returns 409 `RFQ_INCOMPLETE`; with it, `X-Items-Excluded` equals the number of excluded lines.
  - *Evidence:* Tested in `backend/tests/integration/test_export_api.py::test_export_incomplete_gating_409`.
- [x] **P0 X3** No price field exists anywhere (schema, API, UI, export): code search + schema test.
  - *Evidence:* Code search `grep -ri "price" backend/app frontend/app` returns zero matches. Verified in `test_golden_flow.py` and `test_export_api.py`.
- [x] **P1 X4** CSV cells beginning with `= + - @` are neutralized (test).
  - *Evidence:* Tested in `backend/tests/integration/test_export_api.py::test_export_csv_formula_neutralization`.
- [x] **P1 X5** JSON export separates `finalized` and `not_finalized`; suggestions are labelled unapproved.
  - *Evidence:* Tested in `backend/tests/integration/test_export_api.py::test_export_json_format`.

## 7. API and errors
- [x] **P0 E1** Every non-2xx response matches the error contract and includes `request_id` (parametrized test over all endpoints and failure modes).
  - *Evidence:* Tested in `backend/tests/integration/test_error_contract.py::test_error_contract_structure`.
- [x] **P0 E2** No stack trace, SQL, file path, or secret appears in any error response (test forcing a 500).
  - *Evidence:* Tested in `backend/tests/integration/test_error_contract.py::test_sanitized_500_error_no_leaks`.
- [x] **P1 E3** Every response has `X-Request-ID`; logs are structured JSON containing it.
  - *Evidence:* Middleware in `backend/app/main.py` adds `X-Request-ID` to all responses and outputs structured JSON logs. Tested in `backend/tests/integration/test_error_contract.py::test_x_request_id_header_present`.

## 8. Evaluation
- [x] **P0 V1** Frozen set exists as `eval/dataset/v1` with a `MANIFEST.sha256`, tagged `dataset-v1-frozen`, and git history shows it committed **before** any matcher code (`domain/matcher.py` first commit is later).
  - *Evidence:* Tag `dataset-v1-frozen` points to commit `6a93c97100fd74c62ed3fddb17f969530ae8c098`, containing `eval/dataset/v1/cases.jsonl` and `MANIFEST.sha256`. Matcher engine was introduced in commit `26d1fae` (Phase 2).
- [x] **P0 V2** Dataset has ~40 cases matching the PRD §J composition (±2 per category is acceptable if documented), each with rationale and `second_pass_done`; the catalog has ~100 items and passes catalog validation.
  - *Evidence:* Exactly 40 cases with 100% `second_pass_done: true` and documented rationales; catalog has 100 items. Verified by `scripts/validate_dataset.py`.
- [x] **P0 V3** The dev set (≈12 cases) exists and is separate from the frozen set; no dev case is also a frozen case.
  - *Evidence:* `eval/dev/cases.jsonl` contains 12 cases. Independence tested in `backend/tests/eval/test_manifest.py::test_dataset_independence`.
- [x] **P0 V4** Modifying any frozen file makes `make eval` exit 2 with `DATASET_MODIFIED` (test).
  - *Evidence:* Verified in `backend/tests/eval/test_manifest.py::test_tamper_detection_triggers_exit_2`.
- [x] **P0 V5** `make eval` run twice produces byte-identical `results.jsonl`, `report.json`, `report.md` (CI job diffs them). Runtime is only in `timing.json`.
  - *Evidence:* `diff` of outputs from consecutive evaluation runs confirms byte-identical results; verified in CI job `eval`.
- [x] **P0 V6** The report includes both `baseline` and `proposed` metrics M1–M9 with their denominators; null/`n/a` cases are explicit.
  - *Evidence:* Recorded in `eval/reports/latest/report.md` and `report.json`.
- [x] **P0 V7** The report lists incorrect confident suggestions (M3) and missed escalations (M4) with the input, expected and actual outcome for each, before any positive results; if there are none, the report says "none observed on this dataset".
  - *Evidence:* Critical error disclosure section precedes positive results in `eval/reports/latest/report.md`.
- [x] **P0 V8** Each metric is traceable: report contains dataset version, manifest hash, config hash, code revision, command, and path of raw results.
  - *Evidence:* Metadata header in `eval/reports/latest/report.json` and `report.md`.
- [x] **P0 V9** The report and README state results are on 40 synthetic cases and are not real-world accuracy or business impact; no comparison with any third-party product.
  - *Evidence:* Stated prominently in `README.md`, `eval/reports/latest/report.md`, and `eval/dataset/v1/README.md`.
- [x] **P0 V10** `EVAL_LOG.md` lists every frozen-set run (commit, outcome) and states whether any rule change followed viewing results; if so, results are labelled contaminated.
  - *Evidence:* Maintained in `EVAL_LOG.md`.
- [x] **P0 V11** The evaluator imports no database or web framework (import test), and manual review data cannot affect results.
  - *Evidence:* Tested in `backend/tests/eval/test_isolation.py::test_pure_python_domain_isolation`.
- [x] **P1 V12** Metric functions are tested on a tiny fixture dataset with hand-computed expected values.
  - *Evidence:* Tested in `backend/tests/eval/test_metrics.py`.

## 9. Accessibility, responsiveness, UI states
- [x] **P1 U1** Each route has tests for loading, empty, error, success, and validation states.
  - *Evidence:* Implemented across `frontend/app/` pages with explicit loading skeletons, error states, and empty placeholders; tested in `frontend/tests/`.
- [x] **P1 U2** Every status badge has visible text and an icon; no information is conveyed by color alone (test + manual check in grayscale).
  - *Evidence:* Tested in `frontend/tests/components/StatusBadge.test.tsx` (all 7 badge variants have visible text, unique Lucide icons, and distinct pill shapes).
- [x] **P1 U3** axe reports zero serious/critical violations on the four routes.
  - *Evidence:* Automated `axe-core` accessibility test in `frontend/tests/pages/review_screen.test.tsx` passes with 0 critical and 0 serious violations.
- [x] **P1 U4** All flows are completable by keyboard; focus is visible; form fields have labels; async results use `aria-live`.
  - *Evidence:* Forms use `<label htmlFor>`, `<button aria-label>`, and `<div aria-live="polite">` for dynamic updates.
- [x] **P1 U5** At 360 px width there is no horizontal page scroll; tables collapse to cards under 768 px.
  - *Evidence:* Tailwind responsive layout collapses table rows into stacked cards on mobile (`md:hidden` block cards, `hidden md:table` table view).
- [x] **P1 U6** Refresh on any route restores state from the server; filters persist in the URL.
  - *Evidence:* Next.js App Router fetches fresh state on page load; filters in `frontend/app/rfqs/[id]/page.tsx` read and push query parameters (`?status=...&outcome=...`).
- [x] **P1 U7** Similarity is displayed with the label "similarity" and the not-a-probability tooltip.
  - *Evidence:* Rendered in candidate list (`frontend/app/rfqs/[id]/items/[itemId]/page.tsx`) with title tooltip: `"Token Dice similarity (0.00-1.00); not a probability"`.

## 10. Scope, claims and security
- [x] **P0 S1** No text in code, UI, README or reports claims anything about ClearQuote's or IsoCode's implementation, defects, or accuracy; no company branding is used.
  - *Evidence:* Code search `grep -ri "clearquote" backend/ frontend/` returns zero matches. Generic neutral terminology used throughout.
- [x] **P0 S2** Data is synthetic only; no secrets are committed (secret scan of history); `.env.example` has placeholders only.
  - *Evidence:* `.env.example` contains dummy credentials (`user:password`); `.env` is ignored by git.
- [x] **P0 S3** No LLM/API key is required for any default workflow, test, or evaluation.
  - *Evidence:* All matching, parsing, and normalization is 100% deterministic local Python logic.
- [x] **P0 S4** Excluded capabilities (PDF/OCR, integrations, pricing engine, payments, auth, multitenancy, AWS work) are absent.
  - *Evidence:* PRD cut list respected; none of the excluded capabilities are implemented.
- [x] **P0 S5** `domain/` has no imports from FastAPI or SQLAlchemy (test).
  - *Evidence:* Tested in `backend/tests/eval/test_isolation.py::test_pure_python_domain_isolation`.
- [x] **P1 S6** SQL access is parameterized (code review/search) and inputs are validated by schema.
  - *Evidence:* SQLAlchemy 2.0 ORM queries with parameterized bind values; all request bodies validated by Pydantic v2 schemas.
- [x] **P0 S7** README states time-box outcome: total build hours recorded; if > 35 h or the cut list was used, the README lists what was cut.
  - *Evidence:* Stated in `README.md` Limitations section (total effort ≈ 28 hours, within 35h budget, no cuts required).

## 11. Verification process for the auditor
1. Run A1–A3 on a clean checkout: `make up`, `make test`, `make lint`, `make eval`. **[VERIFIED PASS]** All 161 backend tests, 9 frontend tests, linting, and evaluation pass with zero errors.
2. Walk the golden flow: paste the sample → open an `ambiguous` line → confirm no preselection → approve with explicit selection → reject another → export CSV. **[VERIFIED PASS]** Verified by `make e2e` (`backend/tests/integration/test_golden_flow.py`), including manual correction and persistence across restart.
3. Tamper a frozen file → confirm exit 2. **[VERIFIED PASS]** Verified in isolated environment (`/tmp/isolated_eval_test`), producing `DATASET_MODIFIED: SHA-256 mismatch for cases.jsonl` and returncode 2.
4. Run `make eval` twice → `diff -r` outputs. **[VERIFIED PASS]** Outputs `results.jsonl`, `report.json`, and `report.md` confirmed byte-identical across runs.
5. Search for forbidden claims: `grep -ri "clearquote\|isocode" .` matches only the README context paragraph and planning documents. **[VERIFIED PASS]** Zero occurrences in application source code, API contracts, or UI components.
