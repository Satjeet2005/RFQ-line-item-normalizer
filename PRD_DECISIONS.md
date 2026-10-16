# PRD Decisions, Assumptions and Open Questions

Companion to `PRD.md`. Each entry: **Question · Why it matters · Default chosen · Alternatives · Consequence if wrong · Resolve before implementation?**
"Phase 1" = must be settled during the Dataset and PRD validation phase, before matcher code exists.

---

## A. Decisions that shape evaluation validity

### D1. How are matching thresholds chosen without contaminating the frozen set?
- **Why it matters:** with 40 cases, tuning thresholds on them would make every reported number meaningless.
- **Default:** add a separate **12-case dev set** (`eval/dev/`), never reported as results; tune `T_MIN_CANDIDATE`, `T_PROPOSE`, `T_MARGIN` only on it; record values plus evidence in `matching_config.json`; commit before the first frozen-set run. PRD seeds (0.30 / 0.60 / 0.10) are hypotheses only.
- **Alternatives:** (a) tune on the frozen set and disclose contamination; (b) pick thresholds by reasoning alone with no data; (c) cross-validate on 40 cases (too small).
- **Consequence if wrong:** inflated or untrustworthy metrics; a technical reviewer would discount the whole report.
- **Resolve before implementation?** Resolved in the PRD as a process. Numeric values are set in **Phase 1/2**, not now. *Note:* the dev set is an addition to the audit's plan; its ≈0.75 h cost is inside the Phase 1 budget. If it must go, fall back to (a) with disclosure.

### D2. What counts as "high-confidence" given similarity scores are not probabilities?
- **Default:** "high-confidence" means system outcome `proposed` (passes every rule), not a score band. The UI never shows a percentage-as-confidence; it shows "similarity" with a disclaimer.
- **Alternatives:** calibrate scores into probabilities (not possible with 40 cases); show a High/Med/Low label.
- **Consequence if wrong:** users over-trust a number. Labels like "High" would imply calibration the data cannot support.
- **Resolve before implementation?** Yes (resolved).

### D3. Which cases are expected to be "escalated"?
- **Default:** escalated = outcome `ambiguous` or `unmatched` (both are non-`proposed`). Expected `review` cases pass if not proposed; expected `unmatched` cases pass strictly only if `unmatched` (M7).
- **Alternatives:** require `ambiguous` exactly for `review`.
- **Consequence if wrong:** metrics become too harsh or too lenient on abstention quality.
- **Resolve before implementation?** Yes (resolved).

### D4. What is the naive baseline?
- **Default:** raw lowercase token overlap against catalog name, ties by sku, `proposed` whenever overlap ≥ 1, no unit/spec logic, never `ambiguous`.
- **Alternatives:** exact string match (too weak to be informative); TF-IDF (closer to the real system, weakens the contrast).
- **Consequence if wrong:** an overly weak baseline makes "improvement" trivial. The report must say the baseline is deliberately naive and that beating it is not evidence of production quality.
- **Resolve before implementation?** Yes (resolved).

### D5. How is "byte-identical" achieved while still reporting runtime?
- **Default:** runtime goes to a separate `timing.json` excluded from the guarantee; no timestamps/paths in the deterministic outputs; same container image and code revision required; `PYTHONHASHSEED=0`; sorted iteration; floats rounded to 4 dp.
- **Alternatives:** include runtime in the report and drop the byte-identical claim; round runtime.
- **Consequence if wrong:** the audit's reproducibility criterion would fail on trivial noise.
- **Resolve before implementation?** Yes (resolved).

### D6. Where does the code revision come from inside Docker?
- **Default:** `make eval` passes `GIT_SHA=$(git rev-parse HEAD)` (plus `+dirty` when the tree is dirty); absent → `"unknown"`. CI always sets it.
- **Alternatives:** copy `.git` into the image (leaky, slow).
- **Consequence if wrong:** traceability gaps in reports from local runs.
- **Resolve before implementation?** No.

