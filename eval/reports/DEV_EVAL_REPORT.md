# Development Set Evaluation & Threshold Selection Report

## 1. Overview & Protocol

Per `PRD.md` Section J, `PRD_DECISIONS.md` Decision `D1`, and Phase 2 requirements, matching thresholds must be evaluated and selected exclusively using the separate 12-case development set (`eval/dev/cases.jsonl`) and independent unit-test fixtures.

**Contamination Prevention Protocol:**
- Zero inspection of frozen evaluation set labels (`eval/dataset/v1/cases.jsonl`).
- Zero evaluation runs of the proposed matcher against the frozen evaluation set before locking configuration.
- The matching implementation and configuration are committed to Git prior to running the official benchmark evaluation.

---

## 2. Threshold Search Space & Methodology

The matching engine relies on three key parameters:
1. `T_MIN_CANDIDATE`: Minimum Dice similarity required for a catalog product to be retrieved into the candidate pool (up to K=5).
2. `T_PROPOSE`: Minimum similarity of the top candidate required for the system outcome to be `proposed`.
3. `T_MARGIN`: Maximum similarity difference between the top candidate and competing candidates in the plausible set $P$ to form the near-tie group $G$.

A grid search was conducted over 125 candidate parameter combinations:
- `T_MIN_CANDIDATE` $\in \{0.20, 0.25, 0.30, 0.35, 0.40\}$
- `T_PROPOSE` $\in \{0.50, 0.55, 0.60, 0.65, 0.70\}$
- `T_MARGIN` $\in \{0.05, 0.08, 0.10, 0.12, 0.15\}$

### Grid Search Results Summary

| $T_{min}$ | $T_{prop}$ | $T_{marg}$ | Dev Passes (out of 12) | Observations |
|---|---|---|---|---|
| 0.20 | 0.55 | 0.10 | 11 / 12 | Spurious candidates retrieved for `D-011` (goggles) at 0.25 similarity; triggers `ambiguous` instead of `unmatched`. |
| 0.25 | 0.60 | 0.10 | 11 / 12 | Same spurious retrieval on `D-011` with leather gloves / consumables sharing "industrial". |
| **0.30** | **0.60** | **0.10** | **12 / 12 (100%)** | **Optimal balance:** Rejects noise, admits all valid matches, catches near-tie grade discriminator. |
| 0.30 | 0.65 | 0.10 | 11 / 12 | Over-abstains on `D-012` (`loha bolt M12x75 Gr 4.6`, similarity 0.6250) due to `LOW_SIMILARITY`. |
| 0.35 | 0.60 | 0.10 | 12 / 12 | Passes on 12 dev cases, but higher $T_{min}$ risks dropping lower-similarity candidate aliases. |
| 0.30 | 0.60 | 0.03 | 11 / 12 | Fails `D-008` ($|s_1 - s_2| = 0.0417 > 0.03$); fails to trigger `SPEC_MISSING_DISCRIMINATOR`, causing an incorrect confident proposal. |

---

## 3. Chosen Locked Configuration (`data/matching_config.json`)

```json
{
  "version": "1.0.0-final",
  "K": 5,
  "T_MIN_CANDIDATE": 0.30,
  "T_PROPOSE": 0.60,
  "T_MARGIN": 0.10,
  "rationale": "Empirically verified on the 12-case development set (eval/dev/cases.jsonl). T_MIN_CANDIDATE=0.30 rejects spurious non-catalog matches (e.g. D-011 goggles at 0.25 similarity). T_PROPOSE=0.60 safely admits valid matches down to 0.6250 (e.g. D-012 transliterated bolt) while blocking weak matches. T_MARGIN=0.10 identifies near-duplicate ties (e.g. D-008 delta=0.0417) to enforce SPEC_MISSING_DISCRIMINATOR escalation."
}
```

### Empirical Rationale & Supporting Cases:

1. **`T_MIN_CANDIDATE = 0.30`:**
   - Case `D-011` (`Industrial Safety Goggles Clear 5 nos`): Top spurious catalog items have lexical overlap around 0.25. Setting $T_{min} = 0.30$ ensures 0 candidates are returned, yielding `unmatched` with code `NO_CANDIDATE`.
   - Leaves sufficient recall for partial descriptions while discarding irrelevant noise.

