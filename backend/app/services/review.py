import uuid
from decimal import Decimal, InvalidOperation
from typing import Any

from app.core.errors import APIError
from app.db.models import CatalogProduct, LineItem, ReviewDecision
from domain.units import (
    check_unit_compatibility,
    is_count_unit,
    normalize_unit,
)
from sqlalchemy.orm import Session


def _validate_quantity_and_unit(
    req_qty: Any | None,
    req_unit: str | None,
    line_qty: float | None,
    line_unit: str | None,
    cat_product: CatalogProduct,
) -> tuple[Decimal, str]:
    # Determine effective quantity
    effective_qty_val: Decimal | None = None
    if req_qty is not None:
        try:
            val = Decimal(str(req_qty))
            if val <= Decimal(0) or val > Decimal(1000000):
                raise APIError(
                    status_code=422,
                    code="INVALID_QUANTITY",
                    message="Quantity must be greater than 0 and at most 1,000,000",
                )
            exp = val.as_tuple().exponent
            if isinstance(exp, int) and exp < -3:
                raise APIError(
                    status_code=422,
                    code="INVALID_QUANTITY",
                    message="Quantity precision exceeds 3 decimal places",
                )
            effective_qty_val = val
        except (InvalidOperation, ValueError):
            raise APIError(
                status_code=422,
                code="INVALID_QUANTITY",
                message=f"Invalid quantity value: {req_qty}",
            )
    elif line_qty is not None:
        effective_qty_val = Decimal(str(line_qty))
    else:
        raise APIError(
            status_code=422,
            code="QUANTITY_REQUIRED",
            message="Quantity is required to approve or correct this line item",
        )

    # Determine effective unit
    effective_unit_code: str | None = None
    if req_unit:
        norm_u = normalize_unit(req_unit)
        if not norm_u:
            raise APIError(
                status_code=422,
                code="UNIT_REQUIRED",
                message=f"Unrecognized or unsupported unit: {req_unit}",
            )
        effective_unit_code = norm_u
    elif line_unit:
        effective_unit_code = line_unit
    else:
        raise APIError(
            status_code=422,
            code="UNIT_REQUIRED",
            message="Unit is required to approve or correct this line item",
        )

    # Check compatibility with catalog product UOM
    is_compat, _error_code = check_unit_compatibility(effective_unit_code, cat_product.uom)
    if not is_compat:
        raise APIError(
            status_code=422,
            code="UNIT_INCOMPATIBLE",
            message=f"Unit '{effective_unit_code}' is incompatible with catalog product UOM '{cat_product.uom}'",
        )

    # If count unit, quantity must be integer
    if is_count_unit(cat_product.uom):
        if effective_qty_val % Decimal(1) != Decimal(0):
            raise APIError(
                status_code=422,
                code="INVALID_QUANTITY",
                message=f"Count unit '{cat_product.uom}' requires an integer quantity",
            )

    return effective_qty_val, effective_unit_code

