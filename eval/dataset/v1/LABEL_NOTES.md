# Dataset v1 Labelling Notes and Audit Record

## 1. Principles and Methodology

The ground-truth labels in `eval/dataset/v1/cases.jsonl` were derived strictly from the catalog facts (`data/catalog.json`), unit dictionary (`data/aliases.json`), and the normalization and domain rules specified in `PRD.md` Section E and Section J.

Key principles followed:
- **Catalog independence:** Ground truth is independent of what the proposed matcher or naive baseline outputs.
- **Safety over guessing:** When an input lacks essential specifications (such as class or structural grade) needed to distinguish catalog siblings, the expected outcome is `review` (`SPEC_MISSING_DISCRIMINATOR`), never a speculative match.
- **Dimensional compatibility:** Converting between dimensions (e.g. count `nos` to length `mtr` or mass `kg`) is forbidden without explicit pack size or piece weight in the catalog; such requests require `review` (`UNIT_INCOMPATIBLE`).
- **Absence vs near-miss:** Items that cannot be mapped to any catalog product because of non-existent sizes or materials (e.g., 70mm GI Pipe, Brass Hex Bolts) are labelled `unmatched` because all candidate products conflict on core specifications.
- **No price fields:** No pricing data exists in the catalog or ground truth.

---

## 2. Initial Labelling Pass (Pass 1)

- **Timestamp:** `2026-10-16T09:51:57Z` (`15:21:57+05:30` IST)
- **Reviewer:** Single primary annotator
- **Revision:** `v1.0-draft`
- **Total Cases:** 40 cases
- **Outcome Distribution:**
  - `match`: 17 cases (42.5%)
  - `review`: 18 cases (45.0%)
  - `unmatched`: 5 cases (12.5%)

### Category Notes and Decision Rationale

| Category | Cases | Expected | Key Decision Rationale |
|---|---|---|---|
| **Exact / clean match** | E-001 – E-005 | `match` | Explicit description, nominal size, material/grade, and canonical unit. Maps directly to unique SKUs (PIPE-004, BOLT-007, PIPE-021, VALV-003, FITT-002). |
| **Harmless variation** | E-006 – E-010 | `match` | Case differences, punctuation commas/hyphens, abbreviation expansions ("MILD STEEL" for MS, "PCS" for nos, "GR 8.8" for Grade 8.8, "P.T.F.E." for PTFE). Normalization handles them cleanly. |
| **Supported unit alias / convertible** | E-011 – E-014 | `match` | Same-dimension conversion: `ft` to `mtr` (100 ft = 30.48 mtr) and `g` to `kg` (25000 g = 25 kg); unit aliases `piece` -> `nos` and single-letter `l` -> `ltr`. |
| **Unit incompatible** | E-015 – E-017 | `review` | Count vs length (`nos` for pipe in `mtr`), mass vs count (`kg` for bolts in `nos`), count vs length (`mtr` for PTFE tape in `roll`). Incompatible dimensions cannot be safely automated. |
| **Missing quantity** | E-018, E-019 | `review` | Free-text lines terminating in bare unit token (`mtr`, `nos`) without a number trigger `MISSING_QUANTITY`. |
| **Missing or unknown unit** | E-020 – E-022 | `review` | Trailing numbers with missing unit (`50`, `100`) trigger soft issue `MISSING_UNIT`. Unrecognized unit token (`bundles`) is not in unit dictionary, causing `MISSING_QUANTITY` per trailing rule 5. |
| **Conflicting spec (internal)** | E-023 | `review` | Request specifies both `Class A` and `Class B` on the same line, producing `SPEC_CONFLICT_IN_REQUEST`. |
| **Conflicting spec (catalog near-miss)** | E-024, E-025 | `unmatched` | 70mm GI pipe does not exist in standard catalog nominal bores (15, 20, 25, 32, 40, 50, 80, 100mm). Brass hex bolts do not exist in catalog (fasteners only in MS and SS304). Conflicting specs with all candidates lead to `unmatched`. |
| **Near-duplicate missing discriminator** | E-026 – E-028 | `review` | Sibling products differ only by class (PIPE-003 Class A vs PIPE-004 Class B) or grade (BOLT-005 Gr 4.6 vs BOLT-014 Gr 8.8). Omitting the discriminator must not guess. |
| **Multiple plausible candidates** | E-029, E-030 | `review` | Ambiguous request tokens matching multiple distinct product families (Ball Valve vs Gate Valve for "Brass Valve 25mm"; Elbow vs Tee vs Socket for "GI Fitting 25mm"). |
| **Unknown catalog item** | E-031 – E-033 | `unmatched` | Products entirely absent from catalog scope: Submersible pumps, safety helmets, copper refrigeration tubing. |
| **Mixed Hindi–English / transliterated** | E-034 – E-037 | 3 `match`, 1 `review` | E-034 (`paip` -> pipe), E-035 (`pital` -> brass, `valv` -> valve, `nag` -> nos), E-036 (`nat` -> nut, Devanagari `नग` -> nos) match cleanly. E-037 (`kohni` -> elbow) lacks material and class, matching both GI and PVC elbows, requiring review. |
| **Malformed/incomplete ingestible** | E-038 – E-040 | `review` | E-038 (`M12 x 50` trailing dimension not parsed as quantity), E-039 (leading quantity `50 mtr` not parsed in free-text per trailing-only grammar), E-040 (`12.5 nos` fractional quantity for count unit triggers `FRACTIONAL_COUNT`). |

---

## 3. Second Labelling Pass Protocol & Status

