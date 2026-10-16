# 3-Minute Walkthrough: RFQ Line-Item Normalizer

This walkthrough demonstrates the end-to-end workflow using only synthetic industrial benchmark data.

> [!NOTE]
> All data in this walkthrough is synthetic. It contains no real customer, supplier, or pricing data.

---

## 1. Clean Startup (30 seconds)

1. Ensure Docker Engine is running on your machine.
2. In the repository root, start the application:
   ```bash
   make up
   ```
   This creates `.env` from `.env.example` if absent, builds the containers, applies the initial PostgreSQL migration, seeds the 100-item synthetic catalog idempotently, and starts the Next.js frontend on port 3000 and FastAPI on port 8000.
3. Open your browser to `http://localhost:3000`.

---

## 2. Ingest a Sample RFQ (45 seconds)

1. Click **"New RFQ"** in the top navigation bar (`/rfqs/new`).
2. Click the **"Load Sample RFQ"** button in the paste tab. This populates a synthetic 4-line industrial order:
   ```text
   GI Pipe 25mm Class B 100 mtr
   MS Hex Bolt M12x50 500 nos
   GI Pipe 25mm 50 mtr
   Unknown Custom Valve Widget 5 pcs
   ```
3. Set the RFQ Name to **"Synthetic Maintenance Order #101"**.
4. Click **"Import & Normalize RFQ"**.
5. The system parses, normalizes, and runs deterministic matching against the catalog in < 50ms, redirecting you to the RFQ Summary view (`/rfqs/<id>`).

---

## 3. Inspecting Normalization and Non-Preselection (45 seconds)

1. In the RFQ line item table, notice the non-color-alone status badges:
   - Line 1 (`GI Pipe 25mm Class B`): **Proposed** (purple badge with spark icon).
   - Line 2 (`MS Hex Bolt M12x50`): **Proposed** (purple badge with spark icon).
   - Line 3 (`GI Pipe 25mm 50 mtr`): **Ambiguous** (amber badge with alert triangle).
   - Line 4 (`Unknown Custom Valve Widget`): **Unmatched** (gray badge with question circle).
2. Click **Review** on Line 3 (`GI Pipe 25mm 50 mtr`).
3. Notice that:
   - The line is missing a class discriminator (`Class A` vs `Class B`).
   - The system correctly abstained with reason code `SPEC_MISSING_DISCRIMINATOR`.
   - **No candidate is preselected**, and **no "Suggested" label is displayed**.
   - The user must make an active, explicit choice.
4. Select the radio button for `PIPE-001` (Class A).
5. Add an optional note: *"Selected Class A per standard facility spec"*.
6. Click **"Approve Match"**.
7. The line item updates immediately to **Approved** (green check badge), version increments to 2, and the decision is appended to the audit history snapshot.

---

## 4. Rejecting and Confirming No-Match (30 seconds)

1. Navigate back to the RFQ summary.
2. Click **Review** on Line 4 (`Unknown Custom Valve Widget`).
3. The system found no matching products in the catalog (`LOW_SIMILARITY`).
4. Click **"Confirm No Match"**.
5. The line is finalized as **No Match** (gray dash badge).
6. Next, open Line 2 (`MS Hex Bolt M12x50`).
7. Enter a note: *"Not purchasing bolts this quarter"*, and click **"Reject"**.
8. The line is finalized as **Rejected** (red X badge).

---

## 5. Gated Export (30 seconds)

1. Return to the RFQ summary. Notice that Line 1 is still **Pending** review.
2. Click **"Export CSV"**.
3. A modal opens informing you: **"RFQ Review Incomplete"** (1 pending line).
4. The system prevents premature export of unreviewed items.
5. In the modal, click **"Export Finalized Lines Only"**.
6. The browser downloads the RFC 4180 CSV file:
   - Contains only the finalized approved lines (`PIPE-001`).
   - Response header `X-Items-Excluded: 3` accounts for the pending, rejected, and no-match lines.
   - All spreadsheet formula prefixes (`=`, `+`, `-`, `@`) are safely neutralized.
   - **Zero price fields are present anywhere in the export or database.**