def record_decision(
    db: Session,
    rfq_id: uuid.UUID,
    item_id: uuid.UUID,
    decision_type: str,
    expected_version: int,
    sku: str | None = None,
    quantity: Any | None = None,
    unit: str | None = None,
    note: str | None = None,
) -> tuple[ReviewDecision, LineItem]:
    # 1. Fetch current item
    item = (
        db.query(LineItem)
        .filter(LineItem.id == item_id, LineItem.rfq_id == rfq_id)
        .first()
    )
    if not item:
        raise APIError(
            status_code=404,
            code="ITEM_NOT_FOUND",
            message=f"Line item {item_id} not found in RFQ {rfq_id}",
        )

    # 2. Check optimistic concurrency version
    if item.version != expected_version:
        # Construct item payload for 409 body
        from app.schemas.rfq import LineItemSchema
        item_data = LineItemSchema.model_validate(item).model_dump(mode="json")
        raise APIError(
            status_code=409,
            code="STALE_VERSION",
            message=f"Line item was modified by another decision (client version: {expected_version}, current version: {item.version})",
            extra_body={"item": item_data},
        )

    status_before = item.review_status
    version_before = item.version
    system_outcome_snapshot = item.system_outcome
    reason_codes_snapshot = list(item.reason_codes or [])

    # Fetch candidate SKUs for candidate checks
    candidate_skus = [c.sku for c in item.candidates]
    top_cand = sorted(item.candidates, key=lambda c: c.rank)[0] if item.candidates else None

    new_status: str
    final_sku: str | None = None
    final_qty: Decimal | None = None
    final_unit: str | None = None
    overrode_system: bool = False

    if decision_type == "approve":
        if not sku:
            raise APIError(
                status_code=422,
                code="SKU_NOT_A_CANDIDATE",
                message="A candidate product SKU must be selected to approve",
            )
        if sku not in candidate_skus:
            raise APIError(
                status_code=422,
                code="SKU_NOT_A_CANDIDATE",
                message=f"Product {sku} is not in the candidate list for this item",
            )
        cat_product = db.query(CatalogProduct).filter(CatalogProduct.sku == sku).first()
        if not cat_product:
            raise APIError(
                status_code=422,
                code="SKU_NOT_FOUND",
                message=f"Catalog product {sku} not found",
            )

        final_qty, final_unit = _validate_quantity_and_unit(
            quantity, unit, item.quantity, item.unit, cat_product
        )
        final_sku = sku
        new_status = "approved"

        # Determine override
        if item.system_outcome != "proposed" or (top_cand and top_cand.sku != sku):
            overrode_system = True
        else:
            overrode_system = False

    elif decision_type == "correct":
        if not sku:
            raise APIError(
                status_code=422,
                code="SKU_NOT_FOUND",
                message="A product SKU must be provided for correction",
            )
        cat_product = db.query(CatalogProduct).filter(CatalogProduct.sku == sku).first()
        if not cat_product:
            raise APIError(
                status_code=422,
                code="SKU_NOT_FOUND",
                message=f"Catalog product {sku} does not exist in catalog",
            )
        if sku in candidate_skus:
            raise APIError(
                status_code=422,
                code="SKU_IS_A_CANDIDATE",
                message=f"Product {sku} is already a listed candidate; use 'approve' instead of 'correct'",
            )

        final_qty, final_unit = _validate_quantity_and_unit(
            quantity, unit, item.quantity, item.unit, cat_product
        )
        final_sku = sku
        new_status = "corrected"
        overrode_system = True

    elif decision_type == "reject":
        trimmed_note = (note or "").strip()
        if len(trimmed_note) < 3 or len(trimmed_note) > 500:
            raise APIError(
                status_code=422,
                code="NOTE_REQUIRED",
                message="A note of between 3 and 500 characters is required to reject a line item",
            )
        new_status = "rejected"
        final_sku = None
        final_qty = None
        final_unit = None
        overrode_system = (item.system_outcome == "proposed")

    elif decision_type == "confirm_no_match":
        if note and len(note.strip()) > 500:
            raise APIError(
                status_code=422,
                code="NOTE_TOO_LONG",
                message="Note cannot exceed 500 characters",
            )
        new_status = "no_match"
        final_sku = None
        final_qty = None
        final_unit = None
        overrode_system = (item.system_outcome == "proposed")

    else:
        raise APIError(
            status_code=422,
            code="VALIDATION_ERROR",
            message=f"Invalid decision type: {decision_type}",
        )

    # 3. Perform atomic update with WHERE version = expected_version
    update_res = (
        db.query(LineItem)
        .filter(LineItem.id == item_id, LineItem.version == expected_version)
        .update(
            {
                "review_status": new_status,
                "final_sku": final_sku,
                "final_quantity": float(final_qty) if final_qty is not None else None,
                "final_unit": final_unit,
                "version": LineItem.version + 1,
            },
            synchronize_session="fetch",
        )
    )

    if update_res == 0:
        # Race condition: item changed right between our check and update
        db.refresh(item)
        from app.schemas.rfq import LineItemSchema
        item_data = LineItemSchema.model_validate(item).model_dump(mode="json")
        raise APIError(
            status_code=409,
            code="STALE_VERSION",
            message=f"Line item was modified concurrently (version: {item.version})",
            extra_body={"item": item_data},
        )

    # 4. Insert append-only decision record
    decision = ReviewDecision(
        id=uuid.uuid4(),
        line_item_id=item_id,
        decision_type=decision_type,
        sku=final_sku,
        quantity=float(final_qty) if final_qty is not None else None,
        unit=final_unit,
        note=note.strip() if note else None,
        overrode_system=overrode_system,
        system_outcome_snapshot=system_outcome_snapshot,
        reason_codes_snapshot=reason_codes_snapshot,
        status_before=status_before,
        status_after=new_status,
        version_before=version_before,
    )
    db.add(decision)
    db.commit()
    db.refresh(item)
    db.refresh(decision)

    return decision, item
