# RFQ Line-Item Normalizer

A deterministic normalization and catalog matching engine for industrial procurement RFQ (Request for Quote) line items (pipes, fittings, fasteners, valves, consumables).

> [!NOTE]
> This repository contains synthetic benchmark data and domain logic. Results on synthetic benchmark cases do not reflect real-world procurement failure rates or third-party performance.

---

## Architecture & Domain Engine

The core domain logic is implemented in pure Python with zero web or database dependencies under [`backend/domain/`](file:///home/satjeet/Desktop/isocode/backend/domain/):
- **[`domain.types`](file:///home/satjeet/Desktop/isocode/backend/domain/types.py):** Core domain dataclasses (`NormalizedLine`, `Issue`, `Candidate`, `MatchResult`, `Product`).
- **[`domain.units`](file:///home/satjeet/Desktop/isocode/backend/domain/units.py):** Canonical unit dictionary, alias mapping, physical dimensions, and exact same-dimension conversions.
- **[`domain.normalizer`](file:///home/satjeet/Desktop/isocode/backend/domain/normalizer.py):** Deterministic text normalization, Devanagari digit conversion, Unicode fraction parsing, trailing-quantity extraction (Rules 1–5), spec extraction (`size_mm`, `length_mm`, `thread`, `material`, `class`, `grade`), and internal conflict detection (`SPEC_CONFLICT_IN_REQUEST`).
- **[`domain.matcher`](file:///home/satjeet/Desktop/isocode/backend/domain/matcher.py):** Proposed deterministic matching engine with symmetric token indexing, Dice similarity scoring, spec conflict disqualification, unit compatibility checks, and near-tie abstention (`SPEC_MISSING_DISCRIMINATOR`).
- **[`domain.baseline`](file:///home/satjeet/Desktop/isocode/backend/domain/baseline.py):** Naive token-overlap baseline matcher without unit or spec reasoning.

---

## Running Automated Tests

All tests can be executed via the project Makefile:

```bash
# Run all unit, isolation, and development set regression tests (130 tests)
make test

# Validate dataset integrity, catalog schemas, and manifest consistency
make validate-data
```

To run individual test suites:
```bash
# Test unit normalization and conversions
.venv/bin/pytest backend/tests/unit/test_units.py -v

# Test deterministic normalizer and spec extraction
.venv/bin/pytest backend/tests/unit/test_normalizer.py -v

# Test matching engine, invariants, and abstention rules
.venv/bin/pytest backend/tests/unit/test_matcher.py -v

# Test development set (12 cases)
.venv/bin/pytest backend/tests/unit/test_dev_set.py -v

# Test architectural isolation (zero web/db imports)
.venv/bin/pytest backend/tests/eval/test_isolation.py -v
```

---

## Matching Configuration

The matching engine configuration is versioned and locked in [`data/matching_config.json`](file:///home/satjeet/Desktop/isocode/data/matching_config.json):
- `K`: 5 (maximum candidates returned)
- `T_MIN_CANDIDATE`: 0.30 (minimum candidate retrieval score)
- `T_PROPOSE`: 0.60 (minimum proposal similarity threshold)
- `T_MARGIN`: 0.10 (near-tie margin for missing discriminator detection)

For the empirical tuning report on the separate 12-case development set, see [`eval/reports/DEV_EVAL_REPORT.md`](file:///home/satjeet/Desktop/isocode/eval/reports/DEV_EVAL_REPORT.md). For pipeline design and invariants, see [`docs/DESIGN_NOTE.md`](file:///home/satjeet/Desktop/isocode/docs/DESIGN_NOTE.md).
