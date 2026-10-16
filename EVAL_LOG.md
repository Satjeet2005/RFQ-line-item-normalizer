# Evaluation Run Log (`EVAL_LOG.md`)

This log tracks every evaluation execution on the benchmark dataset to enforce methodological integrity, freeze discipline, and contamination transparency per `PRD.md` Section J and Section K.

---

## Run 1: Naive Baseline Harness Verification

- **Date:** 2026-10-16
- **Phase:** Phase 1 (Specification Validation and Evaluation Dataset Foundation)
- **Status:** **DRAFT BENCHMARK EXECUTION** (Dataset unfrozen; second labelling pass pending)
- **Dataset Version:** `v1-draft`
- **Dataset Manifest SHA-256:** `8877085ed6dc569d5bcc3794468bfb707f949b316e3812bb974fd90fa5ccebc6`
- **Config SHA-256:** `3f37679f4bbbe576847bf25cbe35306b3f136d76bd7686a0911ab8bfec0be043`
- **Command:** `python -m rfq_eval run --dataset eval/dataset/v1 --system both --out eval/reports/latest`
- **Code Revision:** `initial-phase1`
- **Contamination Status:** **UNCONTAMINATED**
  - The proposed matcher (`domain/matcher.py`) has **not** been implemented.
  - No matching thresholds have been tuned on frozen evaluation cases.
  - The naive baseline algorithm is fixed and has no parameters.
- **Harness Verification:**
  - Evaluator imports zero web or database frameworks (`test_isolation.py` PASSED).
  - Manifest verification detects tampering and exits with code 2 (`test_manifest.py` PASSED).
  - Successive runs produce byte-identical `results.jsonl`, `report.json`, and `report.md` (runtime isolated in `timing.json`).

### Baseline Metrics Summary (40 Cases)

| Metric | Name | Baseline Result |
|---|---|---|
| **M1** | Top-candidate correct rate | 70.59% (12 / 17 expected matches) |
| **M2** | Proposed precision | 31.58% (12 / 38 proposed) |
| **M3** | Incorrect confident suggestions | **68.42%** (26 cases proposed incorrectly) |
| **M4** | Missed escalations | **91.30%** (21 / 23 required escalations missed) |
| **M5** | Over-abstention rate | 0.00% (0 / 17) |
| **M6** | Appropriate abstention rate | 0.00% (0 / 18 - baseline never abstains) |
| **M7** | Unmatched detection rate | 40.00% (2 / 5 detected solely by zero token overlap) |
| **M8** | Normalization accuracy | n/a (baseline has no normalization engine) |
| **M9** | Validation rule violations | n/a |

### Observations:
The baseline exposes the exact safety hazard described in `PRD.md`: because lexical token overlap has no understanding of units, missing specifications, or near-duplicate product variants, it forces a confident suggestion on 38 out of 40 lines, causing 26 incorrect proposals and missing 21 critical review escalations.

### Sequencing and Freeze Protocol Check:
1. `second_pass_done: false` was set across all 40 cases in initial draft `eval/dataset/v1/cases.jsonl`.
2. Initial labelling pass creation timestamp: `2026-10-16T09:51:57Z` (`15:21:57+05:30` IST).
3. Project owner waiver `D33` approved waiving the 24-hour procedural delay for this iteration.
4. Independent blind second pass executed and recorded at `2026-10-16T12:39:58Z`.
5. Reconciliation completed in `LABEL_NOTES.md`. Reconciled labels applied to `cases.jsonl` with `second_pass_done: true`.

---

## Run 2: Final Frozen Benchmark Evaluation (Phase 1 Baseline)

- **Date:** 2026-10-16
- **Phase:** Phase 1 (Specification Validation and Evaluation Dataset Foundation)
- **Status:** **FROZEN BENCHMARK EXECUTION** (Dataset frozen; second pass completed and reconciled; tagged `dataset-v1-frozen`)
- **Dataset Version:** `v1-frozen`
- **Dataset Manifest SHA-256:** `fa5eb9cc37651a3a28b96a322421500e8b8be3112f631e9f05cdf7b370cc345a`
- **Config SHA-256:** `3f37679f4bbbe576847bf25cbe35306b3f136d76bd7686a0911ab8bfec0be043`
- **Command:** `python -m rfq_eval run --dataset eval/dataset/v1 --system both --out eval/reports/latest`
- **Code Revision:** `dataset-v1-frozen`
- **Contamination Status:** **UNCONTAMINATED**
  - The proposed matcher (`domain/matcher.py`) has **not** been implemented.
  - No matching thresholds have been tuned on frozen evaluation cases.
  - The naive baseline algorithm is fixed and has no parameters.