Per `PRD.md` Section J and `PRD_DECISIONS.md` D7:
- A mandatory second pass must be conducted **at least 24 hours** after the initial labelling pass.
- **Initial Pass Creation Timestamp (mtime):** `2026-10-16T09:51:57Z` (`2026-10-16 15:21:57+05:30` IST)
- **Timezone Discrepancy Note:** Earlier drafts cited `15:10:00Z` due to treating local time (15:10 IST) as UTC (`Z`). That error placed the initial timestamp in the future. The verified real timestamp is `09:51:57Z`.
- **Second-Pass Submission Timestamp (provisional):** `2026-10-16T10:38:44Z` (`2026-10-16 16:08:44+05:30` IST)
- **Elapsed Time at Second Pass Creation:** 46 minutes 47 seconds (< 24 hours).
- **Earliest Permitted Second-Pass Gate (24h minimum):** `2026-10-17T09:51:57Z` (`2026-10-17 15:21:57+05:30` IST)
- **Current Dataset Status:** **RECONCILED & FROZEN**
- **Second Pass Done Status:** `second_pass_done: true` on all 40 cases.
- **Waiver Reference:** PRD Decision D33 (explicit project-owner waiver of calendar delay).

---

## 4. Pre-Freeze Independent Audit Findings (2026-10-16)

An independent automated and manual audit of the 40 cases against the 100-item catalog revealed the following specific label concerns:

1. **Case `E-001` (Input: `"GI Pipe 25mm Class B 10 mtr"`):**
   - *Current Label:* `expected_sku = "PIPE-004"`
   - *Catalog Fact:* `PIPE-004` is `"GI Pipe 20mm Class B"`.
   - *Proposed Correction:* `expected_sku = "PIPE-006"` (`"GI Pipe 25mm Class B"`).
   - *Audit Note:* The initial label suffered an index offset during manual entry (20mm vs 25mm).

2. **Case `E-034` (Input: `"GI paip 20mm Class A 30 mtr"`):**
   - *Current Label:* `expected_sku = "PIPE-002"`
   - *Catalog Fact:* `PIPE-002` is `"GI Pipe 15mm Class B"`.
   - *Proposed Correction:* `expected_sku = "PIPE-003"` (`"GI Pipe 20mm Class A"`).
   - *Audit Note:* The initial label suffered a catalog index offset.

3. **Rationale Citation Inconsistencies:**
   - *Case `E-015`:* Rationale text cites `PIPE-004` instead of `PIPE-006` for 25mm Class B pipe.
   - *Case `E-026`:* Rationale text cites `PIPE-003` and `PIPE-004` instead of `PIPE-005` and `PIPE-006` for 25mm GI pipe variants.

---

## 5. Independent Second-Pass Review Execution (Pass 2)

An independent annotator session (`independent_annotator`) was executed with access restricted strictly to:
- `eval/second_pass/blind_cases.jsonl`
- `eval/second_pass/catalog.json`
- `eval/second_pass/INSTRUCTIONS.md`

- **Execution Timestamp:** `2026-10-16T12:39:58Z` (`18:09:58+05:30` IST)
- **Submission Output:** `eval/second_pass/submissions/pass2_labels.jsonl`
- **Integrity Check:** 40 cases, unique IDs E-001 through E-040, valid schemas.
- **Pass 2 Outcome Counts:** 18 match, 17 review, 5 unmatched.

---

## 6. Inter-Annotator Reconciliation & Final Label Resolutions

Running `scripts/reconcile_second_pass.py` against Pass 1 and Pass 2 yielded:
- **Outcome Agreement:** 97.50% (39/40 cases agree on match/review/unmatched)
- **Full Agreement (Outcome + SKU):** 92.50% (37/40 cases)
- **Discrepancies Identified & Resolved:**

| Case ID | Input | Pass 1 Label | Pass 2 Label | Final Reconciled Decision | Supporting Evidence & Rationale |
|---|---|---|---|---|---|
| **`E-001`** | `"GI Pipe 25mm Class B 10 mtr"` | `match` / `PIPE-004` | `match` / `PIPE-006` | **`match` / `PIPE-006`** | Both passes agree on `match`. Catalog check confirms `PIPE-006` is 25mm Class B, while `PIPE-004` is 20mm Class B. Corrected typo in Pass 1. |
| **`E-034`** | `"GI paip 20mm Class A 30 mtr"` | `match` / `PIPE-002` | `match` / `PIPE-003` | **`match` / `PIPE-003`** | Both passes agree on `match`. `paip` translates to pipe; 20mm Class A is `PIPE-003`, while `PIPE-002` is 15mm Class B. Corrected typo in Pass 1. |
| **`E-015`** | `"GI Pipe 25mm Class B 50 nos"` | `review` / `null` | `review` / `null` | **`review` / `null`** | Both passes agree on `review`. Rationale citation updated to reference `PIPE-006` (25mm item) rather than `PIPE-004`. |
| **`E-026`** | `"GI Pipe 25mm 20 mtr"` | `review` / `null` | `review` / `null` | **`review` / `null`** | Both passes agree on `review`. Rationale citation updated to reference sibling pair `PIPE-005` (Class A) and `PIPE-006` (Class B). |
| **`E-039`** | `"50 mtr GI Pipe 25mm Class B"` | `review` / `null` | `match` / `PIPE-006` | **`review` / `null`** | Pass 2 treated leading quantity as match; however, governing PRD rule D9 and Section J Category 13 explicitly state that leading quantities in free text are NOT parsed and must flag `MISSING_QUANTITY`, forcing `review`. Reconciled strictly per PRD specification. |

All 40 reconciled cases have been applied to `eval/dataset/v1/cases.jsonl` with `second_pass_done: true` and documented review metadata.
