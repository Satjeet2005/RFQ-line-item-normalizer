# PRD: RFQ Line-Item Normalizer & Human Review Queue

**Status:** Implementation-ready draft v1.0 · **Date:** 16 Oct 2026
**Decision record:** `isocode_impact_idea_audit.md`, Outcome B (Redesign). This PRD does not reopen opportunity selection.
**Companion files:** `PRD_DECISIONS.md` (decisions, defaults, open questions) · `PRD_ACCEPTANCE_CHECKLIST.md` (pass/fail verification)
**Working name:** `rfq-line-item-normalizer`. The repo, UI and docs must not use the ClearQuote name or branding.

**Terminology (used consistently throughout):**

| Term | Meaning |
|---|---|
| **Raw input** | The exact text the user supplied (a pasted line or a CSV row). Never modified or discarded. |
| **Line item** | One persisted RFQ row: raw input + normalized data + system suggestion + review state. |
| **Normalized line** | Deterministic parse of the raw input (description, quantity, unit, spec attributes, issues). |
| **Candidate** | A catalog product the matcher lists for a line item, with a similarity score and flags. |
| **System outcome** | The matcher's verdict: `proposed`, `ambiguous`, or `unmatched`. |
| **Review status** | The human state: `pending`, `approved`, `corrected`, `rejected`, `no_match`. |
| **Decision** | One append-only human action on a line item. |
| **Finalized match** | A line item whose review status is `approved` or `corrected`. Only these appear in a "final" export. |

---

## A. Executive Summary

**What it does.** A small web application where a user pastes RFQ (request-for-quotation) lines or imports a CSV; the system deterministically normalizes quantities, units and descriptions, retrieves candidate products from a synthetic catalog, and either **proposes** a match or **abstains** (`ambiguous` / `unmatched`) with visible reasons. A human reviewer approves, corrects, rejects or marks "no match" per line; results are persisted and exported. A separate CLI evaluates the matcher against a frozen, labelled synthetic dataset and a naive baseline.

**Who it is for.** (1) A person processing an RFQ, (2) a reviewer resolving uncertain lines, (3) a developer/evaluator running the benchmark. In practice the audience is a hiring reviewer reading the repo and running it.

**Problem modeled.** Real-world requests for quotation arrive as loosely structured text with inconsistent units, abbreviations, missing quantities and near-identical products. Silent guessing is costly. The product demonstrates the principle: **when information is insufficient to justify a match, make the uncertainty visible instead of silently guessing.**

**Why a standalone demonstration.** Per the audit, nothing public shows any IsoCode Labs product needs an external evaluation tool, and the internship screens end-to-end delivery in IsoCode's stack. This project is independent proof of work, inspired by a publicly described industrial-procurement workflow. It is not a ClearQuote clone, replacement, or critique.

**Success looks like** (all verifiable, see `PRD_ACCEPTANCE_CHECKLIST.md`):
- A clean machine runs `docker compose up` and the app works within 5 minutes (documented reference environment).
- Every normalization rule has an automated test; CI is green.
- A 40-case labelled benchmark was frozen *before* matcher code; `make eval` is byte-reproducible; incorrect confident matches and missed escalations are listed with examples.
- The system never invents a price and never converts an ambiguous candidate into a confirmed match without an explicit human decision.

**Deliberately not proven.** Real-world accuracy, production reliability, business impact, any claim about ClearQuote or IsoCode internals, or suitability for confidential procurement data (see Section U).

---

## B. Problem Statement and Hypothesis

**General workflow problem (modeled).** Turn imperfectly structured RFQ line items (free text or CSV) into normalized, reviewable catalog matches while keeping every uncertain case visible to a human.

**Engineering hypothesis.** On a small frozen synthetic benchmark, a deterministic pipeline (explicit unit/quantity rules, spec extraction, token-similarity retrieval, conservative abstention) produces **fewer incorrect confident matches and fewer missed escalations** than a naive highest-token-overlap baseline, at the cost of more lines routed to review. The experiment is falsifiable: the report may show the opposite, and that outcome is published.

**Synthetic-data assumptions.**
1. The catalog (~100 products across pipes, fittings, fasteners, valves, consumables) and 40 labelled cases are authored by the project owner; they approximate, but do not measure, real distributor data.
2. Labels reflect what a careful human would decide from catalog facts, not what the matcher happens to output.
3. Hindi/transliterated coverage is a small, explicit dictionary, not general language support.

**Unknown about real procurement.** Actual RFQ formats and noise levels, real catalog structure and size, price/commercial rules, reviewer throughput, acceptable false-proposal rates. None are asserted.

**Why human review is necessary.** Lexical similarity is not product equivalence ("M12×60 bolt" and "M12×80 bolt" are lexically close and commercially different). Missing quantity/unit, conflicting specs, and near-duplicate products cannot be resolved without information the system does not have. The system therefore never auto-finalizes: every line, including `proposed` ones, needs a human decision.

No statement here claims any IsoCode Labs product has these problems.

---

## C. Target Users and Use Cases

| User | Goal | Trigger | Expected outcome | Important failure cases |
|---|---|---|---|---|
| **RFQ processor** | Get raw lines into a structured, reviewable RFQ | Has pasted text or a CSV | RFQ created; every line shows normalized form and a system outcome | Bad CSV header, empty file, unreadable encoding, invalid quantity, oversized input, partial failures |
| **Reviewer** | Resolve each line to a final decision | RFQ has `pending` lines | Every line is `approved`, `corrected`, `rejected` or `no_match`; export of finalized matches | Stale concurrent edit (409), approving without quantity/unit, picking an incompatible-unit product, wrong candidate approved |
| **Evaluator/developer** | Verify claims independently | Cloned the repo | Run tests and `make eval`; read report with failures listed | Dataset modified after freeze, non-reproducible output, dirty working tree |

Single local user; no accounts. "Reviewer" and "processor" are roles in the UI flow, not separate logins.

---

## D. Product Goals and Non-Goals

**Goals (each feature must trace to one):**

| ID | Goal |
|---|---|
| G1 | Demonstrate end-to-end delivery in the listed stack (Next.js/TS, FastAPI, Postgres, Docker). |
| G2 | Make uncertainty visible: abstain rather than guess; reasons are shown. |
| G3 | Deterministic, testable domain logic (units, quantities, specs, matching). |
| G4 | Human decisions are validated, persisted, auditable and safe under concurrent edits. |
| G5 | Reproducible, honest evaluation against a frozen dataset and baseline. |
| G6 | Clean-machine reproducibility with tests and CI. |

**Non-goals:** no PDF/OCR, no WhatsApp/email/ERP integration, no real customer data, no pricing/quotation engine (the catalog has **no price field**), no payments/subscriptions/multitenancy, no auth/roles, no AWS-specific work, no LLM in the default workflow or evaluation, no claims about ClearQuote.

**Features to cut first if the 35-hour cap is threatened** (in order): (1) deployed demo, (2) HTTP evaluation endpoint, (3) JSON export, (4) UI pagination and extra filters, (5) Playwright E2E (replace with API integration test of the golden flow + manual script in README), (6) Alembic (replace with a single SQL init script), (7) reduce Hindi term aliases to units only. Never cut: normalization tests, frozen benchmark, abstention logic, review decisions, CI, README.

---

## E. User Journeys and Functional Requirements

**Global limits (configurable constants, defaults):** max 200 lines per RFQ; max 300 characters per line/description; max input 256 KB; max RFQ name 80 characters. Exceeding returns `INPUT_TOO_LARGE` (413) or a row error.

### Workflow 1: Create an RFQ (pasted text)

- **Preconditions:** none.
- **Input:** RFQ name (required, 1–80 chars after trim) and pasted text.
- **Pasted-text grammar** (one item per line):
  - Blank lines and lines starting with `#` are ignored.
  - **Delimited line:** if the line contains `|` or a tab, split on that delimiter into `description | quantity | unit` (unit optional). Extra fields → row error `MALFORMED_ROW`.
  - **Free-text line:** otherwise the whole line is the description, and the system looks for a **trailing quantity** (Workflow 3).
