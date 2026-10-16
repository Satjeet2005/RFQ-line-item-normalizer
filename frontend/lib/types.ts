export type SourceType = 'paste' | 'csv';
export type SystemOutcome = 'proposed' | 'ambiguous' | 'unmatched';
export type ReviewStatus = 'pending' | 'approved' | 'corrected' | 'rejected' | 'no_match';
export type DecisionType = 'approve' | 'correct' | 'reject' | 'confirm_no_match';

export interface RFQSummaryCounts {
  by_review_status: Record<ReviewStatus, number>;
  by_system_outcome: Record<SystemOutcome, number>;
  total_lines: number;
  complete: boolean;
}

export interface RFQ {
  id: string;
  name: string;
  source_type: SourceType;
  catalog_version: string;
  matching_config_hash: string;
  skipped_count: number;
  created_at: string;
  counts?: RFQSummaryCounts;
}

export interface CandidateMatch {
  id: string;
  rank: number;
  sku: string;
  name: string;
  uom: string;
  attributes: Record<string, string>;
  similarity: number;
  disqualified: boolean;
  flags: string[];
  conversion?: {
    from_unit: string;
    to_uom: string;
    quantity_in_uom: number;
  } | null;
}

export interface ReviewDecision {
  id: string;
  line_item_id: string;
  decision_type: DecisionType;
  sku?: string | null;
  quantity?: number | null;
  unit?: string | null;
  note?: string | null;
  overrode_system: boolean;
  system_outcome_snapshot: SystemOutcome;
  reason_codes_snapshot: string[];
  status_before: ReviewStatus;
  status_after: ReviewStatus;
  version_before: number;
  created_at: string;
}

export interface NormalizationIssue {
  code: string;
  severity: 'blocking' | 'info';
  detail: string;
}

export interface LineItem {
  id: string;
  rfq_id: string;
  line_no: number;
  source_row: number;
  raw_input: string;
  description_raw: string;
  quantity_raw?: string | null;
  unit_raw?: string | null;
  description_normalized: string;
  spec: Record<string, string>;
  quantity?: number | null;
  unit?: string | null;
  unit_dimension?: string | null;
  issues: NormalizationIssue[];
  system_outcome: SystemOutcome;
  reason_codes: string[];
  review_status: ReviewStatus;
  final_sku?: string | null;
  final_quantity?: number | null;
  final_unit?: string | null;
  version: number;
  created_at: string;
  updated_at: string;
  candidates: CandidateMatch[];
}

export interface LineItemDetail extends LineItem {
  decisions: ReviewDecision[];
}

export interface SkippedRow {
  row: number;
  code: string;
  message: string;
  raw: string;
}

export interface RFQCreateResponse {
  rfq: RFQ;
  items_summary: {
    total_lines: number;
    by_system_outcome: Record<string, number>;
    skipped_lines: number;
    warnings: string[];
  };
  skipped: SkippedRow[];
}

export interface CatalogProduct {
  sku: string;
  name: string;
  category: string;
  uom: string;
  attributes: Record<string, string>;
  aliases: string[];
}

export interface APIErrorResponse {
  error: {
    code: string;
    message: string;
    details: Array<{ field?: string; code?: string; message: string; [key: string]: unknown }>;
    request_id: string;
  };
  item?: LineItem;
}
