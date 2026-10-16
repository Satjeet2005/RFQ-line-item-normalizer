import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class RFQ(Base):
    __tablename__ = "rfqs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(80), nullable=False)
    source_type = Column(
        String(10),
        nullable=False,
    )
    catalog_version = Column(String(64), nullable=False)
    matching_config_hash = Column(String(64), nullable=False)
    skipped_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("source_type IN ('paste', 'csv')", name="ck_rfq_source_type"),
    )

    line_items = relationship(
        "LineItem",
        back_populates="rfq",
        cascade="all, delete-orphan",
        order_by="LineItem.line_no",
    )


class CatalogProduct(Base):
    __tablename__ = "catalog_products"

    sku = Column(String(32), primary_key=True)
    name = Column(String(255), nullable=False)
    category = Column(String(64), nullable=False)
    uom = Column(String(32), nullable=False)
    attributes = Column(JSONB, nullable=False, default=dict)
    aliases = Column(JSONB, nullable=False, default=list)


class LineItem(Base):
    __tablename__ = "rfq_line_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rfq_id = Column(UUID(as_uuid=True), ForeignKey("rfqs.id", ondelete="CASCADE"), nullable=False)
    line_no = Column(Integer, nullable=False)
    source_row = Column(Integer, nullable=False)
    raw_input = Column(String(2000), nullable=False)
    description_raw = Column(Text, nullable=False)
    quantity_raw = Column(Text, nullable=True)
    unit_raw = Column(Text, nullable=True)
    description_normalized = Column(Text, nullable=False)
    spec = Column(JSONB, nullable=False, default=dict)
    quantity = Column(Numeric(14, 3), nullable=True)
    unit = Column(String(32), nullable=True)
    unit_dimension = Column(String(32), nullable=True)
    issues = Column(JSONB, nullable=False, default=list)
    system_outcome = Column(String(20), nullable=False)
    reason_codes = Column(JSONB, nullable=False, default=list)
    review_status = Column(String(20), nullable=False, default="pending")
    final_sku = Column(String(32), ForeignKey("catalog_products.sku"), nullable=True)
    final_quantity = Column(Numeric(14, 3), nullable=True)
    final_unit = Column(String(32), nullable=True)
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        UniqueConstraint("rfq_id", "line_no", name="uq_rfq_line_no"),
        CheckConstraint(
            "system_outcome IN ('proposed', 'ambiguous', 'unmatched')",
            name="ck_system_outcome",
        ),
        CheckConstraint(
            "review_status IN ('pending', 'approved', 'corrected', 'rejected', 'no_match')",
            name="ck_review_status",
        ),
        CheckConstraint(
            "((review_status IN ('approved', 'corrected') AND final_sku IS NOT NULL AND final_quantity IS NOT NULL AND final_unit IS NOT NULL) OR "
            "(review_status NOT IN ('approved', 'corrected') AND final_sku IS NULL AND final_quantity IS NULL AND final_unit IS NULL))",
            name="ck_final_fields_iff_finalized",
        ),
    )

    rfq = relationship("RFQ", back_populates="line_items")
    candidates = relationship(
        "CandidateMatch",
        back_populates="line_item",
        cascade="all, delete-orphan",
        order_by="CandidateMatch.rank",
    )
    decisions = relationship(
        "ReviewDecision",
        back_populates="line_item",
        order_by="ReviewDecision.created_at",
    )
    product = relationship("CatalogProduct", foreign_keys=[final_sku])


class CandidateMatch(Base):
    __tablename__ = "candidate_matches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    line_item_id = Column(
        UUID(as_uuid=True),
        ForeignKey("rfq_line_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    rank = Column(Integer, nullable=False)
    sku = Column(String(32), ForeignKey("catalog_products.sku"), nullable=False)
    name = Column(String(255), nullable=False)
    uom = Column(String(32), nullable=False)
    attributes = Column(JSONB, nullable=False, default=dict)
    similarity = Column(Numeric(5, 4), nullable=False)
    disqualified = Column(Boolean, nullable=False, default=False)
    flags = Column(JSONB, nullable=False, default=list)
    conversion = Column(JSONB, nullable=True)

    __table_args__ = (
        UniqueConstraint("line_item_id", "rank", name="uq_candidate_line_rank"),
    )

    line_item = relationship("LineItem", back_populates="candidates")
    product = relationship("CatalogProduct", foreign_keys=[sku])


class ReviewDecision(Base):
    __tablename__ = "review_decisions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    line_item_id = Column(
        UUID(as_uuid=True),
        ForeignKey("rfq_line_items.id"),
        nullable=False,
    )
    decision_type = Column(String(20), nullable=False)
    sku = Column(String(32), ForeignKey("catalog_products.sku"), nullable=True)
    quantity = Column(Numeric(14, 3), nullable=True)
    unit = Column(String(32), nullable=True)
    note = Column(Text, nullable=True)
    overrode_system = Column(Boolean, nullable=False)
    system_outcome_snapshot = Column(String(20), nullable=False)
    reason_codes_snapshot = Column(JSONB, nullable=False, default=list)
    status_before = Column(String(20), nullable=False)
    status_after = Column(String(20), nullable=False)
    version_before = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint(
            "decision_type IN ('approve', 'correct', 'reject', 'confirm_no_match')",
            name="ck_decision_type",
        ),
        CheckConstraint(
            "status_before IN ('pending', 'approved', 'corrected', 'rejected', 'no_match')",
            name="ck_status_before",
        ),
        CheckConstraint(
            "status_after IN ('pending', 'approved', 'corrected', 'rejected', 'no_match')",
            name="ck_status_after",
        ),
    )

    line_item = relationship("LineItem", back_populates="decisions")
    product = relationship("CatalogProduct", foreign_keys=[sku])