- **Main steps:** client submits `POST /rfqs`; server parses all lines; if no hard errors, creates RFQ, normalizes and matches every line in one transaction, returns the RFQ.
- **Alternate flows:**
  - *Hard row errors present and `skip_invalid=false` (default):* nothing is saved; response 422 with `row_errors[]` (line number, code, message, raw text). The UI shows a table of errors and a button **"Import N valid lines, skip M"**, which resubmits with `skip_invalid=true`.
  - *`skip_invalid=true`:* valid lines are saved; skipped lines are returned in `skipped[]` and shown on the RFQ page banner. Skipped lines are **not** persisted.
  - *Zero valid lines:* 422 `NO_VALID_ROWS` regardless of the flag.
- **Hard (row-rejecting) errors:** `EMPTY_DESCRIPTION`, `MALFORMED_ROW`, `ROW_TOO_LONG`, `INVALID_QUANTITY` (a quantity is present but unparseable, ≤ 0, > 1,000,000, or has more than 3 decimals).
- **Soft issues** (line is saved, flagged, and cannot become `proposed`): see Workflow 3.
- **Acceptance:** invalid data never reaches matching unflagged; the same input always yields the same RFQ content (apart from IDs/timestamps).

### Workflow 2: Import CSV

- **Format:** UTF-8 (BOM allowed and stripped), comma delimiter, RFC 4180 quoting (Python `csv`), `\n` or `\r\n` line endings, first row is the header.
- **Columns** (case-insensitive, trimmed): required `description`, `quantity`; optional `unit`, `line_ref`. Unknown columns are ignored with a single warning listing them. Duplicate header names → file error.
- **Encoding check:** the browser reads the file as UTF-8 text; if the content contains U+FFFD (replacement character) the server rejects with `UNSUPPORTED_ENCODING`.
- **File-level errors (nothing saved):** `EMPTY_FILE`, `MISSING_REQUIRED_COLUMN` (names the column), `DUPLICATE_COLUMN`, `NO_ROWS` (header only), `UNSUPPORTED_ENCODING`, `INPUT_TOO_LARGE`, and non-`.csv` files rejected client-side (the server only sees text).
- **Row-level handling:** same hard/soft rules as Workflow 1. Row with wrong field count → `MALFORMED_ROW`. Empty `quantity` cell → soft `MISSING_QUANTITY`. Quantity cell containing text that is not a number → hard `INVALID_QUANTITY`.
- **Quantity cell may include a unit** ("50 mtr") only when the `unit` column is absent or empty for that row; if both give a unit and they differ after normalization → soft issue `UNIT_CONFLICT` (blocking).
- **Duplicates:** rows identical in (normalized description, quantity, unit) are **kept** and each gets informational issue `DUPLICATE_OF_LINE` (non-blocking). The system does not merge them.
- **Partial failures:** same `skip_invalid` mechanism and `row_errors` shape as Workflow 1; row numbers refer to the CSV data row (header = row 0).
- **No auto-recovery** of unparseable input: no guessing delimiters, encodings, or column meanings.

### Workflow 3: Normalize line items

Deterministic, pure functions in `domain/`. The raw input is preserved on the line item; the UI shows raw vs normalized side by side.

**Canonical output (`NormalizedLine`):**

```
description_raw        string   as supplied (trimmed ends only)
description_normalized string   lowercase, NFKC, aliases applied, punctuation removed, spec/qty fragments removed
tokens                 string[] sorted unique tokens used for similarity (includes spec tokens like "size:25.4")
spec                   { size_mm?, length_mm?, thread?, material?, class?, grade? }   Decimal-as-string / string values
quantity               decimal | null      canonical Decimal, ≤ 3 dp
unit                   canonical code | null   one of the unit dictionary codes
unit_dimension         count | length | mass | volume | null
issues                 [{code, severity: "blocking"|"info", detail}]
```

**Safe, deterministic normalizations (exhaustive list):**
1. Unicode NFKC; trim; collapse whitespace; lowercase.
2. Devanagari digits `०–९` → `0–9`.
3. Strip trailing `.` from unit tokens; unicode fractions (`½ ¼ ¾`) → numeric.
4. Unit aliases → canonical unit (table below).
5. Product-term transliteration aliases (token-level, table below).
6. Spec extraction (below) with exact inch→mm conversion (1 in = 25.4 mm, `Decimal`).
7. Stop-word removal: `of, the, and, with, for, type, make, quality, item, supply`.

**Not done (explicitly):** inferring a missing quantity, unit, size or material; guessing a unit for a bare number; number words ("ten", "दस"); leading quantities ("50 mtr GI pipe"); unit symbols `'` and `"` as quantity units; spelling correction; any LLM or fuzzy character-level correction.

**Quantity parsing:**
- Accepted: `123`, `12.5`, `1,000`, `1,00,000` (international or Indian grouping, only in these exact grouping patterns), Devanagari digits.
- Rejected as `INVALID_QUANTITY`: comma decimals (`1,5`), `1e3`, negative, zero, > 1,000,000, > 3 decimals, text.
- Count units (`nos, set, pair, box, roll, bag`) require integers; a fractional value gives blocking issue `FRACTIONAL_COUNT`.

**Free-text trailing quantity rule.** Examine the last whitespace-separated tokens of the line:
1. `<number> <unit-alias>` at the end → quantity and unit.
2. `<number>` at the end **and** the preceding token is not `x`/`×` → quantity, unit absent → soft `MISSING_UNIT`.
3. Last token is `<number>` preceded by `x`/`×` (a dimension like `M12 x 50`) → **not** a quantity; soft `MISSING_QUANTITY`.
4. Anything else → soft `MISSING_QUANTITY`; the whole line stays in the description.
5. `<number> <word>` where `<word>` is not in the unit dictionary → not parsed as quantity (rule 4). In delimited/CSV input, an unrecognized unit-column value → blocking `UNKNOWN_UNIT` with the raw value preserved.

**Initial unit dictionary** (case-insensitive; quantity units only):

| Code | Dimension | Aliases |
|---|---|---|
| `nos` | count | nos, no, nr, pc, pcs, piece, pieces, unit, units, nag, नग |
| `set` | count | set, sets |
| `pair` | count | pair, pairs |
| `box` | count | box, boxes |
| `roll` | count | roll, rolls |
| `bag` | count | bag, bags |
| `mtr` | length | m, mtr, mtrs, meter, meters, metre, metres, meetar, मीटर |
| `ft` | length | ft, feet, foot, fut, फुट |
| `kg` | mass | kg, kgs, kilo, kilos, kilogram, kilograms, किलो |
| `g` | mass | g, gm, gms, gram, grams |
| `ltr` | volume | l, lt, ltr, ltrs, liter, liters, litre, litres, लीटर |
| `ml` | volume | ml, mls, millilitre, milliliter |

**Exact conversions** (same dimension only): `1 ft = 0.3048 mtr`; `1 g = 0.001 kg`; `1 ml = 0.001 ltr`. Count units are **never** interchangeable (e.g. `box` ≠ `nos`; pack sizes are not inferred). Conversion uses `Decimal`, result quantized to 6 dp with round-half-even; the original quantity/unit is always kept.

**Initial product-term aliases** (token-level; the implementation ships this list as `data/aliases.json` and may add entries only before the frozen set is committed): `paip/पाइप→pipe`, `bolt/बोल्ट→bolt`, `nat/नट→nut`, `valv/वाल्व→valve`, `kohni/कोहनी→elbow`, `pital/पीतल→brass`. Target size: ≤ 20 entries; every entry must be justified by at least one catalog alias or case.

**Spec extraction** (vocabulary in `data/vocab.json`):

