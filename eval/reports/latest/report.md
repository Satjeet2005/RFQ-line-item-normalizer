# RFQ Matcher Evaluation Benchmark Report

> [!IMPORTANT]
> Results are on 40 synthetic cases authored by the project owner; they are not real-world accuracy and do not show business impact.

> [!NOTE]
> The baseline is a deliberately naive highest-token-overlap heuristic with zero unit logic, spec extraction, or abstention capability. Its failure rates on this synthetic benchmark highlight the risks of unguided lexical matching on near-duplicate products; they do not represent real-world procurement failure rates or third-party performance.

## 1. Traceability and Metadata

- **Dataset Version:** `v1-frozen`
- **Dataset Manifest SHA-256:** `fa5eb9cc37651a3a28b96a322421500e8b8be3112f631e9f05cdf7b370cc345a`
- **Config SHA-256:** `3f37679f4bbbe576847bf25cbe35306b3f136d76bd7686a0911ab8bfec0be043`
- **Code Revision:** `dataset-v1-frozen`
- **Command:** `python -m rfq_eval run --dataset eval/dataset/v1 --system both --out eval/reports/latest`
- **Raw Results:** `results.jsonl`

## 2. Critical Safety Failures (Reported First)

### A. Incorrect Confident Suggestions (M3)

**Baseline observed 24 incorrect confident suggestion(s):**

| Case ID | Input | Expected Outcome | Expected SKU | Baseline Outcome | Baseline SKU |
|---|---|---|---|---|---|
| `E-007` | `MILD STEEL HEX BOLT M16 X 60 MM GR 8.8 50 PCS` | `match` | `BOLT-018` | `proposed` | `BOLT-013` |
| `E-008` | `SS 304 Bolt M10*40 25 nos` | `match` | `BOLT-023` | `proposed` | `BOLT-001` |
| `E-009` | `GI Equal Tee 50 mm Class B 15 no` | `match` | `FITT-009` | `proposed` | `FITT-006` |
| `E-015` | `GI Pipe 25mm Class B 50 nos` | `review` | `null` | `proposed` | `PIPE-006` |
| `E-016` | `MS Hex Bolt M10x40 Grade 4.6 15 kg` | `review` | `null` | `proposed` | `BOLT-005` |
| `E-017` | `PTFE Thread Seal Tape 12mm 5 mtr` | `review` | `null` | `proposed` | `CONS-003` |
| `E-018` | `GI Pipe 40mm Class A mtr` | `review` | `null` | `proposed` | `PIPE-009` |
| `E-019` | `Brass Ball Valve Screwed 20mm nos` | `review` | `null` | `proposed` | `VALV-002` |
| `E-020` | `GI Pipe 32mm Class B 50` | `review` | `null` | `proposed` | `PIPE-008` |
| `E-021` | `MS Hex Bolt M12x75 Grade 8.8 100` | `review` | `null` | `proposed` | `BOLT-017` |
| `E-022` | `PVC Pipe 50mm Class A 30 bundles` | `review` | `null` | `proposed` | `PIPE-025` |
| `E-023` | `GI Pipe 25mm Class A Class B 10 mtr` | `review` | `null` | `proposed` | `PIPE-005` |
| `E-024` | `GI Pipe 70mm Class B 10 mtr` | `unmatched` | `null` | `proposed` | `PIPE-002` |
| `E-025` | `Brass Hex Bolt M12x50 50 nos` | `unmatched` | `null` | `proposed` | `BOLT-007` |
| `E-026` | `GI Pipe 25mm 20 mtr` | `review` | `null` | `proposed` | `PIPE-005` |
| `E-027` | `MS Hex Bolt M10x40 100 nos` | `review` | `null` | `proposed` | `BOLT-005` |
| `E-028` | `PVC Pipe 25mm 60 mtr` | `review` | `null` | `proposed` | `PIPE-019` |
| `E-029` | `Brass Valve 25mm 5 nos` | `review` | `null` | `proposed` | `VALV-003` |
| `E-030` | `GI Fitting 25mm 10 nos` | `review` | `null` | `proposed` | `FITT-003` |
| `E-033` | `Copper Refrigeration Tubing 1/2 inch 15 mtr` | `unmatched` | `null` | `proposed` | `CONS-006` |
| `E-037` | `kohni 25mm 10 nos` | `review` | `null` | `proposed` | `FITT-003` |
| `E-038` | `MS Hex Bolt M12 x 50` | `review` | `null` | `proposed` | `BOLT-001` |
| `E-039` | `50 mtr GI Pipe 25mm Class B` | `review` | `null` | `proposed` | `PIPE-006` |
| `E-040` | `MS Hex Bolt M12x50 Grade 4.6 12.5 nos` | `review` | `null` | `proposed` | `BOLT-007` |

