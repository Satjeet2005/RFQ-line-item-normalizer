import {
  APIErrorResponse,
  CatalogProduct,
  DecisionType,
  LineItem,
  LineItemDetail,
  RFQ,
  RFQCreateResponse,
  RFQSummaryCounts,
  ReviewDecision,
  ReviewStatus,
  SystemOutcome,
} from './types';

export class APIClientError extends Error {
  status: number;
  code: string;
  details: Array<{ field?: string; code?: string; message: string; [key: string]: unknown }>;
  requestId: string;
  item?: LineItem;

  constructor(status: number, errorData: APIErrorResponse) {
    super(errorData.error?.message || 'An error occurred');
    this.status = status;
    this.code = errorData.error?.code || 'UNKNOWN_ERROR';
    this.details = errorData.error?.details || [];
    this.requestId = errorData.error?.request_id || '';
    this.item = errorData.item;
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!res.ok) {
    let errorData: APIErrorResponse;
    try {
      errorData = await res.json();
    } catch {
      errorData = {
        error: {
          code: `HTTP_${res.status}`,
          message: res.statusText || 'Network request failed',
          details: [],
          request_id: res.headers.get('X-Request-ID') || '',
        },
      };
    }
    throw new APIClientError(res.status, errorData);
  }

  return res.json();
}

export async function createRFQ(
  name: string,
  sourceType: 'paste' | 'csv',
  content: string,
  skipInvalid: boolean = false
): Promise<RFQCreateResponse> {
  return request<RFQCreateResponse>('/api/v1/rfqs', {
    method: 'POST',
    body: JSON.stringify({
      name,
      source_type: sourceType,
      content,
      skip_invalid: skipInvalid,
    }),
  });
}

export async function listRFQs(
  limit: number = 50,
  offset: number = 0
): Promise<{ items: RFQ[]; total: number }> {
  return request<{ items: RFQ[]; total: number }>(`/api/v1/rfqs?limit=${limit}&offset=${offset}`);
}

export async function getRFQ(
  rfqId: string
): Promise<{ rfq: RFQ; counts: RFQSummaryCounts; complete: boolean }> {
  return request<{ rfq: RFQ; counts: RFQSummaryCounts; complete: boolean }>(`/api/v1/rfqs/${rfqId}`);
}

export async function listLineItems(
  rfqId: string,
  reviewStatus?: ReviewStatus | 'all',
  systemOutcome?: SystemOutcome | 'all',
  limit: number = 200,
  offset: number = 0
): Promise<{ items: LineItem[]; total: number }> {
  const params = new URLSearchParams();
  if (reviewStatus && reviewStatus !== 'all') params.append('review_status', reviewStatus);
  if (systemOutcome && systemOutcome !== 'all') params.append('system_outcome', systemOutcome);
  params.append('limit', limit.toString());
  params.append('offset', offset.toString());

  return request<{ items: LineItem[]; total: number }>(`/api/v1/rfqs/${rfqId}/items?${params.toString()}`);
}

export async function getLineItem(rfqId: string, itemId: string): Promise<LineItemDetail> {
  return request<LineItemDetail>(`/api/v1/rfqs/${rfqId}/items/${itemId}`);
}

export async function makeDecision(
  rfqId: string,
  itemId: string,
  decision: {
    decision_type: DecisionType;
    expected_version: number;
    sku?: string | null;
    quantity?: number | string | null;
    unit?: string | null;
    note?: string | null;
  }
): Promise<{ decision: ReviewDecision; item: LineItem }> {
  return request<{ decision: ReviewDecision; item: LineItem }>(`/api/v1/rfqs/${rfqId}/items/${itemId}/decisions`, {
    method: 'POST',
    body: JSON.stringify(decision),
  });
}

export async function searchCatalog(
  q: string,
  limit: number = 20
): Promise<{ items: CatalogProduct[]; total: number }> {
  return request<{ items: CatalogProduct[]; total: number }>(
    `/api/v1/catalog?q=${encodeURIComponent(q)}&limit=${limit}`
  );
}

export async function downloadExport(
  rfqId: string,
  format: 'csv' | 'json',
  allowIncomplete: boolean = false
): Promise<{ blob: Blob; filename: string; excludedCount: number }> {
  const res = await fetch(
    `/api/v1/rfqs/${rfqId}/export?format=${format}&allow_incomplete=${allowIncomplete}`
  );

  if (!res.ok) {
    let errorData: APIErrorResponse;
    try {
      errorData = await res.json();
    } catch {
      errorData = {
        error: {
          code: `HTTP_${res.status}`,
          message: 'Export failed',
          details: [],
          request_id: res.headers.get('X-Request-ID') || '',
        },
      };
    }
    throw new APIClientError(res.status, errorData);
  }

  const excludedCount = parseInt(res.headers.get('X-Items-Excluded') || '0', 10);
  const blob = await res.blob();
  const filename = format === 'csv' ? `rfq_${rfqId}_export.csv` : `rfq_${rfqId}_export.json`;

  return { blob, filename, excludedCount };
}