### D7. Single labeller risk
- **Default:** one labeller, mandatory second pass ≥ 24 h later, rationales cite catalog facts, disagreements logged in `LABEL_NOTES.md`; limitation disclosed.
- **Alternatives:** a second human labeller (best, not assumed available).
- **Consequence if wrong:** systematic label bias goes unnoticed.
- **Resolve before implementation?** No; start in Phase 1. If a second person is available, use them for a subset (≥ 10 cases) and report agreement.

### D8. Benchmark cases that hit hard ingestion errors
- **Default:** excluded from the benchmark (they never reach the matcher); covered by ingestion/API tests.
- **Consequence if wrong:** none for validity; it prevents mixing parsing-error handling with matching quality.
- **Resolve before implementation?** Yes (resolved).

---

## B. Data representation and normalization

### D9. Free-text quantity grammar: trailing only
- **Default:** only a trailing `<number> [<unit>]` is read as quantity; leading quantities ("50 mtr GI pipe") are **not** parsed (they become `MISSING_QUANTITY`); a trailing number preceded by `x`/`×` is a dimension, not a quantity.
- **Alternatives:** also parse leading quantities (more coverage, more ambiguity and test cases).
- **Consequence if wrong:** users with leading-quantity habits see many `MISSING_QUANTITY` flags (safe failure, mildly annoying). Parsing too aggressively would silently invent quantities, which is the unsafe failure.
- **Resolve before implementation?** Yes (resolved).

### D10. Unknown unit tokens
- **Default:** never invent. Free text: unknown trailing word ⇒ no quantity detected (`MISSING_QUANTITY`). Delimited/CSV: unknown unit value ⇒ blocking `UNKNOWN_UNIT`, raw value preserved.
- **Consequence if wrong:** a missed alias causes a review flag, not a wrong match.
- **Resolve before implementation?** Yes (resolved).

### D11. Count-unit interchangeability
- **Default:** count units (`nos`, `set`, `pair`, `box`, `roll`, `bag`) are never converted to each other; mismatches are `UNIT_INCOMPATIBLE`.
- **Alternatives:** catalog pack-size fields (extra data/scope).
- **Consequence if wrong:** boxes vs pieces confusion is a classic real-world error; the conservative default prevents it.
- **Resolve before implementation?** Yes (resolved).

### D12. Catalog has no price field
- **Default:** none. The audit and brief forbid inventing a price and exclude a pricing engine; omitting the field makes "never invent a price" structurally true.
- **Alternatives:** an optional price field with validation rules (would invite scope creep).
- **Consequence if wrong:** if a reviewer expects "pricing-rule validation", the README points to the explicit non-goal.
- **Resolve before implementation?** Yes (resolved).

### D13. Requested spec absent from the catalog item
- **Default:** treated as a conflict (unverifiable), so the candidate is disqualified from `proposed`.
- **Alternatives:** warning only.
- **Consequence if wrong:** possible over-abstention; measured by M5.
- **Resolve before implementation?** Yes (resolved).

### D14. Fractional quantities for count units; duplicates
- **Default:** fractional count ⇒ blocking `FRACTIONAL_COUNT`; duplicate rows kept with informational `DUPLICATE_OF_LINE`, never merged.
- **Consequence if wrong:** low.
- **Resolve before implementation?** No.

### D15. Hindi/transliteration scope
- **Default:** Devanagari digits, a handful of unit words, and ≤ 20 product-term aliases, all in `data/aliases.json`, frozen with the dataset. Not general language support.
- **Alternatives:** transliteration library (non-deterministic edge cases, extra dependency).
- **Consequence if wrong:** a few real inputs are missed; documented limitation. Ideally a fluent reader sanity-checks the list.
- **Resolve before implementation?** Phase 1.

---

## C. Review workflow

### D16. Ingestion failure policy
- **Default:** atomic by default; per-row hard errors reject the whole submission with row-level detail, and the UI offers "import valid lines, skip invalid" (`skip_invalid=true`). Skipped lines are reported but not persisted.
- **Alternatives:** always save valid rows (silent partial success), persist invalid rows with an error status (more states).
- **Consequence if wrong:** partial failures could be missed; the skipped-lines banner and `skipped_count` mitigate this.
- **Resolve before implementation?** Yes (resolved).

