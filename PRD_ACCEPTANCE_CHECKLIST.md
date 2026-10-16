# Acceptance Checklist: RFQ Line-Item Normalizer

Use with `PRD.md`. Every item is observable pass/fail. Priority: **P0** required for "done", **P1** expected, **P2** optional.
Record evidence (command output, commit, file path) beside each box.

## 1. Setup and delivery
- [ ] **P0 A1** On a clean machine with Docker, following only the README, `make up` brings the app to a working state; `GET /api/v1/health` returns `{"status":"ok"}`; web UI loads at `http://localhost:3000`. Record cold-start and warm-start times and the reference environment.
- [ ] **P0 A2** A fresh database initializes via migration and seeds the catalog; running seed twice leaves the same row count.
- [ ] **P0 A3** `make test`, `make lint`, `make eval` run from a clean checkout and exit 0.
- [ ] **P0 A4** CI is green on the final commit (backend, frontend, eval-determinism jobs; e2e job for P1).
- [ ] **P0 A5** README lets an independent developer run, test and evaluate; it contains setup, commands, troubleshooting, limitations, and the proof-of-work claim table (PRD §U).
- [ ] **P1 A6** 3-minute walkthrough exists and uses synthetic data only.
- [ ] **P2 A7** Optional deployed demo shows the "Synthetic demo data" banner.

## 2. Normalization
- [ ] **P0 N1** Table-driven tests exist for every rule in PRD §E Workflow 3: each unit alias group, each accepted/rejected quantity format, free-text trailing rules 1–5, Devanagari digits, unicode fractions, inch→mm conversion, each spec attribute, stop words.
- [ ] **P0 N2** Raw input is preserved byte-for-byte on every persisted line item (test).
- [ ] **P0 N3** The system never infers a missing quantity, unit, size or material (tests with missing-field inputs return null + issue).
- [ ] **P0 N4** Same-dimension conversions use the exact factors (0.3048, 0.001); count units never convert (tests).
- [ ] **P1 N5** Normalization of descriptions is idempotent (property test).

## 3. Matching and abstention
- [ ] **P0 M1** Matching has no randomness, network, LLM, or time dependence; two runs give identical candidate order (test).
- [ ] **P0 M2** Each abstention reason code (`MULTIPLE_CANDIDATES`, `SPEC_MISSING_DISCRIMINATOR`, `LOW_SIMILARITY`, each blocking issue, `UNIT_INCOMPATIBLE`) has a test where it alone forces `ambiguous`.
- [ ] **P0 M3** `proposed` is never returned when a blocking issue, spec conflict, unit incompatibility, or near-tie exists (invariant test over the dev set and fixtures).
- [ ] **P0 M4** Ties order by sku after rounding to 4 dp; catalog file order does not change results (test).
- [ ] **P0 M5** `matching_config.json` contains threshold values with `rationale` citing dev-set evidence; frozen-set results were not used to choose them (check `EVAL_LOG.md`).
- [ ] **P0 M6** A close textual match does not become `proposed` on score alone (test with a near-duplicate pair).

## 4. Ingestion and CSV
- [ ] **P0 I1** Pasted text: blank/comment lines ignored; delimited and free-text lines parse per grammar (tests).
- [ ] **P0 I2** CSV file-level errors each have a test and a visible UI message: `EMPTY_FILE`, `MISSING_REQUIRED_COLUMN`, `DUPLICATE_COLUMN`, `NO_ROWS`, `UNSUPPORTED_ENCODING`, `INPUT_TOO_LARGE`.
- [ ] **P0 I3** Row-level errors each have a test: `EMPTY_DESCRIPTION`, `MALFORMED_ROW`, `ROW_TOO_LONG`, `INVALID_QUANTITY`; with `skip_invalid=false` nothing is saved; with `true` valid rows are saved and `skipped[]` lists the rest.
- [ ] **P0 I4** Duplicate rows are kept and flagged `DUPLICATE_OF_LINE`; unknown CSV columns produce one warning.
- [ ] **P0 I5** Input limits (200 lines, 300 chars, 256 KB) are enforced (tests).

## 5. Review workflow and persistence
- [ ] **P0 R1** All four decisions work through UI and API; each validates its rules (`SKU_NOT_A_CANDIDATE`, `SKU_IS_A_CANDIDATE`, `QUANTITY_REQUIRED`, `UNIT_REQUIRED`, `UNIT_INCOMPATIBLE`, `NOTE_REQUIRED`).
- [ ] **P0 R2** Review status changes only through a decision request; no endpoint or code path sets `approved`/`corrected` automatically (test + code search).
- [ ] **P0 R3** Decisions are append-only; each records snapshots, `overrode_system`, status before/after (test).
- [ ] **P0 R4** Submitting with an outdated `expected_version` returns 409 `STALE_VERSION`, changes nothing, and the UI shows a reload prompt (API test + frontend test).
- [ ] **P0 R5** Decisions and RFQs survive a restart of the `api` container (integration test or documented manual check).
- [ ] **P0 R6** `final_*` fields are set iff status is `approved`/`corrected` (DB check constraint test).
- [ ] **P0 R7** An `ambiguous` or `unmatched` line shows no "Suggested" label and no preselected candidate; approval requires an explicit selection (frontend test).