| Attribute | Recognized forms | Canonical value |
|---|---|---|
| `size_mm` | `<n> mm`, `<n> cm`, `<n> inch/in/"`, `<a>/<b> inch`, `<w> <a>/<b> inch`, unicode fractions | Decimal mm string, e.g. `1 inch → "25.4"`, `½" → "12.7"`, `1½" → "38.1"` |
| `length_mm` | `m<d>x<n>`, `m<d> x <n>` (with optional `mm`) | Decimal mm |
| `thread` | `m<d>` | `M12` |
| `material` | gi, galvanized/galvanised, ms, mild steel, ss304, ss 304, ss316, pvc, brass, cu, copper | `GI, MS, SS304, SS316, PVC, BRASS, CU` |
| `class` | `class a/b/c` | `A/B/C` |
| `grade` | `4.6`, `8.8`, `10.9` | as written |

If one single-valued attribute receives two different values in the same line (e.g. `ss304 … brass`), the line gets blocking issue `SPEC_CONFLICT_IN_REQUEST` and the attribute is left unset.

**Acceptance:** every rule above has a table-driven unit test (input → expected normalized line); raw input is returned unchanged in all cases.

### Workflow 4: Match against the synthetic catalog

All in `domain/matcher.py`, pure and deterministic. Configuration in `data/matching_config.json` (versioned and hashed).