- **Harness & Environment Verification:**
  - Evaluator imports zero web or database frameworks (`test_isolation.py` PASSED).
  - Manifest verification detects tampering and exits with code 2 (`test_manifest.py` PASSED).
  - Deterministic evaluation produces byte-identical outputs across successive runs.

### Procedural Waiver & Timestamps Record
- **Project-Owner Waiver:** `D33` recorded in `PRD_DECISIONS.md`. The 24-hour minimum waiting period was explicitly waived to complete the project efficiently without an unnecessary calendar delay. Review independence, data validation, and reproducibility requirements remained fully in effect.
- **Initial Pass Timestamp:** `2026-10-16T09:51:57Z` (Pass 1).
- **Second Pass Timestamp:** `2026-10-16T12:39:58Z` (Pass 2, independent blind session).
- **Reconciliation Agreement:**
  - System Outcome Agreement: **97.5%** (39 / 40 cases agreed)
  - Full Agreement (outcome + SKU + fields): **92.5%** (37 / 40 cases agreed)
- **Reconciliation Resolutions:**
  - `E-001`: Corrected typo `PIPE-004` (20mm) to `PIPE-006` (25mm Class B).
  - `E-034`: Corrected typo `PIPE-002` (15mm) to `PIPE-003` (20mm Class A).
  - `E-015`: Corrected rationale citation to `PIPE-006`.
  - `E-026`: Corrected rationale citation to `PIPE-005` and `PIPE-006`.
  - `E-039`: Reconciled to `review` per PRD Section E / Decision D9 / Category 13 (leading quantity in free-text line without delimiter requires human review).
- **Ground Truth Freeze:** All 40 cases in `eval/dataset/v1/cases.jsonl` marked with `second_pass_done: true`, `second_pass_at: 2026-10-16T12:39:58Z`, and `waiver_applied: project_owner_waiver_d33`.

### Baseline Metrics Summary (40 Frozen Cases)

| Metric | Name | Baseline Result | Proposed Matcher |
|---|---|---|---|
| **M1** | Top-candidate correct rate | 82.35% (14 / 17 expected matches) | *pending Phase 2* |
| **M2** | Proposed precision | 36.84% (14 / 38 proposed) | *pending Phase 2* |
| **M3** | Incorrect confident suggestions | **63.16%** (24 cases proposed incorrectly) | *pending Phase 2* |
| **M4** | Missed escalations | **91.30%** (21 / 23 required escalations missed) | *pending Phase 2* |
| **M5** | Over-abstention rate | 0.00% (0 / 17) | *pending Phase 2* |
| **M6** | Appropriate abstention rate | 0.00% (0 / 18 - baseline never abstains) | *pending Phase 2* |
| **M7** | Unmatched detection rate | 40.00% (2 / 5 detected solely by zero token overlap) | *pending Phase 2* |
| **M8** | Normalization accuracy | n/a (baseline has no normalization engine) | *pending Phase 2* |
| **M9** | Validation rule violations | n/a | *pending Phase 2* |

### Observations & Phase 1 Conclusion:
With corrected labels on `E-001` and `E-034`, baseline M1 increased from 70.59% to 82.35%, and M2 increased from 31.58% to 36.84%. However, the baseline's lack of abstention and spec reasoning continues to produce catastrophic safety hazards: **63.16% incorrect proposals (M3, 24 cases)** and **91.30% missed escalations (M4, 21 cases)**.

Phase 1 benchmark dataset is **FROZEN** and sealed under `MANIFEST.sha256` (`fa5eb9cc37651a3a28b96a322421500e8b8be3112f631e9f05cdf7b370cc345a`). Git tag `dataset-v1-frozen` marks the boundary before any matcher development in Phase 2.

---

## Run 3: Phase 2 Official Frozen Benchmark Evaluation (Proposed Matcher)