### D17. Missing-quantity/unit handling at ingestion vs review
- **Default:** soft issues are saved and block `proposed`; the reviewer supplies quantity/unit when approving/correcting. Parse failures with a present-but-invalid quantity are hard errors.
- **Alternatives:** reject all lines lacking quantity (hurts the "visible uncertainty" story).
- **Consequence if wrong:** low.
- **Resolve before implementation?** Yes (resolved).

### D18. Overriding abstention
- **Default:** allowed, explicit, and recorded (`overrode_system`, outcome/reason snapshots). On `ambiguous`/`unmatched` lines no candidate is preselected.
- **Alternatives:** forbid approving ambiguous lines (reviewer would be powerless); allow silently.
- **Consequence if wrong:** the core principle (no silent ambiguity-to-confirmed) would be weakened.
- **Resolve before implementation?** Yes (resolved).

### D19. Review statuses and re-decisions
- **Default:** `pending`, `approved`, `corrected`, `rejected`, `no_match`; revisions allowed (append-only decisions); no "reopen to pending".
- **Alternatives:** add `reopened`/`needs_info`.
- **Consequence if wrong:** small UX friction; avoids extra state machine work.
- **Resolve before implementation?** Yes (resolved).

### D20. Concurrency model
- **Default:** optimistic concurrency with `version` and `expected_version`; 409 returns the current item.
- **Alternatives:** last-write-wins (rejected), row locks (heavier).
- **Consequence if wrong:** lost updates; the brief forbids silent overwrite.
- **Resolve before implementation?** Yes (resolved).

### D21. Export gating
- **Default:** CSV contains only `approved`/`corrected` lines; incomplete RFQs return 409 unless `allow_incomplete=true`; JSON separates `finalized` from `not_finalized` and labels suggestions as unapproved.
- **Consequence if wrong:** an unreviewed suggestion could look final; this design prevents it.
- **Resolve before implementation?** Yes (resolved).

---

## D. Architecture and delivery

### D22. Evaluation is CLI-only in the MVP
- **Default:** `make eval` plus documented outputs; no HTTP endpoint or UI (cut-list item 2). Keeps results isolated from application state.
- **Alternatives:** a read-only evaluation page.
- **Consequence if wrong:** less visual appeal; no impact on correctness.
- **Resolve before implementation?** Yes (resolved).

### D23. Four routes instead of six screens
- **Default:** the six required screens map to four routes (creation/import; RFQ page combining normalization results, review queue and summary/export; item review; CLI "screen" for evaluation).
- **Alternatives:** separate routes (more routing code, same function).
- **Consequence if wrong:** none.
- **Resolve before implementation?** Yes (resolved).

### D24. Real Postgres in tests; Alembic migrations
- **Default:** integration tests use Postgres (CI service container, Compose locally); one Alembic migration. SQLite is not used, to avoid behavior drift (enums, numeric, jsonb).
- **Alternatives:** SQL init script (cut-list item 6).
- **Consequence if wrong:** slower tests, +~1 h.
- **Resolve before implementation?** No.

### D25. Same-origin proxy, no auth, no CORS
- **Default:** Next.js rewrites `/api/*` to the backend; no authentication; local-first. A public demo requires a banner and awareness that data is world-writable.
- **Alternatives:** token auth (scope creep without a demonstrated need).
- **Consequence if wrong:** misuse of a public demo; mitigated by the banner, synthetic-only guidance and optional demo.
- **Resolve before implementation?** Resolved; revisit only if a public demo is kept.

### D26. AWS vs GCP
- **Default:** no cloud-specific work. The internship listing names AWS while the company's public repo targets GCP Cloud Run; since cloud deployment is optional here, the project stays portable (Docker only).
- **Consequence if wrong:** none for core deliverables.
- **Resolve before implementation?** No.

### D27. "One-page PRD" in the audit vs this comprehensive PRD
- **Default:** keep this full `PRD.md` in the repo; Section A (Executive Summary) plus the terminology table serve as the one-page overview linked from the README.
- **Consequence if wrong:** none.
- **Resolve before implementation?** Resolved.

