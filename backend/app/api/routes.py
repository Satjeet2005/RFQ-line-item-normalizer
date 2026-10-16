import uuid

from app.core.errors import APIError
from app.db.models import RFQ, CatalogProduct, LineItem
from app.db.session import check_db_health, get_db
from app.schemas.rfq import (
    CatalogProductSchema,
    CatalogSearchResponse,
    DecisionCreateRequest,
    LineItemDetailSchema,
    LineItemListResponse,
    LineItemSchema,
    ReviewDecisionSchema,
    RFQCreateRequest,
    RFQCreateResponse,
    RFQDetailResponse,
    RFQListResponse,
    RFQSchema,
    RFQSummaryCounts,
    SkippedRow,
)
from app.services.export import export_rfq
from app.services.ingest import ingest_rfq
from app.services.review import record_decision
from fastapi import APIRouter, Depends, Query
from sqlalchemy import String, cast, func
from sqlalchemy.orm import Session, joinedload

router = APIRouter(prefix="/api/v1")

def _compute_rfq_counts(db: Session, rfq_id: uuid.UUID) -> RFQSummaryCounts:
    items = db.query(LineItem.review_status, LineItem.system_outcome).filter(LineItem.rfq_id == rfq_id).all()
    status_counts = {"pending": 0, "approved": 0, "corrected": 0, "rejected": 0, "no_match": 0}
    outcome_counts = {"proposed": 0, "ambiguous": 0, "unmatched": 0}
    for status, outcome in items:
        status_counts[status] = status_counts.get(status, 0) + 1
        outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1

    total_lines = len(items)
    is_complete = (status_counts.get("pending", 0) == 0 and total_lines > 0)
    return RFQSummaryCounts(
        by_review_status=status_counts,
        by_system_outcome=outcome_counts,
        total_lines=total_lines,
        complete=is_complete,
    )

# 1. Health check
@router.get("/health")
def health_check():
    is_healthy = check_db_health()
    if not is_healthy:
        raise APIError(
            status_code=503,
            code="DB_UNAVAILABLE",
            message="Database connection unavailable",
        )
    return {"status": "ok"}

# 2. RFQ creation
@router.post("/rfqs", status_code=201, response_model=RFQCreateResponse)
def create_rfq(payload: RFQCreateRequest, db: Session = Depends(get_db)):
    rfq, items_summary, row_errors = ingest_rfq(
        db=db,
        name=payload.name,
        source_type=payload.source_type,
        content=payload.content,
        skip_invalid=payload.skip_invalid,
    )
    counts = _compute_rfq_counts(db, rfq.id)
    rfq_schema = RFQSchema.model_validate(rfq)
    rfq_schema.counts = counts

    skipped = [
        SkippedRow(
            row=err["row"],
            code=err["code"],
            message=err["message"],
            raw=err["raw"],
        )
        for err in row_errors
    ]

    return RFQCreateResponse(
        rfq=rfq_schema,
        items_summary=items_summary,
        skipped=skipped,
    )

