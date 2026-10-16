# RFQ Line-Item Normalizer

A deterministic normalization, catalog matching, and human-in-the-loop review application for industrial procurement RFQ (Request for Quote) line items (pipes, fittings, fasteners, valves, consumables).

> [!NOTE]
> **Context & Disclaimer:** This project was inspired by a publicly described workflow in industrial procurement. All benchmark datasets, catalogs, and test fixtures in this repository are **100% synthetic**. Results on synthetic benchmark cases do not reflect real-world procurement failure rates, business impact, or third-party performance.

---

## Architecture & Data Flow

```mermaid
flowchart TD
    UI["Next.js Web UI\n(App Router :3000)"]
    API["FastAPI REST API\n(:8000)"]
    DB[("PostgreSQL 16\nPersistence")]
    NORM["Deterministic Normalizer\n(Pure Python domain/)"]
    MATCH["Matching Engine\n(Dice + Invariants)"]
    AUDIT["Audit Trail\n(Append-Only Decisions)"]
    EXPORT["Export Engine\n(RFC 4180 CSV / JSON)"]

    UI -->|HTTP / JSON| API
    API -->|Raw Text / CSV| NORM
    NORM -->|Tokens + Spec + Issues| MATCH
    MATCH -->|System Outcome & Candidates| API
    API -->|Persist RFQ & Lines| DB
    UI -->|Review Decision + expected_version| API
    API -->|Atomic OCC Check| DB
    API -->|Record Decision Snapshot| AUDIT
    AUDIT -->|Save Snapshot| DB
    UI -->|Gated Export Request| API
    API -->|Neutralized Cells & Filtered Lines| EXPORT
```