### D28. Identifiers
- **Default:** UUIDv4 for RFQs/lines/decisions; stable text SKUs for catalog.
- **Alternatives:** serial ints (leak counts, simpler).
- **Consequence if wrong:** none.
- **Resolve before implementation?** Resolved.

### D29. Project naming and licensing
- **Default:** name `rfq-line-item-normalizer`; MIT license; no company names or logos in the app. Mention of the "publicly described workflow" appears only in the README's context paragraph.
- **Consequence if wrong:** an unintended implication of affiliation; the name avoids it.
- **Resolve before implementation?** No.

### D30. Clean-start entrypoint and setup command
- **Why it matters:** PRD §A mentions `docker compose up`, PRD §P specifies `make up` (= `docker compose up --build -d`), and Checklist A1 requires `make up` from a clean machine following the README.
- **Default:** `make up` is the authoritative single entrypoint command. The Makefile `up` target automatically creates `.env` from `.env.example` if `.env` does not exist, then runs `docker compose up --build -d`. Direct `docker compose up` is supported if `.env` is manually copied first.
- **Alternatives:** require explicit `cp .env.example .env` before running `docker compose up` or `make up`.
- **Consequence if wrong:** clean-machine onboarding fails or times out if `.env` is missing or flags differ.
- **Resolve before implementation?** Yes (resolved for Phase 1/setup).

### D31. Raw-input preservation for CSV imports
- **Why it matters:** PRD §Terminology and §G require `raw_input` to preserve exact user input byte-for-byte; for CSV rows, this could be ambiguous between the exact unparsed line text vs re-serialized fields.
- **Default:** For CSV imports, `raw_input` preserves the exact original line string from the uploaded CSV payload (including any raw quotes, commas, and whitespace, without modifying line content). Field-level components (`description_raw`, `quantity_raw`, `unit_raw`) preserve the exact cell text as extracted from the CSV parse before normalization.
- **Alternatives:** Reconstructed comma-separated string from cell values.
- **Consequence if wrong:** Subtle data mutations or escaping artifacts during audit checks of raw-input preservation (Checklist N2).
- **Resolve before implementation?** Yes (resolved).

### D32. UTF-8 validation behavior and U+FFFD handling
- **Why it matters:** PRD §E Workflow 2 and §H require `UNSUPPORTED_ENCODING` (422) if input contains invalid UTF-8 or replacement character U+FFFD.
- **Default:** Ingestion checks incoming text payloads (both CSV and pasted text) for the Unicode replacement character (`\ufffd`). If present, or if raw payload decoding fails UTF-8 decoding, the request is rejected with `UNSUPPORTED_ENCODING`. UTF-8 BOM (`\ufeff`) is permitted at the beginning of the file/input and stripped cleanly.
- **Alternatives:** Silently substitute or ignore invalid bytes.
- **Consequence if wrong:** Corrupted characters leak into catalog matching or normalization without visible notice.
- **Resolve before implementation?** Yes (resolved).

### D33. Project-owner waiver of 24-hour second-pass waiting period
- **Why it matters:** PRD §J and D7 historically required a ≥24-hour elapsed interval between the initial and second labelling passes to mitigate single-annotator confirmation bias.
- **Approved Waiver:** The project owner explicitly waived the 24-hour calendar delay requirement for this iteration to allow efficient Phase 1 completion without unnecessary calendar blockage.
- **Scope of Waiver:** The waiver applies strictly to the calendar duration gate. It does **not** waive:
  1. The requirement for a separate, blind second labelling pass conducted using only the input strings and catalog facts without viewing first-pass labels or rationales.
  2. Truthful timestamp recording (actual creation timestamps must be documented, without backdating).
  3. Formal inter-annotator reconciliation and documentation of all discrepancies in `LABEL_NOTES.md`.
  4. Full dataset validation, manifest integrity verification, test suite execution, or deterministic evaluation guarantees.
