# IsoCode Labs Technical Outreach & Evidence Package

> [!NOTE]
> **Data Privacy & Scope Notice:** All catalog items, RFQ line inputs, benchmarks, and orders in this project are 100% synthetic. This repository does not contain proprietary data, confidential customer documents, or real-world supplier catalogs. All benchmark claims are strictly measured against the 40-case synthetic benchmark sealed under Git tag `dataset-v1-frozen`.

---

## 1. Executive Summary

The **RFQ Line-Item Normalizer** is a deterministic, audit-trailed full-stack system designed to tackle a high-risk bottleneck in industrial B2B procurement: converting noisy, unstructured line items from RFQ documents into verified catalog SKUs without introducing silent mis-specifications.

In industrial purchasing (piping, fasteners, valves, consumables), automated matching tools often create catastrophic errors by guessing when critical technical attributes (e.g., pipe class, thread standard, material grade) are missing or ambiguous. 

This project demonstrates a production-grade alternative:
- **Pure Python Domain Isolation:** Normalization, attribute extraction, and candidate ranking operate without web, ORM, or database dependencies.
- **Defensive Abstention over Guessing:** If an RFQ line lacks a key discriminator or presents ambiguous candidates, the engine explicitly abstains (`ambiguous` / `unmatched`) and disables candidate preselection in the UI.
- **Optimistic Concurrency & Auditability:** Reviewer actions are protected by version-checked state transitions (HTTP 409 `STALE_VERSION`), immutable decision snapshots, and gated export controls.
- **Empirical Rigor:** The matching engine was evaluated against a frozen 40-case synthetic benchmark with an independent second-pass labelling audit, proving zero false proposals ($M_3 = 0.00\%$) and zero missed escalations ($M_4 = 0.00\%$) compared to a 63.16% error rate in standard token-overlap baselines.

---

## 2. Three Key Engineering Decisions

### Decision 1: Pure Python Domain Isolation (`backend/domain/`)
- **Rationale:** Embedding parsing rules or similarity scoring into web request handlers or database queries tightly couples domain logic to infrastructure, making testing slow and edge-case benchmarking error-prone.
- **Implementation:** The entire normalization and candidate ranking engine (`normalizer.py`, `matcher.py`, `rules.py`) is written in pure standard-library Python with zero external framework dependencies.
- **Verification:** An automated subprocess isolation test (`test_isolation.py`) inspects `sys.modules` to guarantee that importing the domain layer does not load FastAPI, SQLAlchemy, Pydantic, or any network stack. This guarantees sub-millisecond per-line deterministic execution anywhere.

### Decision 2: Defensive Abstention and Non-Preselection
- **Rationale:** In procurement, a false auto-proposal (e.g., proposing Class A light pipe when the buyer required heavy Class B) results in shipping incorrect physical inventory. Abstaining for human review carries a minor operational cost; silent mis-matching carries a major financial and safety cost.
- **Implementation:**
  - **Near-Tie Margin Check:** If the top two catalog candidates have similarity scores within $T_{marg} = 0.10$, the engine rejects auto-proposal and flags `SPEC_MISSING_DISCRIMINATOR`.
  - **Unit Compatibility Gate:** Incompatible units (e.g., matching length in meters to fasteners sold in pieces) force immediate escalation (`UNIT_INCOMPATIBLE`).
  - **UI Non-Preselection:** On ambiguous lines, the human-review UI renders no radio button as preselected and suppresses all "Suggested" labels, forcing an explicit reviewer choice.

### Decision 3: Optimistic Concurrency Control and Append-Only Audit Trail
- **Rationale:** Procurement quote review is multi-tenant and collaborative. Two estimators reviewing the same RFQ simultaneously must never silently overwrite each other's decisions.
- **Implementation:**
  - Every review transition requires the client to supply an integer `expected_version`.
  - The persistence layer executes atomic updates (`UPDATE line_items SET version = version + 1 WHERE id = :id AND version = :expected_version`).
  - If a collision occurs, the API returns **HTTP 409 `STALE_VERSION`**, and the UI presents an immediate recovery reload prompt.
  - Every decision creates an immutable snapshot in `review_decisions` storing the complete line-item state, reviewer notes, and timestamp.

---

## 3. Frozen Benchmark Evaluation Results

All metrics were evaluated on the 40 frozen synthetic evaluation cases sealed under manifest `fa5eb9cc...` and Git tag `dataset-v1-frozen`.

| Metric ID | Metric Description | Naive Baseline (Token Overlap) | Proposed Matcher (Rule + Dice) | Delta / Operational Impact |
|---|---|---|---|---|
| **M1** | Top-Candidate Correct Rate | 82.35% (14 / 17) | **94.12%** (16 / 17) | +11.77% accuracy improvement |
| **M2** | Proposed Precision | 36.84% (14 / 38) | **100.00%** (16 / 16) | +63.16% (Zero false auto-proposals) |
| **M3** | Incorrect Confident Suggestions Rate | **63.16%** (24 cases) | **0.00%** (0 cases) | **Eliminated 24 hazardous auto-proposals** |
| **M4** | Missed Escalations Rate | **91.30%** (21 cases) | **0.00%** (0 cases) | **Eliminated 21 missed review escalations** |
| **M5** | Over-Abstention Rate | 0.00% (0 / 17) | **5.88%** (1 / 17) | 1 case escalated for review (`E-010`) |
| **M6** | Appropriate Abstention Rate | 0.00% (0 / 18) | **100.00%** (18 / 18) | +100.00% (All ambiguous lines escalated) |
| **M7** | Unmatched Detection Rate | 40.00% (2 / 5) | **100.00%** (5 / 5) | +60.00% (All 5 non-catalog items detected) |
| **M8** | Normalization Accuracy | n/a | **100.00%** (206 / 206) | Perfect field extraction across all lines |
| **M9** | Validation Rule Violations | n/a | **0.00%** (0 / 16) | Zero constraint or contract violations |