# 3. List RFQs
@router.get("/rfqs", response_model=RFQListResponse)
def list_rfqs(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    total = db.query(RFQ).count()
    rfqs = (
        db.query(RFQ)
        .order_by(RFQ.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    items = []
    for rfq in rfqs:
        rfq_schema = RFQSchema.model_validate(rfq)
        rfq_schema.counts = _compute_rfq_counts(db, rfq.id)
        items.append(rfq_schema)

    return RFQListResponse(items=items, total=total)

# 4. Get RFQ summary
@router.get("/rfqs/{rfq_id}", response_model=RFQDetailResponse)
def get_rfq(rfq_id: uuid.UUID, db: Session = Depends(get_db)):
    rfq = db.query(RFQ).filter(RFQ.id == rfq_id).first()
    if not rfq:
        raise APIError(
            status_code=404,
            code="RFQ_NOT_FOUND",
            message=f"RFQ {rfq_id} not found",
        )

    counts = _compute_rfq_counts(db, rfq.id)
    rfq_schema = RFQSchema.model_validate(rfq)
    rfq_schema.counts = counts
    return RFQDetailResponse(
        rfq=rfq_schema,
        counts=counts,
        complete=counts.complete,
    )

# 5. List Line Items for an RFQ
@router.get("/rfqs/{rfq_id}/items", response_model=LineItemListResponse)
def list_line_items(
    rfq_id: uuid.UUID,
    review_status: str | None = Query(None),
    system_outcome: str | None = Query(None),
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    rfq = db.query(RFQ).filter(RFQ.id == rfq_id).first()
    if not rfq:
        raise APIError(
            status_code=404,
            code="RFQ_NOT_FOUND",
            message=f"RFQ {rfq_id} not found",
        )

    query = (
        db.query(LineItem)
        .filter(LineItem.rfq_id == rfq_id)
        .options(joinedload(LineItem.candidates))
    )

    if review_status:
        valid_statuses = {"pending", "approved", "corrected", "rejected", "no_match"}
        if review_status not in valid_statuses:
            raise APIError(
                status_code=422,
                code="VALIDATION_ERROR",
                message=f"Invalid review_status: {review_status}. Must be one of {sorted(valid_statuses)}",
            )
        query = query.filter(LineItem.review_status == review_status)

    if system_outcome:
        valid_outcomes = {"proposed", "ambiguous", "unmatched"}
        if system_outcome not in valid_outcomes:
            raise APIError(
                status_code=422,
                code="VALIDATION_ERROR",
                message=f"Invalid system_outcome: {system_outcome}. Must be one of {sorted(valid_outcomes)}",
            )
        query = query.filter(LineItem.system_outcome == system_outcome)

    total = query.count()
    items = query.order_by(LineItem.line_no.asc()).offset(offset).limit(limit).all()

    return LineItemListResponse(
        items=[LineItemSchema.model_validate(it) for it in items],
        total=total,
    )

# 6. Get single Line Item detail
@router.get("/rfqs/{rfq_id}/items/{item_id}", response_model=LineItemDetailSchema)
def get_line_item(
    rfq_id: uuid.UUID,
    item_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    item = (
        db.query(LineItem)
        .filter(LineItem.id == item_id, LineItem.rfq_id == rfq_id)
        .options(joinedload(LineItem.candidates), joinedload(LineItem.decisions))
        .first()
    )
    if not item:
        raise APIError(
            status_code=404,
            code="ITEM_NOT_FOUND",
            message=f"Line item {item_id} not found in RFQ {rfq_id}",
        )

    return LineItemDetailSchema.model_validate(item)

# 7. Record decision
@router.post("/rfqs/{rfq_id}/items/{item_id}/decisions", status_code=201)
def make_decision(
    rfq_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: DecisionCreateRequest,
    db: Session = Depends(get_db),
):
    decision, item = record_decision(
        db=db,
        rfq_id=rfq_id,
        item_id=item_id,
        decision_type=payload.decision_type,
        expected_version=payload.expected_version,
        sku=payload.sku,
        quantity=payload.quantity,
        unit=payload.unit,
        note=payload.note,
    )

    return {
        "decision": ReviewDecisionSchema.model_validate(decision),
        "item": LineItemSchema.model_validate(item),
    }

# 8. Catalog Search
@router.get("/catalog", response_model=CatalogSearchResponse)
def search_catalog(
    q: str = Query("", max_length=80),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(CatalogProduct)
    trimmed = q.strip()
    if trimmed:
        pattern = f"%{trimmed.lower()}%"
        # Search over sku, name, and aliases JSON array as text
        query = query.filter(
            func.lower(CatalogProduct.sku).like(pattern)
            | func.lower(CatalogProduct.name).like(pattern)
            | cast(CatalogProduct.aliases, String).ilike(pattern)
        )

    total = query.count()
    products = query.order_by(CatalogProduct.sku.asc()).limit(limit).all()

    return CatalogSearchResponse(
        items=[CatalogProductSchema.model_validate(p) for p in products],
        total=total,
    )

# 9. Export
@router.get("/rfqs/{rfq_id}/export")
def export_rfq_endpoint(
    rfq_id: uuid.UUID,
    format: str = Query("csv"),
    allow_incomplete: bool = Query(False),
    db: Session = Depends(get_db),
):
    return export_rfq(
        db=db,
        rfq_id=rfq_id,
        export_format=format.lower(),
        allow_incomplete=allow_incomplete,
    )