2. **`T_PROPOSE = 0.60`:**
   - Case `D-012` (`loha bolt M12x75 Gr 4.6 40 nos`): After transliteration, matches `BOLT-008` with similarity `0.6250`.
   - Threshold 0.60 correctly proposes `BOLT-008`. Setting $T_{prop} \ge 0.65$ would cause over-abstention ($M_5$ error).

3. **`T_MARGIN = 0.10`:**
   - Case `D-008` (`MS Hex Bolt M16x60 50 nos`): Request omits grade. Candidates `BOLT-018` (Grade 8.8, sim=0.6667) and `BOLT-009` (Grade 4.6, sim=0.6250) differ by $0.0417$.
   - Because $0.0417 < 0.10$, both candidates enter the near-tie group $G$, triggering `SPEC_MISSING_DISCRIMINATOR` and forcing review. A margin $< 0.04$ would have mistakenly proposed `BOLT-018`.

---

## 4. Development Set Case-by-Case Breakdown (100% Pass)

| Case ID | Input | Category | Expected Outcome | System Outcome | Top SKU | Reason Codes | Status |
|---|---|---|---|---|---|---|---|
| `D-001` | `GI Pipe 80mm Class A 24 mtr` | exact_clean_match | match (`PIPE-013`) | `proposed` | `PIPE-013` | none | **PASS** |
| `D-002` | `ms hex bolt m8x30 grade 4.6 200 nos` | harmless_variation | match (`BOLT-003`) | `proposed` | `BOLT-003` | none | **PASS** |
| `D-003` | `GI Pipe 100mm Class B 300 ft` | unit_alias_or_convertible | match (`PIPE-016`) | `proposed` | `PIPE-016` | none | **PASS** |
| `D-004` | `MS Plain Washer M12 500 pcs` | unit_alias_or_convertible | match (`BOLT-035`) | `proposed` | `BOLT-035` | none | **PASS** |
| `D-005` | `PVC Pipe 20mm Class B 100 kg` | unit_incompatible | review | `ambiguous` | `PIPE-018` | `UNIT_INCOMPATIBLE` | **PASS** |
| `D-006` | `MS Hex Nut M10 nos` | missing_quantity | review | `ambiguous` | `BOLT-029` | `MISSING_QUANTITY` | **PASS** |
| `D-007` | `GI Socket Coupling 20mm Class B 50` | missing_or_unknown_unit | review | `ambiguous` | `FITT-011` | `MISSING_UNIT` | **PASS** |
| `D-008` | `MS Hex Bolt M16x60 50 nos` | missing_discriminator | review | `ambiguous` | `BOLT-018` | `SPEC_MISSING_DISCRIMINATOR` | **PASS** |
| `D-009` | `GI Pipe 25mm MS 10 mtr` | conflicting_spec_internal | review | `ambiguous` | `PIPE-005` | `SPEC_CONFLICT_IN_REQUEST` | **PASS** |
| `D-010` | `Stainless Steel Hex Bolt M24x100 20 nos` | catalog_near_miss | unmatched | `unmatched` | `BOLT-021` | `NO_COMPATIBLE_CANDIDATE` | **PASS** |
| `D-011` | `Industrial Safety Goggles Clear 5 nos` | unknown_catalog_item | unmatched | `unmatched` | none | `NO_CANDIDATE` | **PASS** |
| `D-012` | `loha bolt M12x75 Gr 4.6 40 nos` | mixed_transliterated | match (`BOLT-008`) | `proposed` | `BOLT-008` | none | **PASS** |

---

## 5. Limitations & Caveats

1. **Small sample size ($N=12$):** While the 12 cases test critical boundary conditions (unit conversion, missing dimensions, missing discriminators, internal conflicts, transliteration), 12 cases do not provide exhaustive statistical coverage of all industrial procurement variations.
2. **Deterministic bounds:** The chosen thresholds are simple, round, and defensible rather than overfit to fractions of a percent on 12 points.