## 6. Export
- [ ] **P0 X1** CSV contains only `approved`/`corrected` lines, in the documented column order, UTF-8, RFC 4180.
- [ ] **P0 X2** Incomplete RFQ without `allow_incomplete=true` returns 409 `RFQ_INCOMPLETE`; with it, `X-Items-Excluded` equals the number of excluded lines.
- [ ] **P0 X3** No price field exists anywhere (schema, API, UI, export): code search + schema test.
- [ ] **P1 X4** CSV cells beginning with `= + - @` are neutralized (test).
- [ ] **P1 X5** JSON export separates `finalized` and `not_finalized`; suggestions are labelled unapproved.

## 7. API and errors
- [ ] **P0 E1** Every non-2xx response matches the error contract and includes `request_id` (parametrized test over all endpoints and failure modes).
- [ ] **P0 E2** No stack trace, SQL, file path, or secret appears in any error response (test forcing a 500).
- [ ] **P1 E3** Every response has `X-Request-ID`; logs are structured JSON containing it.

## 8. Evaluation
- [ ] **P0 V1** Frozen set exists as `eval/dataset/v1` with a `MANIFEST.sha256`, tagged `dataset-v1-frozen`, and git history shows it committed **before** any matcher code (`domain/matcher.py` first commit is later).
- [ ] **P0 V2** Dataset has ~40 cases matching the PRD §J composition (±2 per category is acceptable if documented), each with rationale and `second_pass_done`; the catalog has ~100 items and passes catalog validation.
- [ ] **P0 V3** The dev set (≈12 cases) exists and is separate from the frozen set; no dev case is also a frozen case.
- [ ] **P0 V4** Modifying any frozen file makes `make eval` exit 2 with `DATASET_MODIFIED` (test).
- [ ] **P0 V5** `make eval` run twice produces byte-identical `results.jsonl`, `report.json`, `report.md` (CI job diffs them). Runtime is only in `timing.json`.
- [ ] **P0 V6** The report includes both `baseline` and `proposed` metrics M1–M9 with their denominators; null/`n/a` cases are explicit.
- [ ] **P0 V7** The report lists incorrect confident suggestions (M3) and missed escalations (M4) with the input, expected and actual outcome for each, before any positive results; if there are none, the report says "none observed on this dataset".
- [ ] **P0 V8** Each metric is traceable: report contains dataset version, manifest hash, config hash, code revision, command, and path of raw results.
- [ ] **P0 V9** The report and README state results are on 40 synthetic cases and are not real-world accuracy or business impact; no comparison with any third-party product.
- [ ] **P0 V10** `EVAL_LOG.md` lists every frozen-set run (commit, outcome) and states whether any rule change followed viewing results; if so, results are labelled contaminated.
- [ ] **P0 V11** The evaluator imports no database or web framework (import test), and manual review data cannot affect results.
- [ ] **P1 V12** Metric functions are tested on a tiny fixture dataset with hand-computed expected values.

## 9. Accessibility, responsiveness, UI states
- [ ] **P1 U1** Each route has tests for loading, empty, error, success, and validation states.
- [ ] **P1 U2** Every status badge has visible text and an icon; no information is conveyed by color alone (test + manual check in grayscale).
- [ ] **P1 U3** axe reports zero serious/critical violations on the four routes.
- [ ] **P1 U4** All flows are completable by keyboard; focus is visible; form fields have labels; async results use `aria-live`.
- [ ] **P1 U5** At 360 px width there is no horizontal page scroll; tables collapse to cards under 768 px.
- [ ] **P1 U6** Refresh on any route restores state from the server; filters persist in the URL.
- [ ] **P1 U7** Similarity is displayed with the label "similarity" and the not-a-probability tooltip.

## 10. Scope, claims and security
- [ ] **P0 S1** No text in code, UI, README or reports claims anything about ClearQuote's or IsoCode's implementation, defects, or accuracy; no company branding is used.
- [ ] **P0 S2** Data is synthetic only; no secrets are committed (secret scan of history); `.env.example` has placeholders only.
- [ ] **P0 S3** No LLM/API key is required for any default workflow, test, or evaluation.
- [ ] **P0 S4** Excluded capabilities (PDF/OCR, integrations, pricing engine, payments, auth, multitenancy, AWS work) are absent.
- [ ] **P0 S5** `domain/` has no imports from FastAPI or SQLAlchemy (test).
- [ ] **P1 S6** SQL access is parameterized (code review/search) and inputs are validated by schema.
- [ ] **P0 S7** README states time-box outcome: total build hours recorded; if > 35 h or the cut list was used, the README lists what was cut.

## 11. Verification process for the auditor
1. Run A1–A3 on a clean checkout.
2. Walk the golden flow: paste the sample → open an `ambiguous` line → confirm no preselection → approve with explicit selection → reject another → export CSV.
3. Tamper a frozen file → confirm exit 2.
4. Run `make eval` twice → `diff -r` outputs.
5. Search for forbidden claims: `grep -ri "clearquote\|isocode" .` should only match the README context paragraph and planning documents.
