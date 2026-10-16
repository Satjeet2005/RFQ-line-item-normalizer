# Technical Design Note: Normalizer and Deterministic Matching Engine

## 1. Architectural Overview

The RFQ Line-Item Normalizer domain engine is designed as a pure, deterministic, framework-agnostic pipeline in `backend/domain/`. It has zero dependencies on FastAPI, SQLAlchemy, external networks, or large language models.

```
Raw Input Line
     │
     ▼
[ 1. Ingestion Split ] ────► split_raw_line (Free-text trailing rules 1–5 or delimited)
     │
     ▼
[ 2. Deterministic Normalizer ] ────► normalize_line
     ├─ Unicode NFKC, Devanagari digits, Unicode fractions
     ├─ Quantity validation & discrete count integer checks
     ├─ Canonical unit mapping & physical dimension lookup
     ├─ Spec extraction (size_mm, length_mm, thread, material, class, grade)
     ├─ Internal conflict detection (SPEC_CONFLICT_IN_REQUEST)
     └─ Transliteration aliases & stop-word removal
     │
     ▼
[ NormalizedLine ]
  (raw_input, description_normalized, tokens, spec, quantity, unit, unit_dimension, issues)
     │
     ▼
[ 3. Proposed Matcher ] ────► ProposedMatcher.match
     ├─ Symmetric token derivation for catalog products & aliases
     ├─ Lexical Dice similarity scoring: 2·|R∩C| / (|R|+|C|), rounded to 4 dp
     ├─ Candidate ranking: (-similarity, sku) total ordering
     ├─ Spec conflict verification: candidate lacking/contradicting spec -> disqualified
     ├─ Unit dimension compatibility & count unit non-interchangeability check
     ├─ Plausible set P & near-tie group G (|s1 - sc| < T_MARGIN)
     └─ Hierarchical Decision Procedure
     │
     ▼
[ MatchResult ]
  (system_outcome: "proposed" | "ambiguous" | "unmatched", candidates: List[Candidate], reason_codes: List[str])
```

---

## 2. Core Invariants & Safety Guarantees

1. **Safety Precedence over Lexical Overlap:**
   A high lexical token overlap score alone can never justify a `proposed` match. If candidate #1 has a spec conflict (e.g. Grade 10.9 vs requested Grade 4.6), it is marked `disqualified` and can never be proposed.

2. **Conservative Near-Tie Abstention (`SPEC_MISSING_DISCRIMINATOR`):**
   When multiple compatible products fall within $T_{MARGIN} = 0.10$ of the top score and differ on an attribute the buyer omitted (e.g., fastener grade, pipe class), the engine abstains with `ambiguous` and reason code `SPEC_MISSING_DISCRIMINATOR`.

3. **Strict Physical Unit Compatibility:**
   - Same dimension conversions (e.g. `ft` $\to$ `mtr`, `g` $\to$ `kg`) are permitted using exact Decimal factors ($1\text{ ft} = 0.3048\text{ mtr}$).
   - Discrete count units (`nos`, `set`, `pair`, `box`, `roll`, `bag`) are **never** converted or treated as interchangeable.
   - Dimension mismatches (e.g. `kg` requested for a product stocked in `mtr`) force review with reason code `UNIT_INCOMPATIBLE`.

4. **Raw Input Preservation:**
   `description_raw` is preserved byte-for-byte (trimmed ends only) on `NormalizedLine`. No input data is discarded or silently mutated.

5. **Pure Determinism:**
   All operations run with `PYTHONHASHSEED=0`, iterating over sorted collections, with float similarity scores rounded to 4 decimal places before tie-breaking by SKU ascending. Repeated executions on identical inputs produce byte-identical results.

6. **Architectural Isolation:**
   Domain modules (`backend/domain/`) contain no imports of database libraries, ORMs, HTTP frameworks, or async runtimes.

---

## 3. Threshold Configuration (`data/matching_config.json`)

The matching parameters were tuned on the separate 12-case development set (`eval/dev/cases.jsonl`):
- `K = 5`: Up to 5 candidate products returned.
- `T_MIN_CANDIDATE = 0.30`: Rejects spurious lexical overlap while preserving partial descriptions.
- `T_PROPOSE = 0.60`: Permits valid matches (including transliterated items down to 0.6250) while abstaining on low-similarity matches with `LOW_SIMILARITY`.
- `T_MARGIN = 0.10`: Detects near-duplicate variant ties differing by $< 0.10$.
