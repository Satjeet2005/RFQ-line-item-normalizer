# Independent Second-Pass Labelling Instructions

## Objective

This package provides the materials and protocol for conducting the mandatory independent second labelling pass on the 40-case evaluation dataset for the RFQ Line-Item Normalizer project.

To prevent confirmation bias, this package intentionally **excludes** all previous labels, candidate SKUs, rationales, and category hints. The second reviewer must label every line independently using only the input string and the facts in `catalog.json`.

---

## Timing Requirement

> [!WARNING]
> Per `PRD.md` Section J and `PRD_DECISIONS.md` D7, this second pass must not be performed until **at least 24 hours** after the initial labelling pass.
> - **Initial Pass Timestamp:** `2026-10-16T15:10:00Z`
> - **Earliest Permitted Second Pass:** `2026-10-17T15:10:00Z`

---

## Labelling Rules & Criteria

For each case in `blind_cases.jsonl`, evaluate the line against `catalog.json` and determine:

### 1. `expected_outcome`

Assign exactly one of the three canonical outcomes:

- **`match`**:
  - The request clearly and unambiguously identifies a specific product in the catalog.
  - The requested technical attributes (size, material, class, thread, length, grade) fully agree with the chosen catalog product.
  - The requested unit of measure is compatible with the product's canonical `uom` (either identical or convertible within the same dimension, e.g. `ft` → `mtr` or `g` → `kg`).
  - Sibling catalog products (e.g. Class A vs Class B, or Grade 4.6 vs 8.8) are clearly discriminated by the input text.
  - `expected_sku` is **required** and must be the matching product's SKU (e.g. `PIPE-006`).

- **`review`**:
  - The line is ambiguous between multiple plausible catalog products (e.g. missing class, missing structural grade).
  - The line specifies an incompatible unit dimension (e.g. requesting count `nos` for an item tracked by length `mtr`, or weight `kg` for bolts tracked by count `nos`).
  - The line has missing quantity (e.g. bare unit without number) or missing unit (e.g. bare number without unit).
  - The line has an internally conflicting specification (e.g. "Class A Class B" or "GI MS").
  - The line has a fractional count unit (e.g. "12.5 nos").
  - Automatic proposal would require unverified assumptions or guesses.
  - `expected_sku` must be `null`.

- **`unmatched`**:
  - The requested product is entirely outside catalog scope (e.g. submersible pump, safety helmet).
  - The requested item is a "near-miss" where the core specification does not exist in the catalog (e.g. 70 mm GI pipe when the catalog only stocks 15, 20, 25, 32, 40, 50, 80, 100 mm; or brass hex bolt when fasteners are only stocked in MS and SS304).
  - Every catalog product conflicts on one or more requested specifications.
  - `expected_sku` must be `null`.

### 2. `expected_sku`
- Non-null string (e.g. `"BOLT-007"`) if and only if `expected_outcome == "match"`.
- Must be `null` if `expected_outcome` is `"review"` or `"unmatched"`.

### 3. `rationale`
- A concise explanation citing catalog facts and specifications (e.g. why a specific SKU matches, why sibling variants make the line ambiguous, or why no compatible size exists in the catalog).

---

## Submission Procedure

1. Copy `eval/second_pass/submissions/template_submission.jsonl` to `eval/second_pass/submissions/pass2_labels.jsonl`.
2. Fill out each line with your independent decisions.
3. Once completed, run the reconciliation tool to compare Pass 1 and Pass 2:
   ```bash
   python3 scripts/reconcile_second_pass.py --submission eval/second_pass/submissions/pass2_labels.jsonl
   ```
4. The script will report:
   - Schema validation results.
   - Agreement rate and Cohen's kappa.
   - Discrepancy table with side-by-side comparison.
5. Review each discrepancy, agree upon a reconciled label, document the resolution in `eval/dataset/v1/LABEL_NOTES.md`, and apply final labels before dataset freeze.
