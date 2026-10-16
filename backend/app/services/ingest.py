import csv
import io
import json
import uuid
from decimal import Decimal
from typing import Any

from app.core.config import DATA_DIR
from app.core.errors import APIError
from app.db.models import RFQ, CandidateMatch, CatalogProduct, LineItem
from app.db.seed import get_catalog_version, get_matching_config_hash
from domain.matcher import ProposedMatcher
from domain.normalizer import normalize_line, parse_quantity
from domain.split import is_valid_qty_token, split_raw_line
from domain.types import Issue
from domain.units import UNIT_ALIASES, convert_quantity, normalize_unit
from sqlalchemy.orm import Session

MAX_LINES = 200
MAX_CONTENT_BYTES = 256 * 1024
MAX_ROW_CHARS = 2000
MAX_DESCRIPTION_CHARS = 300

def _get_catalog_dict_from_db(db: Session) -> list[dict[str, Any]]:
    db_items = db.query(CatalogProduct).order_by(CatalogProduct.sku).all()
    items = []
    for p in db_items:
        items.append({
            "sku": p.sku,
            "name": p.name,
            "category": p.category,
            "uom": p.uom,
            "attributes": p.attributes or {},
            "aliases": p.aliases or [],
        })
    return items

class ParsedRow:
    def __init__(
        self,
        source_row: int,
        raw_input: str,
        description_raw: str,
        quantity_raw: str | None = None,
        unit_raw: str | None = None,
    ):
        self.source_row = source_row
        self.raw_input = raw_input
        self.description_raw = description_raw
        self.quantity_raw = quantity_raw
        self.unit_raw = unit_raw

def _check_encoding_and_size(content: str) -> str:
    if "\ufffd" in content:
        raise APIError(
            status_code=422,
            code="UNSUPPORTED_ENCODING",
            message="Content contains unsupported character encoding (U+FFFD replacement character detected)",
        )
    # Strip leading UTF-8 BOM if present
    cleaned = content.lstrip("\ufeff")
    encoded_bytes = cleaned.encode("utf-8")
    if len(encoded_bytes) > MAX_CONTENT_BYTES:
        raise APIError(
            status_code=413,
            code="INPUT_TOO_LARGE",
            message=f"Input exceeds maximum allowed size of {MAX_CONTENT_BYTES // 1024} KB",
        )
    return cleaned

def _parse_pasted_text(
    content: str,
) -> tuple[list[ParsedRow], list[dict[str, Any]]]:
    known_unit_aliases = set(UNIT_ALIASES.keys())
    lines = content.splitlines()
    valid_rows: list[ParsedRow] = []
    row_errors: list[dict[str, Any]] = []

    # Filter out blank lines and comments for counting and indexing
    source_row = 0
    for original_line in lines:
        source_row += 1
        stripped = original_line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        raw_input = original_line

        # Size check on raw input
        if len(raw_input) > MAX_ROW_CHARS:
            row_errors.append({
                "row": source_row,
                "code": "ROW_TOO_LONG",
                "message": f"Line exceeds maximum length of {MAX_ROW_CHARS} characters",
                "raw": raw_input,
            })
            continue

        # Delimited vs free-text split
        if "|" in stripped or "\t" in stripped:
            delim = "|" if "|" in stripped else "\t"
            parts = [p.strip() for p in stripped.split(delim)]
            if len(parts) > 3:
                row_errors.append({
                    "row": source_row,
                    "code": "MALFORMED_ROW",
                    "message": f"Delimited line contains {len(parts)} fields; maximum is 3",
                    "raw": raw_input,
                })
                continue
            desc = parts[0]
            qty = parts[1] if len(parts) > 1 and parts[1] else None
            unit = parts[2] if len(parts) > 2 and parts[2] else None
        else:
            ingested = split_raw_line(stripped, known_unit_aliases)
            desc = ingested.description_raw
            qty = ingested.quantity_raw
            unit = ingested.unit_raw

        if not desc or not desc.strip():
            row_errors.append({
                "row": source_row,
                "code": "EMPTY_DESCRIPTION",
                "message": "Description is empty",
                "raw": raw_input,
            })
            continue

        if len(desc.strip()) > MAX_DESCRIPTION_CHARS:
            row_errors.append({
                "row": source_row,
                "code": "ROW_TOO_LONG",
                "message": f"Description exceeds maximum length of {MAX_DESCRIPTION_CHARS} characters",
                "raw": raw_input,
            })
            continue

        # Validate quantity if present
        if qty is not None:
            _parsed_qty, qty_issues = parse_quantity(qty, None)
            invalid_issue = next((i for i in qty_issues if i.code == "INVALID_QUANTITY"), None)
            if invalid_issue:
                row_errors.append({
                    "row": source_row,
                    "code": "INVALID_QUANTITY",
                    "message": invalid_issue.detail,
                    "raw": raw_input,
                })
                continue

        valid_rows.append(
            ParsedRow(
                source_row=source_row,
                raw_input=raw_input,
                description_raw=desc,
                quantity_raw=qty,
                unit_raw=unit,
            )
        )

    if len(valid_rows) + len(row_errors) > MAX_LINES:
        raise APIError(
            status_code=413,
            code="INPUT_TOO_LARGE",
            message=f"Input exceeds maximum allowed line count of {MAX_LINES}",
        )

    return valid_rows, row_errors

