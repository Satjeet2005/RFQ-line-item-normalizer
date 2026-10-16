import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RFQCreateRequest(BaseModel):
    name: str = Field(..., description="User label for RFQ (1-80 chars trimmed)")
    source_type: Literal["paste", "csv"]
    content: str
    skip_invalid: bool = False

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        trimmed = v.strip()
        if not (1 <= len(trimmed) <= 80):
            raise ValueError("RFQ name must be between 1 and 80 characters after trimming")
        return trimmed

class DecisionCreateRequest(BaseModel):
    decision_type: Literal["approve", "correct", "reject", "confirm_no_match"]
    expected_version: int
    sku: str | None = None
    quantity: Decimal | float | int | str | None = None
    unit: str | None = None
    note: str | None = None

class CandidateMatchSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    rank: int
    sku: str
    name: str
    uom: str
    attributes: dict[str, Any]
    similarity: float
    disqualified: bool
    flags: list[str]
    conversion: dict[str, Any] | None = None

class ReviewDecisionSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    line_item_id: uuid.UUID
    decision_type: str
    sku: str | None = None
    quantity: float | None = None
    unit: str | None = None
    note: str | None = None
    overrode_system: bool
    system_outcome_snapshot: str
    reason_codes_snapshot: list[str]
    status_before: str
    status_after: str
    version_before: int
    created_at: datetime

class LineItemSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    rfq_id: uuid.UUID
    line_no: int
    source_row: int
    raw_input: str
    description_raw: str
    quantity_raw: str | None = None
    unit_raw: str | None = None
    description_normalized: str
    spec: dict[str, Any]
    quantity: float | None = None
    unit: str | None = None
    unit_dimension: str | None = None
    issues: list[dict[str, Any]]
    system_outcome: str
    reason_codes: list[str]
    review_status: str
    final_sku: str | None = None
    final_quantity: float | None = None
    final_unit: str | None = None
    version: int
    created_at: datetime
    updated_at: datetime
    candidates: list[CandidateMatchSchema] = []

class LineItemDetailSchema(LineItemSchema):
    decisions: list[ReviewDecisionSchema] = []

class RFQSummaryCounts(BaseModel):
    by_review_status: dict[str, int]
    by_system_outcome: dict[str, int]
    total_lines: int
    complete: bool

class RFQSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    source_type: str
    catalog_version: str
    matching_config_hash: str
    skipped_count: int
    created_at: datetime
    counts: RFQSummaryCounts | None = None

class RFQDetailResponse(BaseModel):
    rfq: RFQSchema
    counts: RFQSummaryCounts
    complete: bool

class SkippedRow(BaseModel):
    row: int
    code: str
    message: str
    raw: str

class RFQCreateResponse(BaseModel):
    rfq: RFQSchema
    items_summary: dict[str, Any]
    skipped: list[SkippedRow] = []

class RFQListResponse(BaseModel):
    items: list[RFQSchema]
    total: int

class LineItemListResponse(BaseModel):
    items: list[LineItemSchema]
    total: int

class CatalogProductSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sku: str
    name: str
    category: str
    uom: str
    attributes: dict[str, Any]
    aliases: list[str]

class CatalogSearchResponse(BaseModel):
    items: list[CatalogProductSchema]
    total: int
