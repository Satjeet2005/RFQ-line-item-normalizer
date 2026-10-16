"""0001_initial

Revision ID: 0001_initial
Revises: 
Create Date: 2026-10-16 18:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0001_initial'
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

def upgrade() -> None:
    op.create_table(
        'rfqs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(length=80), nullable=False),
        sa.Column('source_type', sa.String(length=10), nullable=False),
        sa.Column('catalog_version', sa.String(length=64), nullable=False),
        sa.Column('matching_config_hash', sa.String(length=64), nullable=False),
        sa.Column('skipped_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("source_type IN ('paste', 'csv')", name='ck_rfq_source_type'),
    )

    op.create_table(
        'catalog_products',
        sa.Column('sku', sa.String(length=32), primary_key=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('category', sa.String(length=64), nullable=False),
        sa.Column('uom', sa.String(length=32), nullable=False),
        sa.Column('attributes', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('aliases', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    )

    op.create_table(
        'rfq_line_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('rfq_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('rfqs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('line_no', sa.Integer(), nullable=False),
        sa.Column('source_row', sa.Integer(), nullable=False),
        sa.Column('raw_input', sa.String(length=2000), nullable=False),
        sa.Column('description_raw', sa.Text(), nullable=False),
        sa.Column('quantity_raw', sa.Text(), nullable=True),
        sa.Column('unit_raw', sa.Text(), nullable=True),
        sa.Column('description_normalized', sa.Text(), nullable=False),
        sa.Column('spec', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('quantity', sa.Numeric(precision=14, scale=3), nullable=True),
        sa.Column('unit', sa.String(length=32), nullable=True),
        sa.Column('unit_dimension', sa.String(length=32), nullable=True),
        sa.Column('issues', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('system_outcome', sa.String(length=20), nullable=False),
        sa.Column('reason_codes', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('review_status', sa.String(length=20), server_default='pending', nullable=False),
        sa.Column('final_sku', sa.String(length=32), sa.ForeignKey('catalog_products.sku'), nullable=True),
        sa.Column('final_quantity', sa.Numeric(precision=14, scale=3), nullable=True),
        sa.Column('final_unit', sa.String(length=32), nullable=True),
        sa.Column('version', sa.Integer(), server_default='1', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('rfq_id', 'line_no', name='uq_rfq_line_no'),
        sa.CheckConstraint("system_outcome IN ('proposed', 'ambiguous', 'unmatched')", name='ck_system_outcome'),
        sa.CheckConstraint("review_status IN ('pending', 'approved', 'corrected', 'rejected', 'no_match')", name='ck_review_status'),
        sa.CheckConstraint(
            "((review_status IN ('approved', 'corrected') AND final_sku IS NOT NULL AND final_quantity IS NOT NULL AND final_unit IS NOT NULL) OR "
            "(review_status NOT IN ('approved', 'corrected') AND final_sku IS NULL AND final_quantity IS NULL AND final_unit IS NULL))",
            name='ck_final_fields_iff_finalized',
        ),
    )

    op.create_table(
        'candidate_matches',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('line_item_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('rfq_line_items.id', ondelete='CASCADE'), nullable=False),
        sa.Column('rank', sa.Integer(), nullable=False),
        sa.Column('sku', sa.String(length=32), sa.ForeignKey('catalog_products.sku'), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('uom', sa.String(length=32), nullable=False),
        sa.Column('attributes', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('similarity', sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column('disqualified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('flags', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('conversion', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.UniqueConstraint('line_item_id', 'rank', name='uq_candidate_line_rank'),
    )

    op.create_table(
        'review_decisions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('line_item_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('rfq_line_items.id'), nullable=False),
        sa.Column('decision_type', sa.String(length=20), nullable=False),
        sa.Column('sku', sa.String(length=32), sa.ForeignKey('catalog_products.sku'), nullable=True),
        sa.Column('quantity', sa.Numeric(precision=14, scale=3), nullable=True),
        sa.Column('unit', sa.String(length=32), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('overrode_system', sa.Boolean(), nullable=False),
        sa.Column('system_outcome_snapshot', sa.String(length=20), nullable=False),
        sa.Column('reason_codes_snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('status_before', sa.String(length=20), nullable=False),
        sa.Column('status_after', sa.String(length=20), nullable=False),
        sa.Column('version_before', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("decision_type IN ('approve', 'correct', 'reject', 'confirm_no_match')", name='ck_decision_type'),
        sa.CheckConstraint("status_before IN ('pending', 'approved', 'corrected', 'rejected', 'no_match')", name='ck_status_before'),
        sa.CheckConstraint("status_after IN ('pending', 'approved', 'corrected', 'rejected', 'no_match')", name='ck_status_after'),
    )

def downgrade() -> None:
    op.drop_table('review_decisions')
    op.drop_table('candidate_matches')
    op.drop_table('rfq_line_items')
    op.drop_table('catalog_products')
    op.drop_table('rfqs')