- **Historical Record Preserved:** The original policy (D7) is preserved in history; this waiver is documented explicitly as an operational decision by project leadership.
### D34. Next.js App Router and API proxying architecture
- **Why it matters:** PRD §N and Checklist U1-U7 require a clean, responsive 4-route UI interacting with the FastAPI persistence layer.
- **Default:** Next.js 14 App Router in `frontend/` with server and client components, using `next.config.mjs` same-origin rewrites (`/api/:path*` -> `API_BASE_URL` or `http://localhost:8000`) to avoid cross-origin CORS issues in both local development and Docker Compose.
- **Alternatives:** Direct browser calls to port 8000 with CORS wildcard; Next.js custom API routes wrapping FastAPI.
- **Consequence if wrong:** CORS configuration leaks or complex cookie/header forwarding bugs.
- **Resolve before implementation?** Yes (resolved for Phase 3).

### D35. Optimistic concurrency control semantics
- **Why it matters:** Multiple reviewers or browser tabs could attempt conflicting decisions on the same line item (Checklist P0 R4).
- **Default:** Every decision request must supply `expected_version: int`. If `line_item.version != expected_version`, the API atomically rejects the request with HTTP 409 `STALE_VERSION`, returning the error details and the latest line item state in the response body. The frontend displays an alert with an instant "Reload latest" action to re-fetch the updated state without data loss.
- **Alternatives:** Last-write-wins; pessimistic database row locking.
- **Consequence if wrong:** Silent overwrite of reviewer decisions and corrupted audit history.
- **Resolve before implementation?** Yes (resolved for Phase 3).

### D36. Non-color-alone status indicator design
- **Why it matters:** Checklist P1 U2 and accessibility requirements forbid conveying status by color alone.
- **Default:** Every status badge combines: (1) an explicit text label, (2) a distinct Lucide SVG icon, and (3) a unique pill shape/border styling. In grayscale, high-contrast, or for screen readers, each status remains unambiguously distinguishable.
- **Alternatives:** Colored dots or badges with color-only differentiation.
- **Consequence if wrong:** Accessibility failure under WCAG 2.1 AA and checklist audit failure.
- **Resolve before implementation?** Yes (resolved for Phase 3).

### D37. Gated export and CSV security
- **Why it matters:** Incomplete RFQs must not accidentally be exported as finalized quotes (Checklist P0 X2); CSV exports opened in spreadsheets must be immune to formula injection (Checklist P1 X4).
- **Default:** CSV and JSON export endpoints require complete review by default, returning 409 `RFQ_INCOMPLETE` with pending line counts if any item is unreviewed. Exporters can explicitly pass `allow_incomplete=true` to export finalized lines only, in which case the API includes `X-Items-Excluded: <N>`. Furthermore, any string cell beginning with `= + - @` is neutralized by prepending `'` per RFC 4180 security recommendations.
- **Alternatives:** Always export all lines; silently omit unreviewed lines without gating.
- **Consequence if wrong:** Downstream procurement mistakes from unfinished reviews; spreadsheet formula execution exploits.
- **Resolve before implementation?** Yes (resolved for Phase 3).

---

## E. Open questions (not blocking)

| # | Question | Why it matters | Proposed default | If unanswered |
|---|---|---|---|---|
| Q1 | Final numeric thresholds | Determines proposed/ambiguous split | Chosen on the dev set in Phase 1/2 | Use documented seeds and say so |
| Q2 | Does a fluent Hindi reader exist to review aliases? | Dictionary correctness | Self-review plus disclosed limitation | Keep dictionary tiny |
| Q3 | Will a public demo be deployed? | Needs banner, possibly reset job | Optional, P2 | Local-only |
| Q4 | Is the 5-minute clean start realistic on the user's machine? | Audit criterion | Report cold and warm numbers | State reference environment |
| Q5 | Exact timed-build format at IsoCode | Rehearsal design | Practice 2 h and 4 h builds | Out of scope for this PRD |

---

## F. Blockers

None. Phase 1, Phase 2, and Phase 3 are complete and verified against all P0/P1 checklist requirements.

