# 3-Minute Technical Walkthrough: RFQ Line-Item Normalizer

This document provides a guided walkthrough of the RFQ Line-Item Normalizer using only synthetic industrial benchmark items.

> [!NOTE]
> **Data Privacy Notice:** All products, SKUs, customer lines, and orders used in this walkthrough are 100% synthetic. No real supplier catalog, confidential pricing, or proprietary customer data is used.

---

## Part 1: Hands-On Operator Guide

### 1. Clean Startup (0:00 – 0:30)

1. Ensure Docker Engine is running on your machine.
2. From the project root, execute:
   ```bash
   make up
   ```
   *Under the hood:* This command copies `.env.example` to `.env` if missing, starts PostgreSQL 16, runs Alembic migration `0001_initial`, seeds the 100-item synthetic catalog idempotently, and launches FastAPI on `:8000` and Next.js on `:3000`.
3. Open your browser to [`http://localhost:3000`](http://localhost:3000). The dashboard displays the global synthetic demo banner, RFQ summary statistics, and recent orders.

---

### 2. Ingesting Unstructured RFQ Items (0:30 – 1:00)

1. Navigate to **New RFQ** (`/rfqs/new`).
2. Click **"Load Sample RFQ"** in the Paste tab. This loads 4 representative industrial procurement lines:
   ```text
   GI Pipe 25mm Class B 100 mtr
   MS Hex Bolt M12x50 500 nos
   GI Pipe 25mm 50 mtr
   Unknown Custom Valve Widget 5 pcs
   ```
3. Enter the RFQ name: `Plant Maintenance Order #401`.
4. Click **"Import & Normalize RFQ"**.
5. The normalizer strips boilerplate, parses quantities/units, extracts technical specifications (`size_mm`, `class`, `grade`, `thread`), computes Dice candidate similarities, and redirects to the RFQ details page (`/rfqs/<id>`) in under 50 ms.

---

### 3. Inspecting Non-Preselection on Ambiguous Lines (1:00 – 1:45)

1. On the RFQ summary table, observe the non-color-alone status badges:
   - Line 1 (`GI Pipe 25mm Class B`): **Proposed** (purple spark icon + pill).
   - Line 2 (`MS Hex Bolt M12x50`): **Proposed** (purple spark icon + pill).
   - Line 3 (`GI Pipe 25mm 50 mtr`): **Ambiguous** (amber alert triangle + pill).
   - Line 4 (`Unknown Custom Valve Widget`): **Unmatched** (gray question circle + pill).
2. Click **Review** on Line 3 (`GI Pipe 25mm 50 mtr`).
3. **Verify Safety Invariant:**
   - The purchaser omitted whether they need `Class A` (light) or `Class B` (medium) pipe.
   - The engine detected a near-tie and abstained with `SPEC_MISSING_DISCRIMINATOR`.
   - **No candidate is preselected**, and **no "Suggested" label is rendered**.
   - The approval button is disabled until the reviewer makes an explicit choice.
4. Select `PIPE-001` (Class A). Add note: *"Approved Class A per standard facility spec"*.
5. Click **"Approve Match"**. The line item updates to **Approved**, version advances to 2, and the decision snapshot is appended to the audit history.

---

### 4. Stale-Version Conflict & Recovery (1:45 – 2:15)

1. Open Line 3 in a second browser tab (or simulate stale expected version `1`).
2. Attempt to submit a decision with `expected_version = 1`.
3. The API rejects the request atomically with **HTTP 409 `STALE_VERSION`**.
4. The frontend renders an inline warning: *"This line item was modified by another reviewer (version conflict). Please reload the latest state before proceeding."*
5. Click **"Reload Latest"** to seamlessly re-synchronize state.

---

### 5. Manual Correction & No-Match Handling (2:15 – 2:45)

1. Open Line 4 (`Unknown Custom Valve Widget`). The system found no matching products (`LOW_SIMILARITY`).
2. Click **"Confirm No Match"**. The line updates to **No Match**.
3. Open Line 2 (`MS Hex Bolt M12x50`). Suppose the purchaser changed requirements to a ball valve.
4. In the Manual Catalog Search box, type `"valve"`.
5. Select `VALV-001` (Brass Ball Valve Screwed 15mm), override quantity to `10`, unit to `nos`, enter note: *"Client requested valve substitution"*, and click **"Correct to Catalog Product"**.
6. The line updates to **Corrected** with `overrode_system = true`.

---

### 6. Gated Safe Export & Formula Neutralization (2:45 – 3:00)

1. Return to the RFQ details page.
2. If any line remained pending, clicking **Export CSV** triggers an **Incomplete RFQ Warning Modal** (preventing accidental export of unreviewed items).
3. With all lines reviewed, click **"Export CSV"**.
4. The downloaded RFC 4180 CSV:
   - Contains only finalized approved/corrected items (`PIPE-001` and `VALV-001`).
   - Omits rejected and no-match items (verified via `X-Items-Excluded: 2` response header).
   - Neutralizes any leading `= + - @` spreadsheet formula characters by prepending `'`.
   - **Contains zero price fields.**

---

## Part 2: Video Recording Script & Shot List

> [!NOTE]
> **Recording Status:** Outstanding operator action. This repository is maintained in a headless CI/CLI environment. The precise video recording shot list and narration script below allow any operator to record the video in under 3 minutes. The entire underlying flow is continuously verified by `make e2e`.

| Timestamp | Visual Focus / Shot | Screen Action | Narration Script |
|---|---|---|---|
| **0:00 – 0:25** | Terminal window | Run `make up`. Show containers starting, Alembic migration applying, and catalog seeding 100 products. | *"Welcome to the RFQ Line-Item Normalizer. We're launching the complete stack—PostgreSQL, FastAPI, and Next.js—in under 45 seconds using Docker Compose. All data is 100% synthetic."* |
| **0:25 – 0:50** | Browser at `localhost:3000/rfqs/new` | Click "Load Sample RFQ". Show the 4-line industrial text paste with mixed units and abbreviations. Click "Import & Normalize". | *"Purchasers send messy RFQs with abbreviations, mixed units, and missing specs. We paste a raw 4-line order. In under 50 milliseconds, our pure Python domain engine parses specs and matches against our catalog."* |
| **0:50 – 1:30** | Browser at `localhost:3000/rfqs/<id>` then `/items/<itemId>` | Show the RFQ table with non-color-alone badges. Click into Line 3 (`GI Pipe 25mm 50 mtr`). Highlight the radio buttons: neither is preselected. Select `PIPE-001` and approve. | *"Notice the status badges: each has text, an icon, and a distinct shape. On Line 3, the buyer asked for 25mm pipe without specifying Class A or Class B. Instead of guessing, the system abstains with SPEC_MISSING_DISCRIMINATOR. No candidate is preselected, forcing an explicit human choice."* |
| **1:30 – 2:05** | Browser inspecting candidate list and decision modal | Open second tab, submit stale edit. Show HTTP 409 conflict banner and reload button. | *"To protect multi-user integrity, every review action enforces optimistic concurrency control. An outdated version returns HTTP 409 STALE_VERSION, preventing silent overwrites and prompting the reviewer to reload."* |
| **2:05 – 2:35** | Line review screen for Line 2 and Line 4 | Search catalog for `VALV-001` and submit a correction. On Line 4, click Confirm No Match. | *"Reviewers can correct items to any catalog SKU with quantity overrides, or confirm no match for custom items. All decisions are appended to an immutable audit trail with system snapshots."* |
| **2:35 – 3:00** | RFQ summary page and downloaded CSV file | Click Export CSV. Open downloaded CSV file in spreadsheet/text editor. Show header and rows. | *"Finally, exports are gated. The RFC 4180 CSV export contains only human-finalized lines. Spreadsheet formula prefixes are neutralized, and zero price fields exist anywhere in the application. Run `make all` to verify all 170 tests and frozen benchmark reproducibility."* |