def _parse_csv_content(
    content: str,
) -> tuple[list[ParsedRow], list[dict[str, Any]], list[str]]:
    warnings: list[str] = []
    if not content or not content.strip():
        raise APIError(
            status_code=422,
            code="EMPTY_FILE",
            message="Uploaded CSV file is empty",
        )

    # Split lines preserving original lines for exact raw_input
    raw_lines = content.splitlines()
    if not raw_lines:
        raise APIError(
            status_code=422,
            code="EMPTY_FILE",
            message="Uploaded CSV file is empty",
        )

    reader = csv.reader(io.StringIO(content))
    try:
        header_row = next(reader)
    except StopIteration:
        raise APIError(
            status_code=422,
            code="EMPTY_FILE",
            message="Uploaded CSV file is empty",
        )

    headers = [h.strip().lower() for h in header_row]
    if len(headers) != len(set(headers)):
        raise APIError(
            status_code=422,
            code="DUPLICATE_COLUMN",
            message="CSV contains duplicate column headers",
        )

    if "description" not in headers:
        raise APIError(
            status_code=422,
            code="MISSING_REQUIRED_COLUMN",
            message="Missing required column: description",
            details=[{"field": "description", "code": "MISSING_REQUIRED_COLUMN", "message": "Missing required column 'description'"}],
        )

    if "quantity" not in headers:
        raise APIError(
            status_code=422,
            code="MISSING_REQUIRED_COLUMN",
            message="Missing required column: quantity",
            details=[{"field": "quantity", "code": "MISSING_REQUIRED_COLUMN", "message": "Missing required column 'quantity'"}],
        )

    desc_idx = headers.index("description")
    qty_idx = headers.index("quantity")
    unit_idx = headers.index("unit") if "unit" in headers else -1

    known_cols = {"description", "quantity", "unit", "line_ref"}
    unknown_cols = [h for h in headers if h not in known_cols]
    if unknown_cols:
        warnings.append(f"Unknown columns ignored: {', '.join(unknown_cols)}")

    valid_rows: list[ParsedRow] = []
    row_errors: list[dict[str, Any]] = []

    data_row_count = 0

    for i, row in enumerate(reader):
        data_row_count += 1
        source_row = data_row_count
        # Preserve exact raw_input from original line (index i + 1 in raw_lines)
        raw_input = raw_lines[i + 1] if (i + 1) < len(raw_lines) else ",".join(row)

        if len(raw_input) > MAX_ROW_CHARS:
            row_errors.append({
                "row": source_row,
                "code": "ROW_TOO_LONG",
                "message": f"Row exceeds maximum length of {MAX_ROW_CHARS} characters",
                "raw": raw_input,
            })
            continue

        if len(row) != len(headers):
            row_errors.append({
                "row": source_row,
                "code": "MALFORMED_ROW",
                "message": f"Row field count ({len(row)}) does not match header count ({len(headers)})",
                "raw": raw_input,
            })
            continue

        desc = row[desc_idx].strip()
        if not desc:
            row_errors.append({
                "row": source_row,
                "code": "EMPTY_DESCRIPTION",
                "message": "Description cell is empty",
                "raw": raw_input,
            })
            continue

        if len(desc) > MAX_DESCRIPTION_CHARS:
            row_errors.append({
                "row": source_row,
                "code": "ROW_TOO_LONG",
                "message": f"Description exceeds maximum length of {MAX_DESCRIPTION_CHARS} characters",
                "raw": raw_input,
            })
            continue

        qty_cell = row[qty_idx].strip() if row[qty_idx] else ""
        unit_cell = row[unit_idx].strip() if unit_idx >= 0 and row[unit_idx] else ""

        qty_str: str | None = None
        unit_str: str | None = unit_cell if unit_cell else None

        if not qty_cell:
            qty_str = None
        else:
            # Check if quantity cell contains text with unit (e.g. "50 mtr")
            tokens = qty_cell.split()
            if len(tokens) == 2 and is_valid_qty_token(tokens[0]):
                qty_val_candidate = tokens[0]
                unit_val_candidate = tokens[1]
                if not unit_cell:
                    qty_str = qty_val_candidate
                    unit_str = unit_val_candidate
                else:
                    # Both give a unit; check for conflict during normalization
                    qty_str = qty_val_candidate
                    # If they differ after normalization, normalizer will flag or we can flag here
                    norm_cell_unit = normalize_unit(unit_val_candidate)
                    norm_col_unit = normalize_unit(unit_cell)
                    if norm_cell_unit and norm_col_unit and norm_cell_unit != norm_col_unit:
                        # UNIT_CONFLICT soft issue handled below
                        unit_str = unit_cell
                    else:
                        unit_str = unit_cell
            else:
                qty_str = qty_cell

        # Validate quantity format
        if qty_str is not None:
            _parsed_qty, qty_issues = parse_quantity(qty_str, None)
            invalid_issue = next((iss for iss in qty_issues if iss.code == "INVALID_QUANTITY"), None)
            if invalid_issue:
                row_errors.append({
                    "row": source_row,
                    "code": "INVALID_QUANTITY",
                    "message": invalid_issue.detail,
                    "raw": raw_input,
                })
                continue

        valid_rows.append(
            ParsedRow(
                source_row=source_row,
                raw_input=raw_input,
                description_raw=desc,
                quantity_raw=qty_str,
                unit_raw=unit_str,
            )
        )

    if data_row_count == 0:
        raise APIError(
            status_code=422,
            code="NO_ROWS",
            message="CSV file contains header only with no data rows",
        )

    if data_row_count > MAX_LINES:
        raise APIError(
            status_code=413,
            code="INPUT_TOO_LARGE",
            message=f"CSV row count ({data_row_count}) exceeds maximum allowed limit of {MAX_LINES}",
        )

    return valid_rows, row_errors, warnings