- **Date:** 2026-10-16
- **Phase:** Phase 2 (Deterministic Normalizer and Proposed Matching Engine)
- **Status:** **OFFICIAL BENCHMARK EVALUATION (FIRST FROZEN RUN OF PROPOSED MATCHER)**
- **Dataset Version:** `v1-frozen`
- **Dataset Manifest SHA-256:** `fa5eb9cc37651a3a28b96a322421500e8b8be3112f631e9f05cdf7b370cc345a`
- **Config SHA-256:** `9a9cd6d453fc504344a13684c0db67fce86f1625a63a430b30b3946178edbdac`
- **Command:** `python -m rfq_eval run --dataset eval/dataset/v1 --system both --out eval/reports/latest`
- **Code Revision:** `a0b234793dd73297667623234dd3e8350762a4c2`
- **Contamination Status:** **UNCONTAMINATED**
  - Matching thresholds ($T_{min}=0.30$, $T_{prop}=0.60$, $T_{marg}=0.10$) were selected on the separate 12-case development set (`eval/dev/cases.jsonl`) and documented in `eval/reports/DEV_EVAL_REPORT.md`.
  - The implementation, configuration, and unit tests were committed to Git (`a0b2347`) **prior** to executing this frozen evaluation.
  - No thresholds or rules were tuned or modified after viewing the frozen evaluation results.
- **Harness & Environment Verification:**
  - Evaluator imports zero web or database frameworks (`test_isolation.py` PASSED, 130 tests total).
  - Manifest verification confirmed dataset integrity against `fa5eb9cc...` (`test_manifest.py` PASSED).
  - Outputs in `eval/reports/latest/` (`results.jsonl`, `report.json`, `report.md`) are byte-identical and deterministic.

### Comparative Metrics Summary (40 Frozen Cases)

| Metric ID | Metric Description | Naive Baseline | Proposed Matcher | Outcome / Delta |
|---|---|---|---|---|
| **M1** | Top-candidate correct rate | 82.35% (14 / 17) | **94.12%** (16 / 17) | +11.77% |
| **M2** | Proposed precision | 36.84% (14 / 38) | **100.00%** (16 / 16) | +63.16% |
| **M3** | Incorrect confident suggestions rate | **63.16%** (24 cases) | **0.00%** (0 cases) | **-63.16% (Zero false proposals)** |
| **M4** | Missed escalations rate | **91.30%** (21 cases) | **0.00%** (0 cases) | **-91.30% (Zero missed escalations)** |
| **M5** | Over-abstention rate | 0.00% (0 / 17) | **5.88%** (1 / 17) | 1 case over-abstained (`E-010`) |
| **M6** | Appropriate abstention rate | 0.00% (0 / 18) | **100.00%** (18 / 18) | +100.00% (All review lines escalated) |
| **M7** | Unmatched detection rate | 40.00% (2 / 5) | **100.00%** (5 / 5) | +60.00% (All 5 unmatched detected) |
| **M8** | Normalization accuracy | n/a | **100.00%** (206 / 206) | Perfect field-level accuracy |
| **M9** | Validation rule violations | n/a | **0.00%** (0 / 16) | Zero rule violations |

### Key Observations & Findings:
1. **Critical Safety Elimination:** The proposed matcher completely eliminated both critical hazards of the baseline:
   - **M3:** Dropped from 24 incorrect proposals to **0**.
   - **M4:** Dropped from 21 missed review escalations to **0**.
   - Proposed precision reached **100.00%** (every proposed line is an exact match to the correct SKU).
2. **Review & Unmatched Escalation:**
   - 100% of review-required cases (18/18) were safely abstained via reason codes (`SPEC_MISSING_DISCRIMINATOR`, `UNIT_INCOMPATIBLE`, `MISSING_QUANTITY`, `MISSING_UNIT`, `SPEC_CONFLICT_IN_REQUEST`).
   - 100% of unmatched cases (5/5) were rejected (`NO_CANDIDATE` or `NO_COMPATIBLE_CANDIDATE`).
3. **Over-Abstention Audit (`E-010`):**
   - Case `E-010` (`P.T.F.E. Thread Seal Tape 12mm 10 roll`) expected `CONS-003`.
   - The dotted abbreviation `P.T.F.E.` produced similarity `0.5333`, which sits below $T_{PROPOSE} = 0.60$.
   - The system abstained with `LOW_SIMILARITY`.
   - In accordance with freeze protocol, thresholds were **not** tuned or retroactively modified; the over-abstention is reported honestly ($M_5 = 5.88\%$).