### Module Responsibilities
- **[`domain/`](file:///home/satjeet/Desktop/isocode/backend/domain/)**: Pure Python domain engine with zero database or web framework dependencies. Performs Unicode NFKC normalization, Devanagari digit conversion, Unicode fraction parsing, trailing-quantity extraction (Rules 1–5), spec attribute extraction, physical dimension conversion, and invariant-checked deterministic candidate scoring.
- **[`backend/app/`](file:///home/satjeet/Desktop/isocode/backend/app/)**: FastAPI application with structured JSON logging (`request_id`), Pydantic validation, optimistic concurrency control via `expected_version`, and Alembic-migrated PostgreSQL persistence.
- **[`frontend/`](file:///home/satjeet/Desktop/isocode/frontend/)**: Next.js 14 App Router application with accessible non-color-alone badges, keyboard-navigable review workflows, instant reload alerts on 409 conflicts, and responsive tables collapsing to cards on small screens.

---

## Setup & Delivery

### Prerequisites
- Docker Engine ≥ 24 with Compose v2
- GNU Make
- Git
- ~4 GB free RAM

*Reference environment:* 8-core CPU, 16 GB RAM (Linux x86_64 / macOS).
- **Cold start (first-time container build):** ≈ 45 seconds (excluding initial Docker base image download).
- **Warm start:** ≈ 5 seconds.

### Quick Start
To launch the full application from a clean checkout:

```bash
make up
```

This single command automatically:
1. Copies `.env.example` to `.env` if not already present.
2. Builds and starts the PostgreSQL database, FastAPI service, and Next.js frontend in detached mode.
3. Applies Alembic migration `0001_initial` and idempotently seeds the 100-product catalog.
4. Exposes the Web UI at [`http://localhost:3000`](http://localhost:3000) and the API at [`http://localhost:8000`](http://localhost:8000).

Verify the health check endpoint:
```bash
curl -s http://localhost:8000/api/v1/health
# {"status":"ok"}
```

---

## Available Commands

| Command | Description |
|---|---|
| `make up` | Create `.env` from template and launch all Docker containers |
| `make down` | Stop and remove running Docker containers |
| `make reset-db` | Stop containers and wipe database volumes for a clean state |
| `make test` | Run all 159 backend pytest tests and 9 frontend vitest tests |
| `make lint` | Run backend Ruff checks and frontend ESLint |
| `make eval` | Run the frozen-set evaluation harness with determinism check |
| `make e2e` | Run the end-to-end golden flow integration test suite |
| `make validate-data` | Validate dataset manifest hashes, catalog schemas, and unit consistency |
| `make all` | Run data validation, evaluation, tests, and linting sequentially |

---

## 3-Minute Walkthrough

For a guided step-by-step tour using only synthetic industrial benchmark items, see [`docs/WALKTHROUGH.md`](file:///home/satjeet/Desktop/isocode/docs/WALKTHROUGH.md):
1. **Import:** Ingest a sample 4-line RFQ with mixed formats and missing discriminators.
2. **Review:** Inspect an ambiguous line item and verify that **no candidate is preselected** and **no "Suggested" label is shown**.
3. **Decide:** Select a candidate explicitly with notes and approve.
4. **Reject / Confirm No-Match:** Handle unmatchable or unwanted items.
5. **Export:** Verify incomplete export gating (409 `RFQ_INCOMPLETE`) and download formula-neutralized RFC 4180 CSV with `X-Items-Excluded`.

---

## Evaluation Benchmark & Determinism

The evaluation benchmark is versioned and frozen under git tag `dataset-v1-frozen` (commit `6a93c97100fd74c62ed3fddb17f969530ae8c098`):
- **40 Frozen Evaluation Cases:** Located in [`eval/dataset/v1/cases.jsonl`](file:///home/satjeet/Desktop/isocode/eval/dataset/v1/cases.jsonl), guarded by [`eval/dataset/v1/MANIFEST.sha256`](file:///home/satjeet/Desktop/isocode/eval/dataset/v1/MANIFEST.sha256).
- **12 Development Cases:** Located in [`eval/dev/cases.jsonl`](file:///home/satjeet/Desktop/isocode/eval/dev/cases.jsonl) for threshold tuning, entirely independent from the frozen set.
- **Tamper Detection:** Modifying any frozen dataset file causes `make eval` to immediately abort with exit code 2 (`DATASET_MODIFIED`).
- **Byte-Identical Outputs:** Running `make eval` repeatedly produces byte-identical `results.jsonl`, `report.json`, and `report.md` (runtime performance is recorded separately in `timing.json`).

---

## Proof-of-Work and Impact Claims

Per PRD Section U:

| # | Claim | Can this standalone project support it? | Substantiating artifacts |
|---|---|---|---|
| 1 | Engineering quality | **Yes** | Repository structure, 168 automated tests, CI workflows, architecture diagrams, clean-machine setup instructions, 3-minute walkthrough |
| 2 | Improvement over the documented naive baseline on the frozen synthetic dataset | **Yes, narrowly** ("on 40 synthetic cases") | `report.json` / `report.md`, `results.jsonl`, dataset manifest hash + `dataset-v1-frozen` git tag, code revision, `EVAL_LOG.md`, listed failure cases |
| 3 | Plausible relevance to ClearQuote's publicly described workflow | **Hypothesis**: only company feedback can validate | Problem formulation and domain modeling inspired by publicly described workflows; no claim in artifacts beyond this conceptual inspiration |
| 4 | Verified impact on IsoCode's engineering or business outcomes | **No**: requires their data, baselines and production access | None; this repository explicitly disclaims any such verified business impact |

---

## Project Limitations & Non-Goals

1. **Synthetic Data Only:** The 40-case evaluation set is synthetic and does not represent real-world supplier catalog coverage or real-world error frequencies.
2. **Never Invent a Price:** The catalog contains **zero price fields**. The system strictly addresses item normalization and matching. It does not calculate quotes, validate pricing margins, or process payments.
3. **Excluded Capabilities:** By design, this MVP intentionally excludes:
   - OCR and unstructured PDF extraction.
   - WhatsApp, email, or external ERP integrations.
   - Multi-tenant organizations and user authentication.
4. **Time-Box Outcome:** Total engineering effort for Phases 1–3 was approximately **28 hours**, well within the approved 35-hour budget. No scope cut from the primary cut list was required.

---

## Troubleshooting

- **Port 3000, 8000, or 5432 in use:** Check for existing services using `lsof -i :<port>` or modify ports in `.env`.
- **Database state reset:** If schema changes or dirty test data accumulate, run `make reset-db` followed by `make up`.
- **Exit Code 2 on Evaluation (`DATASET_MODIFIED`):** A frozen benchmark file in `eval/dataset/v1/` has been modified. Revert changes to match `eval/dataset/v1/MANIFEST.sha256`.
- **Missing `GIT_SHA`:** If running outside of git, export `GIT_SHA=$(git rev-parse HEAD)` manually before invoking evaluation commands.