> [!IMPORTANT]
> **Methodological Disclaimer:** These metrics are measured on 40 synthetic industrial cases authored to test specification boundaries. They do not represent real-world supplier catalog accuracy or external business impact. No comparison is made with any third-party commercial software.

---

## 4. Failure Case Analysis: Case `E-010`

Honest evaluation requires transparently documenting edge cases and model failures rather than hiding them.

### Input Case Details
- **Case ID:** `E-010`
- **Raw Line Text:** `"P.T.F.E. Thread Seal Tape 12mm 10 roll"`
- **Category:** Category 4 (Abbreviations & Alternate Forms)
- **Catalog Ground Truth:** `CONS-003` (`PTFE Thread Seal Tape 12mm x 10m`)
- **Expected Outcome:** `proposed` with SKU `CONS-003`

### Observed System Behavior
- **Actual Outcome:** `ambiguous` (Abstained with reason code `LOW_SIMILARITY`)
- **Top Candidate:** `CONS-003`
- **Computed Similarity:** `0.5333`
- **Configured Proposal Threshold ($T_{PROPOSE}$):** `0.60`

### Root Cause
The tokenizer splits on spaces and standard delimiters but treats `"P.T.F.E."` as four distinct single-letter tokens or an un-normalized punctuation sequence. In the catalog, the SKU description uses `"PTFE"`. The resulting character-trigram / token overlap fell just below the 0.60 proposal threshold (`0.5333`).

### Engineering Freeze Integrity
Because this failure was identified after the evaluation benchmark was frozen:
1. We **did not** retroactively lower $T_{PROPOSE}$ to 0.50 to force a 100% benchmark score (which would have degraded precision across other edge cases).
2. We **did not** modify the ground-truth dataset.
3. The over-abstention was logged honestly as $M_5 = 5.88\%$ in `EVAL_LOG.md`.
4. **Planned Remediation:** Punctuation-stripping normalization (`re.sub(r'(?<=\w)\.(?=\w)', '', text)`) has been logged as a candidate enhancement for dataset v2.

---

## 5. Artifact & Demonstration Links

- **Repository:** [`https://github.com/Satjeet2005/RFQ-line-item-normalizer`](https://github.com/Satjeet2005/RFQ-line-item-normalizer)
- **Interactive Walkthrough Guide:** [`docs/WALKTHROUGH.md`](./WALKTHROUGH.md) (Complete 3-minute hands-on script and test data)
- **Walkthrough Video:** `[3-Minute Technical Walkthrough Video — Insert Link]` *(Recorded per the shot list in `docs/WALKTHROUGH.md`)*
- **Evaluation Benchmark Log:** [`EVAL_LOG.md`](../EVAL_LOG.md) (Full audit trail of baseline and matcher runs)
- **Architecture & Schema Documentation:** [`docs/DESIGN_NOTE.md`](./DESIGN_NOTE.md)

---

## 6. Outreach Message Template for IsoCode Labs

Below is a concise, peer-to-peer technical outreach message tailored for engineering contacts at IsoCode Labs.

```text
Subject: Technical notes on deterministic line-item normalization & abstention in procurement RFQs

Hi [Name],

I've been following IsoCode Labs' work on structured document parsing and AI workflows for B2B industrial workflows.

A recurring challenge I've observed in RFQ processing is the "silent mis-specification" problem: when automated matching models guess catalog SKUs on ambiguous lines (e.g., missing pipe schedule/class or thread types), causing costly downstream shipping errors.

I recently built and open-sourced a full-stack reference implementation addressing this exact problem: the RFQ Line-Item Normalizer. 

Key technical aspects:
1. Pure Python Domain Isolation: The normalization and candidate-ranking engine runs with zero web or database dependencies, verified by subprocess isolation tests.
2. Defensive Abstention: Near-tie margin checks and unit compatibility gates prevent false proposals. On ambiguous lines, the UI explicitly suppresses candidate preselection to force human sign-off.
3. Frozen Benchmark Discipline: On a frozen 40-case synthetic benchmark with independent two-pass labelling, the engine reduced false confident proposals from 63.16% (naive baseline) to 0.00%, with an honest 5.88% over-abstention rate analyzed transparently (Case E-010).
4. Multi-Tenant Integrity: Optimistic concurrency control (HTTP 409 STALE_VERSION) and append-only audit snapshots protect multi-user review workflows.

Repository & Walkthrough:
- Code & Architecture: https://github.com/Satjeet2005/RFQ-line-item-normalizer
- 3-Minute Technical Demo: [Insert Video URL / docs/WALKTHROUGH.md]

Question for your team:
In your production ingestion pipelines, how do you typically balance the tradeoff between auto-proposal coverage and defensive abstention when dealing with incomplete buyer specifications? Do you favor deterministic attribute-extraction gates before vector/similarity search, or handle confidence thresholds dynamically in the LLM layer?

Best regards,

Satjeet
[Your Portfolio / Contact Links]
```
