# Evaluation Dataset v1 (`eval/dataset/v1`)

## Overview

This directory contains the frozen evaluation benchmark dataset for the RFQ Line-Item Normalizer project. The dataset models realistic, imperfect industrial procurement RFQ line items across pipes, fittings, fasteners, valves, and consumables.

## Structure

```
eval/dataset/v1/
├── cases.jsonl        # 40 labelled evaluation cases (JSON Lines)
├── catalog.json       # Frozen copy of the 100-item synthetic catalog
├── aliases.json       # Frozen copy of unit dictionary and Hindi transliterations
├── vocab.json         # Frozen copy of spec attribute vocabulary
├── MANIFEST.sha256    # Cryptographic integrity manifest
├── LABEL_NOTES.md     # Labelling rationale, edge-case audit, and second-pass record
└── README.md          # Dataset documentation
```

## Schema (`cases.jsonl`)

Each line in `cases.jsonl` is a self-contained JSON object with the following fields:

| Field | Type | Description |
|---|---|---|
| `id` | `string` | Unique identifier (`E-001` through `E-040`) |
| `category` | `string` | One of the 13 PRD Section J categories |
| `input` | `string` | Raw line-item text as supplied by the user |
| `expected_outcome` | `enum` | Expected system verdict: `"match"`, `"review"`, or `"unmatched"` |
| `expected_sku` | `string \| null` | Canonical product SKU; non-null if and only if `expected_outcome == "match"` |
| `expected_normalized` | `object \| null` | Subset of verifiable fields (`quantity`, `unit`, `spec`, `issue_codes`) |
| `rationale` | `string` | Explanation citing catalog facts and normalization rules |
| `label_pass` | `object` | Metadata including `labelled_by`, `created_at`, and `second_pass_done` |

## Category Composition (40 Cases)

| Category | Cases | Target Outcome |
|---|---|---|
| `exact_clean_match` | 5 | 5 `match` |
| `harmless_variation` | 5 | 5 `match` |
| `supported_unit_alias_or_convertible` | 4 | 4 `match` |
| `unit_incompatible` | 3 | 3 `review` |
| `missing_quantity` | 2 | 2 `review` |
| `missing_or_unknown_unit` | 3 | 3 `review` |
| `conflicting_spec_internal` | 1 | 1 `review` |
| `conflicting_spec_catalog_near_miss` | 2 | 2 `unmatched` |
| `near_duplicate_missing_discriminator` | 3 | 3 `review` |
| `multiple_plausible_candidates` | 2 | 2 `review` |
| `unknown_catalog_item` | 3 | 3 `unmatched` |
| `mixed_hindi_english_transliterated` | 4 | 3 `match`, 1 `review` |
| `malformed_incomplete_ingestible` | 3 | 3 `review` |
| **Total** | **40** | **17 match, 18 review, 5 unmatched** |

## Integrity Verification

The dataset is locked with a SHA-256 manifest. Any tampering with `cases.jsonl`, `catalog.json`, `aliases.json`, or `vocab.json` will cause the evaluator to terminate immediately with exit code 2 (`DATASET_MODIFIED`).

To verify integrity manually:
```bash
sha256sum -c MANIFEST.sha256
```

## Benchmark Status

- **Status:** **FROZEN** (`v1-frozen`, tagged `dataset-v1-frozen`).
- **Initial Labelling Pass:** Completed 2026-10-16T09:51:57Z.
- **Independent Second Pass:** Completed 2026-10-16T12:39:58Z by an isolated blind reviewer.
- **Waiver Applied:** `D33` (Project owner approved waiver of the 24-hour procedural delay; documented in `PRD_DECISIONS.md`).
- **Reconciliation:** Completed and documented in `LABEL_NOTES.md` (97.5% outcome agreement, 92.5% full agreement). All 40 cases reconciled and marked with `second_pass_done: true`.

## Known Limitations

1. **Synthetic data:** Cases approximate industrial procurement lines but do not represent actual customer transactions.
2. **Small benchmark size:** 40 cases provide targeted coverage of edge cases and critical failure modes, but statistical power is limited compared to large production datasets.