4. **Phase 2 Complete:** The deterministic normalizer and proposed matching engine meet all PRD Phase 2 acceptance criteria.

---

## Run 4: Phase 4 Full-System Audit and Reproducibility Verification

- **Date:** 2026-10-16
- **Phase:** Phase 4 (Full-System Audit, Frozen Benchmark Evaluation, and Regression Verification)
- **Status:** **OFFICIAL VERIFICATION BENCHMARK EXECUTION**
- **Dataset Version:** `v1-frozen`
- **Dataset Manifest SHA-256:** `fa5eb9cc37651a3a28b96a322421500e8b8be3112f631e9f05cdf7b370cc345a`
- **Config SHA-256:** `9a9cd6d453fc504344a13684c0db67fce86f1625a63a430b30b3946178edbdac`
- **Command:** `python -m rfq_eval run --dataset eval/dataset/v1 --system both --out eval/reports/latest`
- **Code Revision:** `73e94ddec029ca31e544d09e47e8e6f40f15b914`
- **Contamination Status:** **UNCONTAMINATED**
  - Zero modifications were made to the frozen evaluation benchmark, its manifest, catalog, or expected labels.
  - Database state from the full application, reviews, or API sessions cannot affect evaluation outputs.
  - Pure Python domain isolation verified (`test_isolation.py`).
  - No thresholds or rules were tuned or modified against the frozen set.
- **Harness & Reproducibility Verification:**
  - Double execution with `--out` diff confirmed byte-identical `results.jsonl`, `report.json`, and `report.md`.
  - Isolated dataset modification test confirmed immediate abort with exit code 2 (`DATASET_MODIFIED: SHA-256 mismatch for cases.jsonl`).
  - All 161 backend tests, 9 frontend tests (including automated `axe` checks), and clean build pass with zero warnings/errors.

### Benchmark Metrics Summary (40 Frozen Cases)

| Metric ID | Metric Description | Naive Baseline | Proposed Matcher | Outcome / Delta |
|---|---|---|---|---|
| **M1** | Top-candidate correct rate | 82.35% (14 / 17) | **94.12%** (16 / 17) | +11.77% |
| **M2** | Proposed precision | 36.84% (14 / 38) | **100.00%** (16 / 16) | +63.16% |
| **M3** | Incorrect confident suggestions rate | **63.16%** (24 cases) | **0.00%** (0 cases) | **Zero false proposals** |
| **M4** | Missed escalations rate | **91.30%** (21 cases) | **0.00%** (0 cases) | **Zero missed escalations** |
| **M5** | Over-abstention rate | 0.00% (0 / 17) | **5.88%** (1 / 17) | 1 case over-abstained (`E-010`) |
| **M6** | Appropriate abstention rate | 0.00% (0 / 18) | **100.00%** (18 / 18) | +100.00% (All review lines escalated) |
| **M7** | Unmatched detection rate | 40.00% (2 / 5) | **100.00%** (5 / 5) | +60.00% (All 5 unmatched detected) |
| **M8** | Normalization accuracy | n/a | **100.00%** (206 / 206) | Perfect field-level accuracy |
| **M9** | Validation rule violations | n/a | **0.00%** (0 / 16) | Zero rule violations |

### Safety and Error Disclosures:
- **Incorrect Confident Suggestions (M3):** 0 observed on the proposed matcher (vs 24 in baseline).
- **Missed Escalations (M4):** 0 observed on the proposed matcher (vs 21 in baseline).
- **Over-Abstention Audit (`E-010`):** Case `E-010` (`P.T.F.E. Thread Seal Tape 12mm 10 roll`) expected `CONS-003` with similarity `0.5333` (< $T_{PROPOSE} = 0.60$), abstaining with `LOW_SIMILARITY`. In accordance with freeze protocol, thresholds were **not** retroactively lowered or tuned; over-abstention is reported honestly ($M_5 = 5.88\%$).
- **Disclaimer:** All results are on 40 synthetic cases authored for this benchmark; they do not represent real-world procurement failure rates or business impact, and no comparison is made with any third-party commercial product.


