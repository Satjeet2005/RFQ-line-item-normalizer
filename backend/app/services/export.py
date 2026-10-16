import csv
import io
import uuid
from decimal import Decimal
from typing import Any

from app.core.errors import APIError
from app.db.models import RFQ, LineItem, ReviewDecision
from domain.units import convert_quantity
from fastapi.responses import JSONResponse, Response
from sqlalchemy.orm import Session

FORMULA_PREFIXES = ("=", "+", "-", "@")

def _neutralize_formula(val: Any) -> str:
    s = str(val) if val is not None else ""
    if s and s[0] in FORMULA_PREFIXES:
        return f"'{s}"
    return s

def export_rfq(
    db: Session,
    rfq_id: uuid.UUID,
    export_format: str,
    allow_incomplete: bool = False,
) -> Response:
    rfq = db.query(RFQ).filter(RFQ.id == rfq_id).first()
    if not rfq:
        raise APIError(
            status_code=404,
            code="RFQ_NOT_FOUND",
            message=f"RFQ {rfq_id} not found",
        )

    line_items = (
        db.query(LineItem)
        .filter(LineItem.rfq_id == rfq_id)
        .order_by(LineItem.line_no)
        .all()
    )

    pending_lines = [li for li in line_items if li.review_status == "pending"]
    is_complete = (len(pending_lines) == 0)

    if not is_complete and not allow_incomplete:
        raise APIError(
            status_code=409,
            code="RFQ_INCOMPLETE",
            message=f"RFQ has {len(pending_lines)} pending line(s). Set allow_incomplete=true to export finalized lines only.",
            details=[{"code": "PENDING_LINES", "pending_count": len(pending_lines)}],
        )

    finalized_lines = [
        li for li in line_items if li.review_status in ("approved", "corrected")
    ]
    excluded_lines = [
        li for li in line_items if li.review_status not in ("approved", "corrected")
    ]
    excluded_count = len(excluded_lines)

    if export_format == "csv":
        output = io.StringIO()
        writer = csv.writer(output, lineterminator="\n", quoting=csv.QUOTE_MINIMAL)

        # Header columns per PRD Workflow 7
        writer.writerow([
            "line_no",
            "original_description",
            "catalog_sku",
            "catalog_name",
            "requested_quantity",
            "requested_unit",
            "quantity_in_catalog_uom",
            "catalog_uom",
            "review_status",
            "overrode_system",
            "reviewed_at",
        ])

        for li in finalized_lines:
            latest_decision = (
                db.query(ReviewDecision)
                .filter(ReviewDecision.line_item_id == li.id)
                .order_by(ReviewDecision.created_at.desc())
                .first()
            )
            reviewed_at = (
                latest_decision.created_at.isoformat() if latest_decision else li.updated_at.isoformat()
            )
            overrode_system = (
                latest_decision.overrode_system if latest_decision else False
            )

            # Compute quantity in catalog uom
            qty_in_uom: float | None = None
            cat_name = ""
            cat_uom = ""
            if li.product:
                cat_name = li.product.name
                cat_uom = li.product.uom
                if li.final_quantity is not None and li.final_unit:
                    conv = convert_quantity(
                        Decimal(str(li.final_quantity)), li.final_unit, cat_uom
                    )
                    qty_in_uom = float(conv) if conv is not None else float(li.final_quantity)

            writer.writerow([
                li.line_no,
                _neutralize_formula(li.description_raw),
                _neutralize_formula(li.final_sku),
                _neutralize_formula(cat_name),
                li.final_quantity,
                _neutralize_formula(li.final_unit),
                qty_in_uom,
                _neutralize_formula(cat_uom),
                li.review_status,
                overrode_system,
                reviewed_at,
            ])

        csv_content = output.getvalue().encode("utf-8")
        filename = f"rfq_{rfq_id}_export.csv"
        return Response(
            content=csv_content,
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "X-Items-Excluded": str(excluded_count),
            },
        )

    elif export_format == "json":
        finalized_data = []
        for li in finalized_lines:
            latest_decision = (
                db.query(ReviewDecision)
                .filter(ReviewDecision.line_item_id == li.id)
                .order_by(ReviewDecision.created_at.desc())
                .first()
            )
            reviewed_at = (
                latest_decision.created_at.isoformat() if latest_decision else li.updated_at.isoformat()
            )
            overrode_system = (
                latest_decision.overrode_system if latest_decision else False
            )

            qty_in_uom = None
            cat_name = ""
            cat_uom = ""
            if li.product:
                cat_name = li.product.name
                cat_uom = li.product.uom
                if li.final_quantity is not None and li.final_unit:
                    conv = convert_quantity(
                        Decimal(str(li.final_quantity)), li.final_unit, cat_uom
                    )
                    qty_in_uom = float(conv) if conv is not None else float(li.final_quantity)

            finalized_data.append({
                "line_no": li.line_no,
                "original_description": li.description_raw,
                "catalog_sku": li.final_sku,
                "catalog_name": cat_name,
                "requested_quantity": float(li.final_quantity) if li.final_quantity is not None else None,
                "requested_unit": li.final_unit,
                "quantity_in_catalog_uom": qty_in_uom,
                "catalog_uom": cat_uom,
                "review_status": li.review_status,
                "overrode_system": overrode_system,
                "reviewed_at": reviewed_at,
            })

        not_finalized_data = []
        for li in excluded_lines:
            suggestion = None
            if li.candidates:
                top_cand = sorted(li.candidates, key=lambda c: c.rank)[0]
                suggestion = {
                    "sku": top_cand.sku,
                    "name": top_cand.name,
                    "uom": top_cand.uom,
                    "similarity": float(top_cand.similarity),
                    "disclaimer": "Unapproved system suggestion; not confirmed",
                }

            not_finalized_data.append({
                "line_no": li.line_no,
                "original_description": li.description_raw,
                "review_status": li.review_status,
                "system_outcome": li.system_outcome,
                "reason_codes": li.reason_codes or [],
                "suggestion": suggestion,
            })

        payload = {
            "rfq": {
                "id": str(rfq.id),
                "name": rfq.name,
                "created_at": rfq.created_at.isoformat(),
            },
            "complete": is_complete,
            "finalized": finalized_data,
            "not_finalized": not_finalized_data,
        }
        return JSONResponse(
            content=payload,
            headers={"X-Items-Excluded": str(excluded_count)},
        )

    else:
        raise APIError(
            status_code=422,
            code="VALIDATION_ERROR",
            message=f"Invalid export format: {export_format}. Supported formats are 'csv' and 'json'.",
        )