### B. Missed Escalations (M4)

**Baseline observed 21 missed escalation(s) (proposing when review or unmatched was required):**

| Case ID | Input | Expected Outcome | Baseline Outcome | Baseline SKU |
|---|---|---|---|---|
| `E-015` | `GI Pipe 25mm Class B 50 nos` | `review` | `proposed` | `PIPE-006` |
| `E-016` | `MS Hex Bolt M10x40 Grade 4.6 15 kg` | `review` | `proposed` | `BOLT-005` |
| `E-017` | `PTFE Thread Seal Tape 12mm 5 mtr` | `review` | `proposed` | `CONS-003` |
| `E-018` | `GI Pipe 40mm Class A mtr` | `review` | `proposed` | `PIPE-009` |
| `E-019` | `Brass Ball Valve Screwed 20mm nos` | `review` | `proposed` | `VALV-002` |
| `E-020` | `GI Pipe 32mm Class B 50` | `review` | `proposed` | `PIPE-008` |
| `E-021` | `MS Hex Bolt M12x75 Grade 8.8 100` | `review` | `proposed` | `BOLT-017` |
| `E-022` | `PVC Pipe 50mm Class A 30 bundles` | `review` | `proposed` | `PIPE-025` |
| `E-023` | `GI Pipe 25mm Class A Class B 10 mtr` | `review` | `proposed` | `PIPE-005` |
| `E-024` | `GI Pipe 70mm Class B 10 mtr` | `unmatched` | `proposed` | `PIPE-002` |
| `E-025` | `Brass Hex Bolt M12x50 50 nos` | `unmatched` | `proposed` | `BOLT-007` |
| `E-026` | `GI Pipe 25mm 20 mtr` | `review` | `proposed` | `PIPE-005` |
| `E-027` | `MS Hex Bolt M10x40 100 nos` | `review` | `proposed` | `BOLT-005` |
| `E-028` | `PVC Pipe 25mm 60 mtr` | `review` | `proposed` | `PIPE-019` |
| `E-029` | `Brass Valve 25mm 5 nos` | `review` | `proposed` | `VALV-003` |
| `E-030` | `GI Fitting 25mm 10 nos` | `review` | `proposed` | `FITT-003` |
| `E-033` | `Copper Refrigeration Tubing 1/2 inch 15 mtr` | `unmatched` | `proposed` | `CONS-006` |
| `E-037` | `kohni 25mm 10 nos` | `review` | `proposed` | `FITT-003` |
| `E-038` | `MS Hex Bolt M12 x 50` | `review` | `proposed` | `BOLT-001` |
| `E-039` | `50 mtr GI Pipe 25mm Class B` | `review` | `proposed` | `PIPE-006` |
| `E-040` | `MS Hex Bolt M12x50 Grade 4.6 12.5 nos` | `review` | `proposed` | `BOLT-007` |

## 3. Benchmark Metrics Summary

| Metric ID | Metric Description | Naive Baseline | Proposed Matcher |
|---|---|---|---|
| **M1** | Top-candidate correct rate | 82.35% (14/17) | *pending Phase 2* |
| **M2** | Proposed precision | 36.84% (14/38) | *pending Phase 2* |
| **M3** | Incorrect confident suggestions rate | 63.16% | *pending Phase 2* |
| **M4** | Missed escalations rate | 91.30% | *pending Phase 2* |
| **M5** | Over-abstention rate | 0.00% (0/17) | *pending Phase 2* |
| **M6** | Appropriate abstention rate | 0.00% (0/18) | *pending Phase 2* |
| **M7** | Unmatched detection rate | 40.00% (2/5) | *pending Phase 2* |
| **M8** | Normalization accuracy | n/a (no normalizer in baseline) | *pending Phase 2* |
| **M9** | Validation rule violations | n/a | *pending Phase 2* |

## 4. Proposed Matcher Status

> [!NOTE]
> Proposed matcher (domain/matcher.py) not implemented in Phase 1 per PRD freeze protocol. Implementation scheduled for Phase 2 after threshold tuning on dev set.