def ingest_rfq(
    db: Session,
    name: str,
    source_type: str,
    content: str,
    skip_invalid: bool = False,
) -> tuple[RFQ, dict[str, Any], list[dict[str, Any]]]:
    clean_content = _check_encoding_and_size(content)

    warnings: list[str] = []
    if source_type == "paste":
        valid_rows, row_errors = _parse_pasted_text(clean_content)
    elif source_type == "csv":
        valid_rows, row_errors, warnings = _parse_csv_content(clean_content)
    else:
        raise APIError(status_code=422, code="VALIDATION_ERROR", message=f"Invalid source_type: {source_type}")

    if row_errors and not skip_invalid:
        raise APIError(
            status_code=422,
            code="ROW_ERRORS",
            message=f"Input contains {len(row_errors)} invalid row(s)",
            details=row_errors,
        )

    if not valid_rows:
        raise APIError(
            status_code=422,
            code="NO_VALID_ROWS",
            message="No valid rows could be extracted from input",
        )

    catalog_items = _get_catalog_dict_from_db(db)
    with open(DATA_DIR / "matching_config.json", "r", encoding="utf-8") as f:
        matching_config = json.load(f)
    matcher = ProposedMatcher(catalog_items, matching_config)

    catalog_version = get_catalog_version()
    matching_config_hash = get_matching_config_hash()

    try:
        rfq = RFQ(
            id=uuid.uuid4(),
            name=name,
            source_type=source_type,
            catalog_version=catalog_version,
            matching_config_hash=matching_config_hash,
            skipped_count=len(row_errors),
        )
        db.add(rfq)
        db.flush()

        line_items: list[LineItem] = []
        seen_rows: dict[tuple[str, str | None, str | None], int] = {}

        for line_idx, row in enumerate(valid_rows):
            line_no = line_idx + 1

            norm = normalize_line(
                row.description_raw,
                quantity_input=row.quantity_raw,
                unit_input=row.unit_raw,
            )

            # Duplicate row check: identical in (normalized description, quantity, unit)
            qty_key = str(norm.quantity) if norm.quantity is not None else None
            key = (norm.description_normalized, qty_key, norm.unit)
            if key in seen_rows:
                earlier_line = seen_rows[key]
                norm.issues.append(
                    Issue(
                        code="DUPLICATE_OF_LINE",
                        severity="info",
                        detail=f"Line is identical to earlier line {earlier_line}",
                    )
                )
            else:
                seen_rows[key] = line_no

            match_res = matcher.match(norm)

            line_item = LineItem(
                id=uuid.uuid4(),
                rfq_id=rfq.id,
                line_no=line_no,
                source_row=row.source_row,
                raw_input=row.raw_input,
                description_raw=row.description_raw,
                quantity_raw=row.quantity_raw,
                unit_raw=row.unit_raw,
                description_normalized=norm.description_normalized,
                spec=norm.spec,
                quantity=float(norm.quantity) if norm.quantity is not None else None,
                unit=norm.unit,
                unit_dimension=norm.unit_dimension,
                issues=[{"code": i.code, "severity": i.severity, "detail": i.detail} for i in norm.issues],
                system_outcome=match_res.system_outcome,
                reason_codes=match_res.reason_codes,
                review_status="pending",
                final_sku=None,
                final_quantity=None,
                final_unit=None,
                version=1,
            )
            db.add(line_item)
            db.flush()

            for rank_idx, cand in enumerate(match_res.candidates, start=1):
                conversion = None
                if norm.quantity is not None and norm.unit and cand.uom:
                    converted_qty = convert_quantity(Decimal(str(norm.quantity)), norm.unit, cand.uom)
                    if converted_qty is not None:
                        conversion = {
                            "from_unit": norm.unit,
                            "to_uom": cand.uom,
                            "quantity_in_uom": float(converted_qty),
                        }

                cand_model = CandidateMatch(
                    id=uuid.uuid4(),
                    line_item_id=line_item.id,
                    rank=rank_idx,
                    sku=cand.sku,
                    name=cand.name,
                    uom=cand.uom or "",
                    attributes=cand.attributes or {},
                    similarity=float(cand.similarity),
                    disqualified=cand.disqualified,
                    flags=cand.flags or [],
                    conversion=conversion,
                )
                db.add(cand_model)

            line_items.append(line_item)

        db.commit()
        db.refresh(rfq)
    except Exception:
        db.rollback()
        raise

    # Calculate summary counts
    outcome_counts = {"proposed": 0, "ambiguous": 0, "unmatched": 0}
    for li in line_items:
        outcome_counts[li.system_outcome] = outcome_counts.get(li.system_outcome, 0) + 1

    items_summary = {
        "total_lines": len(line_items),
        "by_system_outcome": outcome_counts,
        "skipped_lines": len(row_errors),
        "warnings": warnings,
    }

    return rfq, items_summary, row_errors