1. **Token set.** Request tokens = normalized description tokens plus spec tokens (`size:25.4`, `thread:M12`, `material:GI`, `class:B`, `length:60`, `grade:8.8`). Catalog product token sets are built the same way from `name`, each `alias`, and `attributes`. For a product, take the **best** (maximum) similarity over its name and each alias.
2. **Similarity** = Dice coefficient `2·|R∩C| / (|R|+|C|)`, rounded to 4 decimals. This is a *lexical similarity score*, **not a probability**; the UI labels it "similarity" and never shows a percentage-as-confidence.
3. **Retrieval.** Score all catalog products; list up to `K=5` with score ≥ `T_MIN_CANDIDATE`, ordered by (score desc, sku asc). Rounding before ordering plus the sku tie-break makes order total and reproducible.
4. **Per-candidate checks:** spec conflict (below) and unit check (below).
5. **Spec conflict.** For each attribute the request specifies: if the candidate lacks it, or has a different value → conflict (`SPEC_CONFLICT:<attr>`; an absent candidate attribute is treated as unverifiable and therefore conflicting). Conflicting candidates are shown but flagged `disqualified`.
6. **Unit check** (against the candidate's `uom`): same code → ok; same dimension → ok with conversion; different dimension, or two different count units → `UNIT_INCOMPATIBLE`; request unit missing → `MISSING_UNIT`.
7. **Plausible set P** = listed candidates not disqualified.
8. **Near-tie group G** = candidates in P with `s1 − s_c < T_MARGIN` (s1 = top score).

**Naive baseline** (`domain/baseline.py`): raw lowercase alphanumeric tokens of `description_raw` (no aliases, no spec extraction, no unit logic, no stop words); score = count of shared tokens with the catalog product `name`; pick max, tie → lowest sku; outcome `proposed` if score ≥ 1 else `unmatched`; never abstains otherwise. It uses the same ingestion split of description vs quantity as the proposed system.

**Reproducibility:** no LLM, network call, randomness, or time-dependence in matching. `PYTHONHASHSEED=0`; all iterations over sorted collections.

### Workflow 5: Abstain and request review

**System outcomes:**

| Outcome | Meaning |
|---|---|
| `proposed` | Exactly one clearly leading, compatible candidate and no blocking issue. Still requires human approval. |
| `ambiguous` | Candidates exist but the system cannot justify choosing one. The top candidate is shown **without** a "suggested" badge. |
| `unmatched` | No acceptable candidate. Near-misses may be listed as disqualified/low-score. |

**Decision procedure (in order):**
1. No listed candidates → `unmatched`, reason `NO_CANDIDATE`.
2. P empty (all listed candidates disqualified) → `unmatched`, reason `NO_COMPATIBLE_CANDIDATE`.
3. Collect **abstention reasons** (any one forces `ambiguous`):
   - `MULTIPLE_CANDIDATES`: |G| ≥ 2.
   - `SPEC_MISSING_DISCRIMINATOR`: |G| ≥ 2 and members differ on a spec attribute the request does not specify (replaces `MULTIPLE_CANDIDATES` as the more specific reason).
   - `LOW_SIMILARITY`: top score < `T_PROPOSE`.
   - Any **blocking request issue**: `MISSING_QUANTITY`, `MISSING_UNIT`, `UNKNOWN_UNIT`, `UNIT_CONFLICT`, `FRACTIONAL_COUNT`, `SPEC_CONFLICT_IN_REQUEST`.
   - `UNIT_INCOMPATIBLE` with the top candidate.
4. No reasons → `proposed`.

Every reason is stored as a code and rendered in plain language on the item page. A close textual match never becomes `proposed` on score alone.

**Override.** A reviewer may approve any listed candidate (including on `ambiguous` lines, with explicit selection and no preselected default) or correct to any catalog product. Such decisions record `overrode_system = true` when the chosen product differs from the system's top-ranked candidate **or** the system outcome was not `proposed`. For `reject` and `confirm_no_match`, `overrode_system = true` only when the system outcome was `proposed` (the human contradicts a suggestion). The system's outcome/reasons at decision time are snapshotted on the decision.

### Workflow 6: Review and correct

- **Preconditions:** RFQ exists; line item exists.
- **Inspect:** raw input, normalized line (with changed fields highlighted), issues, candidates (rank, sku, name, uom, attributes, similarity, flags/conflicts), system outcome and reasons, decision history.
- **Decision types and effects:**

| Decision | Requires | New review status |
|---|---|---|
| `approve` | `product_sku` that is a **listed candidate**; effective quantity+unit | `approved` |
| `correct` | `product_sku` in the catalog that is **not** a listed candidate; effective quantity+unit | `corrected` |
| `reject` | `note` (3–500 chars) | `rejected` |
| `confirm_no_match` | none (note optional) | `no_match` |

- **Effective quantity/unit:** the line's normalized value unless the request supplies `quantity`/`unit` overrides; both must be present and valid (same parsing rules; unit must be dimension-compatible with the product `uom`, else `UNIT_INCOMPATIBLE`). This is how a reviewer resolves `MISSING_QUANTITY/UNIT`.
- **Allowed transitions:** any status → any decided status (revision allowed; every revision appends a decision). There is no return to `pending` (no "reopen" in MVP).
- **Staleness:** the request carries `expected_version`; the server updates only if it equals the line item's current `version` (optimistic concurrency); mismatch → 409 `STALE_VERSION` with the current item, and the UI offers "Reload". Each successful decision increments `version`.
- **Visibility:** status badge (text + icon) in all lists; counts on the RFQ summary.

### Workflow 7: Export results

- `GET /rfqs/{id}/export?format=csv|json&allow_incomplete=false`.
- **Completeness:** an RFQ is *complete* when no line item is `pending`. If incomplete and `allow_incomplete` is not `true` → 409 `RFQ_INCOMPLETE` (UI shows count of pending lines and a "Export finalized lines only" option).
- **CSV (final data only):** one row per **finalized match** (`approved`/`corrected`). Columns (fixed order): `line_no, original_description, catalog_sku, catalog_name, requested_quantity, requested_unit, quantity_in_catalog_uom, catalog_uom, review_status, overrode_system, reviewed_at`. UTF-8, `\n`, RFC 4180 quoting, values beginning with `= + - @` prefixed with `'` to prevent spreadsheet formula injection. No price column exists.
- **JSON:** `{ "rfq": {...}, "complete": bool, "finalized": [...same fields...], "not_finalized": [{line_no, original_description, review_status, system_outcome, reason_codes, suggestion: {...}|null}] }`. Anything under `suggestion` is explicitly labelled as unapproved system output.
- `rejected`, `no_match` and `pending` lines never appear in the CSV; they appear in the JSON `not_finalized` list.

### Workflow 8: Run the evaluation

- **Command:** `make eval` ⇒ `python -m rfq_eval run --dataset eval/dataset/v1 --system both --out eval/reports/latest`.
- **Isolation:** the evaluator imports `domain/` only. It does **not** use the database, the API, or any review decision; manual review actions cannot influence results.
- **Steps:** (1) verify `eval/dataset/v1/MANIFEST.sha256` against the files (mismatch → exit code 2, `DATASET_MODIFIED`); (2) load catalog and cases; (3) run `baseline` and `proposed` on each case; (4) compute metrics (Section K); (5) write outputs.
- **Outputs:** `results.jsonl` (per case, per system, raw), `report.json` (deterministic metrics + metadata), `report.md` (rendered from the JSON), and a separate `timing.json` (wall-clock; excluded from the determinism guarantee).
- **Reproducibility:** `report.json`/`report.md`/`results.jsonl` are byte-identical across repeated runs for the same dataset, config, code revision and container image. No timestamps, absolute paths, or timing values inside them.

---

## F. UX and Screen Specifications

**Routes:** `/` RFQ list · `/rfqs/new` create/import · `/rfqs/[id]` summary, normalization results and review queue · `/rfqs/[id]/items/[itemId]` item review. The evaluation "screen" is documented CLI output (screen 6).

**Cross-cutting UI rules**
- Status is conveyed by **icon + text label + shape**, never color alone:

| State | Label (always visible text) | Icon |
|---|---|---|
| System `proposed` (pending) | "Suggested: needs approval" | ◇ |
| System `ambiguous` | "Ambiguous: choose or reject" | ⚠ |
| System `unmatched` | "Unmatched" | ∅ |
| `approved` | "Approved" | ✓ |
| `corrected` | "Corrected" | ✓✎ |
| `rejected` | "Rejected" | ✕ |
| `no_match` | "Confirmed no match" | ∅✓ |

- Similarity is shown as a number plus the word "similarity" with a tooltip: "Text similarity, not a probability or confirmation."
- Ambiguous lines never display a "Suggested" badge or a preselected radio.
- All API errors are shown with the server `message` and `request_id`; no stack traces.
- State lives on the server; refresh restores everything. Filters live in the URL query string; browser back/forward work.
- Keyboard accessible; visible focus; forms have labels; async results announced via `aria-live="polite"`; contrast ≥ 4.5:1; layout works from 360 px to 1440 px (tables become stacked cards under 768 px).

### Screen 1: RFQ creation and CSV import (`/rfqs/new`)
- **Purpose:** create an RFQ from pasted text or CSV.
- **Components:** name field; tabs "Paste" / "CSV file"; textarea with grammar hint; file picker with column help; "Load sample RFQ" button (inserts bundled synthetic text); submit button; error panel.
- **Primary action:** "Create RFQ". **Secondary:** load sample, clear, "Import N valid lines, skip M" (after errors).
- **Empty state:** helper text and sample button. **Loading:** button disabled with "Creating…", `aria-busy`. **Error:** file-level error banner or row-error table (line, code, message, raw text). **Validation feedback:** inline name errors, client-side checks for file extension/size.
- **Refresh/navigation:** unsaved form content is not persisted; on success navigate to `/rfqs/[id]`.

### Screen 2 + 3 + 5: RFQ page (`/rfqs/[id]`): normalization results, review queue, summary & export
- **Purpose:** see what was normalized and matched, work the queue, export.
- **Components:** header (name, created time, source, skipped-lines banner); summary counts by review status and by system outcome; **Export** menu; table with columns: line #, original text, normalized description, quantity/unit (with conversion note), issues, system outcome badge, review status badge, link "Review"; filters: status (default "pending"), outcome; "Next pending" button.
- **Data displayed:** raw vs normalized side by side; issue chips with text.
- **Primary action:** open next pending line. **Secondary:** filters, export CSV/JSON.
- **Empty state:** "No lines match these filters." **Loading:** skeleton rows. **Error:** retry banner with request id. **Validation:** export when incomplete shows a dialog explaining `RFQ_INCOMPLETE` and offering "Export finalized lines only".
- **Refresh/navigation:** filters from URL; counts re-fetched.

### Screen 4: Item review (`/rfqs/[id]/items/[itemId]`)
- **Purpose:** inspect and decide one line.
- **Components:** raw input block; normalized block with changed values marked ("changed" text, not just color); issues list; **candidate list** (radio group; each with rank, SKU, name, uom, attributes, similarity, flags such as "Spec conflict: size", "Unit incompatible"); reason list in plain language; quantity/unit inputs (prefilled when known; required if missing); catalog search box ("Correct to another product"); note field; decision buttons: **Approve selected**, **Correct to searched product**, **Reject**, **Confirm no match**; decision history list.
- **Primary action:** the decision. Approve is disabled until a candidate is explicitly selected for `ambiguous`/`unmatched` lines; for `proposed` lines the top candidate is preselected and labelled "Suggested".
- **Empty states:** no candidates → "No candidate found"; no history → "No decisions yet". **Loading/Error:** as above. **Validation feedback:** inline errors mapped from API `details` (`QUANTITY_REQUIRED`, `UNIT_INCOMPATIBLE`, note too short). **409 STALE_VERSION:** banner "This line changed elsewhere", with Reload; form content is kept where possible.
- **After success:** status badge updates, history appended, "Next pending" shortcut.

### Screen 6: Evaluation (documented CLI output)
- README documents the `make eval` command, the output files, how to read `report.md`, and the "Incorrect confident matches" and "Missed escalations" sections with example cases. A web view is out of MVP (cut-list item 2).

---

## G. Domain Model and Data Definitions

All IDs are UUIDv4 (`uuid`), except catalog `sku` (stable text). Timestamps are `timestamptz` UTC. Enumerations are Postgres enums or `CHECK` constraints.

### RFQ (`rfqs`)
| Field | Type | Req | Validation | Meaning |
|---|---|---|---|---|
| id | uuid | Y | PK | Identifier |
| name | text | Y | 1–80 chars trimmed | User label |
| source_type | enum(`paste`,`csv`) | Y | | Input channel |
| catalog_version | text | Y | matches loaded catalog file hash prefix | Catalog used |
| matching_config_hash | text | Y | sha256 of `matching_config.json` | Config used |
| skipped_count | int | Y | ≥ 0 | Lines skipped by `skip_invalid` |
| created_at | timestamptz | Y | default now | |

### RFQ line item (`rfq_line_items`)
| Field | Type | Req | Validation | Meaning |
|---|---|---|---|---|
| id | uuid | Y | PK | |
| rfq_id | uuid | Y | FK → rfqs, cascade | |
| line_no | int | Y | ≥ 1; **unique (rfq_id, line_no)** | Order in the input (post-skip, 1-based) |
| source_row | int | Y | ≥ 1 | Original line/row number in the input |
| raw_input | text | Y | ≤ 2000 chars | Exact input line/row (**raw input**) |
| description_raw | text | Y | non-empty | Parsed description as supplied |
| quantity_raw | text | N | | Quantity text as supplied |
| unit_raw | text | N | | Unit text as supplied |
| description_normalized | text | Y | | **Normalized** description |
| spec | jsonb | Y | keys ⊆ {size_mm,length_mm,thread,material,class,grade} | Extracted attributes |
| quantity | numeric(14,3) | N | > 0 | Normalized quantity |
| unit | text | N | in unit dictionary | Canonical unit |
| issues | jsonb | Y | array of {code,severity,detail} | Normalization issues |
| system_outcome | enum(`proposed`,`ambiguous`,`unmatched`) | Y | | Matcher verdict |
| reason_codes | text[] | Y | | Abstention/unmatched reasons |
| review_status | enum(`pending`,`approved`,`corrected`,`rejected`,`no_match`) | Y | default `pending` | **Confirmed human state** |
| final_sku | text | N | FK → catalog; set iff status ∈ {approved, corrected} | Human-confirmed product |
| final_quantity | numeric(14,3) | N | set iff final_sku set | Human-confirmed quantity |
| final_unit | text | N | set iff final_sku set | Human-confirmed unit |
| version | int | Y | default 1 | Optimistic-concurrency counter |
| created_at / updated_at | timestamptz | Y | | |

### Catalog product (`catalog_products`, seeded from `data/catalog.json`)
| Field | Type | Req | Validation | Meaning |
|---|---|---|---|---|
| sku | text | Y | PK, pattern `[A-Z]{2,4}-\d{3}` | Stable identifier |
| name | text | Y | | Product name |
| category | text | Y | | pipe, fitting, fastener, valve, consumable… |
| uom | text | Y | in unit dictionary | Catalog unit of measure |
| attributes | jsonb | Y | keys ⊆ spec keys; values canonical | Structured attributes |
| aliases | text[] | Y | may be empty | Synthetic alternative names |

Seeding is idempotent upsert by `sku`. **No price field.**

### Candidate match (`candidate_matches`): **suggestions only, never confirmation**
| Field | Type | Req | Validation | Meaning |
|---|---|---|---|---|
| id | uuid | Y | PK | |
| line_item_id | uuid | Y | FK, cascade | |
| rank | int | Y | 1..5; **unique (line_item_id, rank)** | Order after sorting |
| sku | text | Y | FK → catalog | |
| similarity | numeric(5,4) | Y | 0..1 | Lexical similarity (not a probability) |
| disqualified | bool | Y | | Spec conflict present |
| flags | jsonb | Y | array of codes (`SPEC_CONFLICT:size_mm`, `UNIT_INCOMPATIBLE`, …) | Per-candidate checks |
| conversion | jsonb | N | {factor, quantity_in_uom} | Present when unit is convertible |

### Review decision (`review_decisions`): append-only
| Field | Type | Req | Validation | Meaning |
|---|---|---|---|---|
| id | uuid | Y | PK | |
| line_item_id | uuid | Y | FK | |
| decision_type | enum(`approve`,`correct`,`reject`,`confirm_no_match`) | Y | | |
| sku | text | N | required for approve/correct | |
| quantity / unit | numeric / text | N | required (effective) for approve/correct | |
| note | text | N | ≤ 500; required for reject (≥ 3) | |
| overrode_system | bool | Y | | See Workflow 5 |
| system_outcome_snapshot | enum | Y | | Outcome at decision time |
| reason_codes_snapshot | text[] | Y | | Reasons at decision time |
| status_before / status_after | enum | Y | | Transition |
| version_before | int | Y | | Version the client saw |
| created_at | timestamptz | Y | | |

### Evaluation case (file-based, `eval/dataset/v1/cases.jsonl`; not in the database)
| Field | Type | Req | Meaning |
|---|---|---|---|
| id | string | Y | `E-001`… |
| category | enum | Y | One of the Section J categories |
| input | string | Y | A single pasted-text line (same grammar as Workflow 1) |
| expected_outcome | `match`/`review`/`unmatched` | Y | Ground-truth label |
| expected_sku | string/null | Y | Required iff `match` |
| expected_normalized | object | N | Labelled subset of {quantity, unit, spec, issue_codes} |
| rationale | string | Y | Why, citing catalog facts (not matcher behavior) |
| label_pass | object | Y | `{labelled_by, second_pass_done: true}` |

**Relationships & constraints:** RFQ 1—N line items; line item 1—N candidates (≤ 5); line item 1—N decisions; line item N—0..1 catalog product via `final_sku`. Cascade deletes are not exposed by the API.

**Status transitions (review_status):** `pending → {approved, corrected, rejected, no_match}`; any decided status → any decided status. `final_*` fields are cleared when the new status is `rejected` or `no_match`.

---

## H. API Contract

Base path `/api/v1`. JSON UTF-8. Next.js proxies `/api/*` to the backend, so the browser sees one origin (no CORS config needed in production mode).

**Error contract (all non-2xx):**
```json
{ "error": { "code": "STRING_CODE", "message": "Human-readable, safe", "details": [ { "field": "optional", "code": "optional", "message": "..." } ], "request_id": "uuid" } }
```
Pydantic validation errors map to `VALIDATION_ERROR` (422). Unhandled exceptions return `INTERNAL_ERROR` (500) with a generic message; the stack trace is logged server-side with the same `request_id`. Every response carries `X-Request-ID`.

| # | Method & path | Purpose | Request | Success | Errors / notes |
|---|---|---|---|---|---|
| 1 | `GET /health` | Liveness + DB check | | 200 `{status:"ok"}` | 503 `DB_UNAVAILABLE` |
| 2 | `POST /rfqs` | Parse, normalize, match, persist | `{name, source_type, content, skip_invalid=false}` | 201 `RFQ` + `items_summary` + `skipped[]` | 422 `ROW_ERRORS` (`details` = row errors with `row`, `code`, `message`, `raw`), 422 `NO_VALID_ROWS`, `MISSING_REQUIRED_COLUMN`, `EMPTY_FILE`, `NO_ROWS`, `DUPLICATE_COLUMN`, `UNSUPPORTED_ENCODING`; 413 `INPUT_TOO_LARGE`. Atomic: nothing saved on error. Not idempotent. |
| 3 | `GET /rfqs` | List RFQs | `?limit=50&offset=0` | 200 `{items:[RFQ+counts], total}` | 422 on bad paging (limit 1–100) |
| 4 | `GET /rfqs/{id}` | RFQ summary | | 200 `RFQ` + counts by review_status and system_outcome + `complete` | 404 `RFQ_NOT_FOUND` |
| 5 | `GET /rfqs/{id}/items` | Line items with candidates | `?review_status=&system_outcome=&limit=200&offset=0` | 200 `{items:[LineItem+candidates], total}` | 404; 422 invalid enum |
| 6 | `GET /rfqs/{id}/items/{item_id}` | One item + candidates + decisions | | 200 `LineItemDetail` | 404 `ITEM_NOT_FOUND` |
| 7 | `POST /rfqs/{id}/items/{item_id}/decisions` | Record a decision | `{decision_type, expected_version, sku?, quantity?, unit?, note?}` | 201 `{decision, item}` (item has new `version`) | 409 `STALE_VERSION` (body includes current item); 422 `SKU_NOT_A_CANDIDATE` (approve), `SKU_IS_A_CANDIDATE` (correct), `SKU_NOT_FOUND`, `QUANTITY_REQUIRED`, `UNIT_REQUIRED`, `UNIT_INCOMPATIBLE`, `NOTE_REQUIRED`, `INVALID_QUANTITY`. Executed in one transaction with `UPDATE … WHERE id=? AND version=?`; zero rows ⇒ 409. |
| 8 | `GET /catalog` | Search catalog (for corrections) | `?q=&limit=20` | 200 `{items:[Product], total}` | q ≤ 80 chars; case-insensitive substring over sku/name/aliases; ordered by sku |
| 9 | `GET /rfqs/{id}/export` | Export | `?format=csv|json&allow_incomplete=false` | 200 file (`text/csv; charset=utf-8` with `Content-Disposition`, or JSON) with header `X-Items-Excluded: N` | 409 `RFQ_INCOMPLETE`; 422 bad format; 404 |

**Concurrency/idempotency summary:** decisions are protected by `expected_version`; replaying a decision request with a stale version returns 409 and changes nothing. RFQ creation is not idempotent (UI disables submit while pending). Reads are side-effect free.

**Not provided (out of scope):** delete/update RFQ, re-run matching, evaluation endpoint (cut-list item 2), authentication.

---

## I. Matching and Normalization Rules

Section E, Workflows 3–5, is normative for rules. This section fixes the data contracts and open parameters.

**Canonical line item:** `NormalizedLine` as defined in Workflow 3.

**Catalog attribute canonical forms:** `size_mm`/`length_mm` Decimal strings without trailing zeros; `thread` `M<d>`; `material` ∈ {GI, MS, SS304, SS316, PVC, BRASS, CU}; `class` ∈ {A,B,C}; `grade` ∈ {4.6, 8.8, 10.9}. Catalog items must declare **every** attribute that distinguishes them from siblings (checked by a catalog-validation test).

**Parameters to be fixed during Phase 1 (not authoritative here):**

| Parameter | Meaning | Provisional seed (hypothesis only) | Rule |
|---|---|---|---|
| `K` | max listed candidates | 5 | fixed |
| `T_MIN_CANDIDATE` | minimum similarity to list | 0.30 | choose using the **dev set** |
| `T_PROPOSE` | minimum top similarity for `proposed` | 0.60 | choose using the dev set |
| `T_MARGIN` | near-tie gap | 0.10 | choose using the dev set |

The seeds are starting points for the dev set, **not requirements**. The implementer must (1) tune only against `eval/dev/cases.jsonl` (never the frozen set), (2) record the chosen values and the dev-set evidence in `data/matching_config.json` (`rationale` field) and `EVAL_LOG.md`, and (3) commit them before the first frozen-set run.

**Lexical similarity ≠ equivalence.** A high similarity can still be `ambiguous` (near-tie, missing discriminator, unit/spec problems). Approval is always a human act. When the system cannot safely determine a result it returns `ambiguous` or `unmatched` with reason codes, never a guess.

**Match tie handling:** equal (rounded) scores order by sku ascending; a tie within `T_MARGIN` between plausible candidates always abstains.

---

## J. Synthetic Catalog and Frozen Evaluation Dataset

**Planning targets (subject to feasibility; see Kill criteria):** ~100 catalog products, 40 frozen cases, plus a **12-case dev set** (new vs. the audit; its purpose is to set thresholds without contaminating the frozen set, and its cost is inside the Phase 1 budget).

**Catalog construction.** Hand-authored (optionally via a small committed generator script; the committed JSON is the source of truth). Families with deliberate near-duplicates: GI pipes (sizes × classes A/B), MS and SS304 hex bolts (thread × length), nuts, washers, GI elbows/tees/sockets (sizes), brass ball valves and gate valves (sizes), PVC pipes (sizes), PVC elbows, plus consumables to cover each unit dimension (welding electrodes in `kg`, PTFE tape in `roll`, paint in `ltr`, wire/pipe in `mtr`). Each product has 0–3 aliases. A catalog-validation test enforces unique SKUs, canonical attributes, and that siblings differ in at least one declared attribute.

**Frozen set composition (target 40):**

| Category | Cases | Expected |
|---|---|---|
| Exact/clean match | 5 | match |
| Harmless variation (case, punctuation, abbreviations) | 5 | match |
| Supported unit alias or convertible unit (e.g. ft → mtr) | 4 | match |
| Unit incompatible (e.g. `nos` for a `mtr` item) | 3 | review |
| Missing quantity | 2 | review |
| Missing or unknown unit | 3 | review |
| Conflicting spec: request internally conflicting | 1 | review |
| Conflicting spec: catalog has no compatible size/material (near-miss) | 2 | unmatched |
| Near-duplicate products with missing discriminator | 3 | review |
| Multiple plausible candidates | 2 | review |
| Unknown catalog item | 3 | unmatched |
| Mixed Hindi–English / transliterated | 4 | 3 match, 1 review |
| Malformed/incomplete but ingestible (dimension tail `x 50`, leading quantity, fractional count) | 3 | review |
| **Total** | **40** | **17 match · 18 review · 5 unmatched** |

Inputs that cause **hard row errors** (e.g. `INVALID_QUANTITY`) never reach the matcher, so they are covered by ingestion/API tests, not the benchmark.

**Ground truth contents:** per case see Evaluation case in Section G. `expected_normalized` includes only fields the labeller can justify.

**Labelling process:**
1. Write catalog first. 2. Write each case and label from catalog facts; the `rationale` must cite them. 3. **Second pass** at least 24 hours later: re-derive each label from the rationale without looking at the first label; resolve disagreements in `eval/dataset/v1/LABEL_NOTES.md`. 4. Limitation recorded: single labeller.
5. Labels are never edited to match matcher output.

**Freeze protocol.**
- `eval/dataset/v1/MANIFEST.sha256` lists SHA-256 of `catalog.json`, `cases.jsonl`, and `aliases.json`/`vocab.json` copies. Commit and tag `dataset-v1-frozen` **before any matcher code exists** (the baseline may exist; it is part of the harness).
- The evaluator verifies the manifest (exit 2 on mismatch). Any later change requires a new dataset version (`v2`), and old results are not compared as if they were the same benchmark.
- **Contamination rule:** if the matcher, normalizer, aliases, vocab or config change **after** frozen-set results have been viewed, the report must say so (`EVAL_LOG.md`), and later numbers are labelled "contaminated by tuning". The dev set exists to prevent this.

**Naive baseline** defined in Workflow 4, implemented and run in Phase 1 to prove the harness works.

---

## K. Metrics and Evaluation Methodology

Notation: `E` = expected outcome (`match`/`review`/`unmatched`), `P` = system outcome. A case is **correct-proposed** iff `P=proposed` and `E=match` and the top candidate's sku equals `expected_sku`. The baseline's `proposed` means "picked a product".

| # | Metric | Computation | Denominator | Edge cases |
|---|---|---|---|---|
| M1 | **Top-candidate correct rate** | correct-proposed ÷ N(`E=match`) | cases with `E=match` | 0 → `null` |
| M2 | **Proposed precision** | correct-proposed ÷ N(`P=proposed`) | all proposed | 0 proposed → `null` |
| M3 | **Incorrect confident suggestions** | N(`P=proposed` and not correct-proposed); also as a rate over N(`P=proposed`) | N(`P=proposed`) for the rate | each such case is listed with input, expected, got |
| M4 | **Missed escalations** | N(`P=proposed` and `E∈{review,unmatched}`); rate over N(`E∈{review,unmatched}`) | cases with `E∈{review,unmatched}` | listed with examples |
| M5 | **Over-abstention rate** | N(`E=match` and `P≠proposed`) ÷ N(`E=match`) | cases with `E=match` | quantifies reviewer burden |
| M6 | **Appropriate abstention** | N(`E=review` and `P≠proposed`) ÷ N(`E=review`) | `E=review` | |
| M7 | **Unmatched detection** | N(`E=unmatched` and `P=unmatched`) ÷ N(`E=unmatched`); also report how many were `proposed` | `E=unmatched` | strict: `ambiguous` does not count |
| M8 | **Normalization accuracy** | per field (quantity, unit, each spec key, issue-code set): exact matches ÷ labelled values | labelled values of that field | proposed system only; baseline `n/a` |
| M9 | **Validation-rule violations** | N(`P=proposed` where an independent check using the **labelled** `expected_normalized` finds unit-dimension incompatibility or spec conflict with the proposed product; only cases with labelled values are checked, and the count of checked cases is reported) | N(`P=proposed`) | by design should be 0; non-zero is a bug report |
| M10 | **Runtime** | wall-clock for the run | n/a | reported only in `timing.json` |

**Rules:**
- Human-corrected review results are **never** mixed into these metrics; the evaluator ignores the database.
- "Improvement" may be claimed only as a documented comparison of baseline vs proposed on the **same frozen cases**, stated as "on 40 synthetic cases".
- Every number in `report.json` includes `dataset_version`, `dataset_manifest_sha256`, `config_sha256`, `code_revision` (from `GIT_SHA` env, `"unknown"` if absent, `+dirty` suffix when the tree has uncommitted changes), the command, and a pointer to `results.jsonl`.
- `report.md` begins with the limitation statement: "Results are on 40 synthetic cases authored by the project owner; they are not real-world accuracy and do not show business impact." It lists every M3 and M4 case first, before positive results.

---

## L. Non-Functional Requirements

| Area | Requirement |
|---|---|
| Reliability | App survives malformed input without 5xx; DB failures surface as `DB_UNAVAILABLE`/`INTERNAL_ERROR`; creation is transactional (all or nothing). |
| Input validation | All API inputs validated by Pydantic; limits in Workflow 1; string fields length-capped; enums enforced. |
| Determinism | Matching, normalization and evaluation have no randomness/time dependence; `PYTHONHASHSEED=0`; stable sorting. |
| Error handling | Single error contract (Section H); no internal messages or stack traces to clients; request IDs logged. |
| Security | Section N. |
| Data integrity | FKs, uniqueness constraints, check constraints (`final_*` iff finalized), optimistic concurrency, append-only decisions. |
| Accessibility | WCAG 2.1 AA target for implemented screens: keyboard-complete, labels, focus order, contrast, non-color status, `aria-live` for async status; automated axe checks on the four routes with zero serious/critical violations. |
| Responsive | 360–1440 px; no horizontal page scroll at 360 px. |
| Maintainability | `domain/` has no imports from FastAPI/SQLAlchemy (tested); ruff + mypy (strict on `domain/`) and ESLint + `tsc --noEmit` clean; rules live in data files where possible. |
| Performance (small scale) | Create a 200-line RFQ ≤ 2 s on the reference machine; list/detail API p95 ≤ 300 ms locally; full eval ≤ 10 s. |
| Local setup | See Section P. |
| Documentation | README, this PRD, `PRD_DECISIONS.md`, `EVAL_LOG.md`, dataset README, limitations section. |
| Observability | JSON structured logs with `request_id`; one log line per request (method, path, status, duration); `/health`. No metrics stack. |

---

## M. Testing and CI Strategy

| Level | Tooling | Must cover |
|---|---|---|
| Unit (domain) | pytest, table-driven | Every normalization rule (each unit alias group, quantity formats incl. rejects, free-text trailing rules 1–5, Devanagari digits, spec extraction incl. fractions and conflicts, stop words); conversions; similarity and ordering with ties; each abstention reason; baseline; catalog validation. |
| Property/invariants | pytest | Normalization is idempotent on descriptions; raw input preserved; matcher never returns `proposed` when any blocking issue or conflict exists; output independent of catalog order. |
| API/integration | pytest + FastAPI test client + **real Postgres** (service container) | CSV validation (each file- and row-level error), paste grammar, `skip_invalid` flows, error contract on every failure, decisions (all four types, transitions, 409 stale, 422 rules), persistence across app restart, export CSV/JSON incl. incomplete gating and formula-injection prefix, fresh DB init + seed idempotency. |
| Evaluation | pytest + CLI | Manifest verification (tamper → exit 2); two consecutive runs byte-identical; M-metric computation on a tiny fixture dataset with hand-computed expectations. |
| Frontend unit | Vitest + Testing Library + axe | Each screen's loading, empty, error, success and validation states; ambiguous lines show no "Suggested" badge/preselection; status text present without color. |
| E2E | Playwright (1 golden flow) | Paste sample → see outcomes → approve one, correct one, reject one → export CSV contains only finalized lines. (Cut-list item 5.) |

**Definition of done for any change:** ruff, mypy, pytest (all levels), ESLint, `tsc`, Vitest, build, and (on main) E2E all pass locally and in CI; the eval determinism job passes.

**CI (GitHub Actions):** jobs `backend` (lint, type, tests with Postgres service), `frontend` (lint, type, unit, build), `eval` (verify manifest; run `make eval` twice; `diff` the outputs), `e2e` (compose up, Playwright). Failures reproduce locally via the same `make` targets (`make lint`, `make test`, `make eval`, `make e2e`), documented in the README with the Docker image tags used in CI.

---

## N. Security and Data Handling

- Synthetic data only; the README states it must not be used with confidential procurement data and that the prototype is not production-hardened.
- No secrets committed; `.env.example` with placeholders; `.env` is git-ignored; configuration via environment variables (`DATABASE_URL`, `API_BASE_URL`, `GIT_SHA`, `LOG_LEVEL`).
- Parameterized queries via SQLAlchemy only; no string-built SQL.
- Strict input validation and size limits; CSV export neutralizes formula-leading characters; the frontend renders user text via React escaping (no `dangerouslySetInnerHTML`).
- Sanitized errors (Section H); security headers basic defaults via Next.js; CORS closed (same-origin proxy).
- **No authentication** in MVP: the app is local-first. If a public demo is deployed, it must document that anyone can read/write demo data, show a banner "Synthetic demo data. Do not enter real data.", and consider a reset command. Adding auth is justified only if a public deployment is kept (see decisions).
- Dependencies pinned (lockfiles); CI runs `pip-audit`/`npm audit` informationally (non-blocking).

---

## O. Architecture and Repository Layout

**Components:** Next.js frontend → (same-origin `/api` rewrite) → FastAPI → PostgreSQL. The evaluation CLI imports `domain/` directly; it shares code, not state, with the app.

**Data flow:** raw text/CSV → `services/ingest.py` (parse, hard/soft validation) → `domain/normalize.py` (+`units.py`, `quantity.py`, `specs.py`) → `domain/matcher.py` (candidates, outcome, reasons) → persisted line item + candidates → `services/review.py` (decisions, versioning) → `services/export.py`.

**Rules ownership:** units/conversions `domain/units.py`; quantity parsing `domain/quantity.py`; spec extraction `domain/specs.py`; normalization `domain/normalize.py`; matching/abstention `domain/matcher.py`; baseline `domain/baseline.py`; configuration data in `data/`.

**Evaluation isolation:** `rfq_eval` reads only `eval/dataset/*` and `data/*`; no DB driver imported; outputs to `eval/reports/`.

```
rfq-line-item-normalizer/
├─ README.md  PRD.md  PRD_DECISIONS.md  PRD_ACCEPTANCE_CHECKLIST.md  EVAL_LOG.md
├─ docker-compose.yml  .env.example  Makefile
├─ .github/workflows/ci.yml
├─ data/            catalog.json  aliases.json  vocab.json  matching_config.json
├─ eval/
│  ├─ dataset/v1/   cases.jsonl  MANIFEST.sha256  LABEL_NOTES.md  README.md
│  ├─ dev/          cases.jsonl
│  └─ reports/      latest/{results.jsonl, report.json, report.md, timing.json}
├─ backend/
│  ├─ pyproject.toml  Dockerfile  alembic/  alembic.ini
│  ├─ app/{main.py, api/, core/{config.py,errors.py,logging.py}, db/{models.py,session.py,seed.py},
│  │       services/{ingest.py,review.py,export.py},
│  │       domain/{units.py,quantity.py,specs.py,normalize.py,matcher.py,baseline.py,types.py}}
│  ├─ rfq_eval/{__main__.py,run.py,metrics.py,report.py}
│  └─ tests/{unit/, integration/, eval/}
└─ frontend/
   ├─ package.json  Dockerfile  next.config.mjs
   ├─ app/{page.tsx, rfqs/new/, rfqs/[id]/, rfqs/[id]/items/[itemId]/}
   ├─ components/  lib/{api.ts,types.ts}  tests/  e2e/
```

**Docker Compose:** services `db` (postgres:16, volume, healthcheck), `api` (waits for healthy db, runs `alembic upgrade head`, seeds catalog idempotently, serves on 8000), `web` (Next.js standalone build on 3000, `API_BASE_URL=http://api:8000`). Ports 3000/8000/5432 documented and overridable. No queues, caches, or extra services.

---

## P. Deployment and Developer Experience

- **Prerequisites (reference environment):** Docker Engine ≥ 24 with Compose v2, GNU make, git; ~4 GB free RAM; no local Python/Node needed to run. Reference: a 4-core/8 GB laptop with a warm Docker image cache; the 5-minute target excludes first-time image downloads (document both numbers).
- **Config:** `cp .env.example .env` (defaults work).
- **Run:** `make up` (= `docker compose up --build -d`), then open `http://localhost:3000`.
- **DB init/migrations:** Alembic migration `0001_initial`; applied on `api` start; catalog seeded from `data/catalog.json` by idempotent upsert.
- **Commands:** `make test` (backend+frontend unit/integration), `make lint`, `make eval` (sets `GIT_SHA`), `make e2e`, `make down`, `make reset-db`.
- **CI:** Section M.
- **Optional deployment:** a free-tier host for the demo only after all P0 checklist items pass; must carry the demo banner (Section N). Not required for completion.
- **Troubleshooting (README):** port conflicts, stale volume (`make reset-db`), Docker memory, CRLF line endings in shell scripts, `DATASET_MODIFIED` exit code 2, missing `GIT_SHA`.

---

## Q. Milestones and Scope Control

**Estimates are planning figures, not measurements.** Core build ≈ **30 h** planned, **35 h hard cap**; the 6–8 h timed-build rehearsal is a separate track and is not counted.

| Phase | Deliverable | Prerequisites | Acceptance criteria | Effort |
|---|---|---|---|---|
| **0. Existing work and application** (outside budget, ≤ 2 h) | IsoCode application submitted with CV, GitHub, best shipped project; existing repo tidied | none | Submission confirmed. Independent of whether this project is finished. | ≤ 2 h (not counted) |
| **1. Dataset and PRD validation** | PRD accepted; canonical schema & unit tables; `catalog.json` (~100); `eval/dev` (12 cases); `eval/dataset/v1` (40 cases + labels + second pass); harness skeleton + baseline; manifest + tag | PRD | Catalog-validation test passes; all 40 cases have rationale and second pass done; baseline runs and writes a report; manifest committed and tagged **before** matcher code | **7 h** (catalog 1.75, dev set 0.75, frozen set 2.5, baseline+harness skeleton 1.5, schemas/tables/freeze 0.5) |
| **2. Core normalization and matching** | `domain/` modules with unit tests; thresholds selected on dev set and recorded | Phase 1 freeze | All normalization rules tested; matcher unit tests (each abstention reason) pass; `matching_config.json` has rationale from dev-set evidence; no frozen-set run yet | **6.5 h** |
| **3. Review workflow and persistence** | DB + Alembic; ingest and review services; API endpoints; four frontend routes with all states; CSV/JSON export | Phase 2 | Golden flow works manually; API integration tests for validation, 409, export gating pass; fresh DB init verified | **9.5 h** (DB/migrations 1.5, ingest+API 3, frontend 4, export 1) |
| **4. Verification** | Full `rfq_eval` run on frozen set; failure inspection; regression tests for issues found; EVAL_LOG | Phase 3 (matcher stable) | Two consecutive runs byte-identical; M3/M4 cases listed with examples; limitations written; EVAL_LOG records the first frozen-set run | **3.5 h** |
| **5. Delivery and presentation** | README, CI green, E2E, optional deployed demo, 3-minute walkthrough, 1-page results note | Phase 4 | Clean-machine run per README succeeds; CI green; checklist P0 items pass | **3.5 h** |
| **Total** | | | | **30 h** (cap 35 h; contingency 5 h) |

**Early-warning indicators** and the response:
- Dataset work (catalog + dev set + frozen set) passes 6 h, or fewer than 30 trusted labelled frozen cases exist at that point → trigger Kill criterion 1. Phase 1 as a whole passing 9 h → start the cut list.
- Cumulative time > 17 h at end of Phase 2 → start the cut list (items 1–4).
- No working `make eval` by hour 24 → cut to Kill criterion 2 path immediately.

---

## R. Acceptance Criteria

Detailed, ID'd checks live in `PRD_ACCEPTANCE_CHECKLIST.md`. Summary by priority:

**P0 (required to call the project done)**
1. Clean-environment start via documented commands; app reachable; `/health` returns ok.
2. All supported normalization rules have automated tests; CI passes.
3. Frozen benchmark (40 cases + manifest + tag) is committed before any matcher code (verifiable from git history).
4. Baseline implemented; both systems reported on the same cases.
5. `make eval` twice yields byte-identical `results.jsonl`, `report.json`, `report.md`.
6. Report lists incorrect confident matches and missed escalations with example cases first.
7. Synthetic data and methodological limitations documented in README and report.
8. The application never produces a price and never sets `approved`/`corrected` without an explicit decision request.
9. An `ambiguous` line is never shown as "Suggested" and has no preselected candidate.
10. Persistence: decisions survive restart; `version` increments; stale submit returns 409 and changes nothing.
11. CSV handling: every file-level and row-level error in Workflow 2 has a test and a visible UI message.
12. API errors always use the error contract; no stack trace appears in any response.
13. Export CSV contains only `approved`/`corrected` lines; incomplete RFQ without `allow_incomplete` returns 409.
14. README lets an independent developer run, test and evaluate.
15. No claim about ClearQuote or IsoCode internals in repo text, UI, or report.

**P1:** accessibility automated checks pass; responsive at 360 px; Playwright golden flow; JSON export; evaluation `timing.json` produced; structured logs with request IDs.

**P2:** deployed demo with banner; pagination UI; evaluation HTTP endpoint.

---

## S. Risks, Assumptions, and Kill Criteria

| Risk / assumption | Mitigation / early warning |
|---|---|
| Dataset realism: synthetic RFQ language may look contrived | Keep domain vocabulary small and explicit; state limits; do not generalize results. |
| Single-labeller bias | Second pass after ≥ 24 h; label notes; disclose. |
| Tuning leakage | Dev set; frozen manifest; contamination rule; EVAL_LOG. |
| Over-building | Cut list in Section D; hour checkpoints in Section Q. |
| Hindi/transliteration correctness | Tiny reviewed dictionary only; ask a fluent reader to check entries if available (not a blocker). |
| Threshold fragility on 40 cases | Report counts, not just rates; disclose small-N. |
| Docker/CI environment drift | Pin image tags; document reference environment. |
| Application outcome unknown | Phase 0 is independent; project is reusable as a general portfolio piece. |

**Kill criteria (preserved from the audit):**
1. If a defensible labelled dataset cannot be produced within about **6 hours**, pivot away from the RFQ-specific dataset (use a generic-domain project) rather than inventing unrealistic cases.
2. If the project exceeds **35 hours** without a working evaluation command, cut scope to the deterministic normalizer and its tests.
3. If the IsoCode application results in a hiring rejection, stop bespoke investment and reuse the result as a general portfolio artifact.
4. If a founder says the idea is irrelevant, stop adding features intended to impress them.
5. Respect competing opportunities and deadlines; the application and existing shipped work take priority over Phases 2–5.
6. Stop any testing that conflicts with access restrictions, product terms, or responsible-disclosure obligations.

---

## T. Future Opportunities (not MVP)

| Idea | Evidence/collaboration needed before investing |
|---|---|
| Stronger matching (embeddings, optional LLM adapter) | A frozen benchmark showing where the deterministic matcher fails, and a fixed cost/reproducibility policy; the adapter must remain optional and off by default. |
| Evaluation on realistic data | Anonymized, permissioned samples from a real distributor; agreed labelling. |
| Integrations (email, WhatsApp, ERP), PDF/Excel ingestion | A stated need from an actual user/team and agreed formats. |
| Authentication, roles, audit export | A deployment that holds non-demo data. |
| More units/packaging (pack sizes) | Catalog data defining pack conversions. |
| Web evaluation dashboard | Reader feedback that the CLI report is insufficient. |

---

## U. Proof-of-Work and Impact Claims

| # | Claim | Can this standalone project support it? | Substantiating artifacts |
|---|---|---|---|
| 1 | Engineering quality | **Yes** | Repo, tests, CI history, architecture/data-flow description, clean-machine run instructions, 3-minute walkthrough |
| 2 | Improvement over the documented naive baseline on the frozen synthetic dataset | **Yes, narrowly** ("on 40 synthetic cases") | `report.json`/`report.md`, `results.jsonl`, dataset manifest hash + tag, code revision, `EVAL_LOG.md`, listed failures |
| 3 | Plausible relevance to ClearQuote's publicly described workflow | **Hypothesis**: only company feedback can validate | The outreach question in the audit (§10); no claim in artifacts beyond "inspired by a publicly described workflow" |
| 4 | Verified impact on IsoCode's engineering or business outcomes | **No**: requires their data, baselines and production access | None; the repo must say this explicitly |

The README must contain this table (or equivalent wording) so a reader cannot mistake claim 2 for claim 3 or 4.

---

## Appendix: Resolved Item Index

Unresolved or defaulted decisions are recorded with rationale, alternatives and consequences in `PRD_DECISIONS.md`. None blocks starting Phase 1; items marked "resolve before implementation" there (D1 thresholds are resolved *during* Phase 1) are scheduled in the plan above.
