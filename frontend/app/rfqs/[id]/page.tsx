'use client';

import React, { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
import { getRFQ, listLineItems, downloadExport, APIClientError } from '../../../lib/api';
import { LineItem, RFQ, ReviewStatus, SystemOutcome } from '../../../lib/types';
import { ReviewStatusBadge, SystemOutcomeBadge } from '../../../components/StatusBadge';

export default function RFQDetailPage() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const rfqId = params.id as string;

  // Read filters from URL search params (persisted in URL!)
  const initialStatus = (searchParams.get('status') as ReviewStatus | 'all') || 'pending';
  const initialOutcome = (searchParams.get('outcome') as SystemOutcome | 'all') || 'all';

  const [statusFilter, setStatusFilter] = useState<ReviewStatus | 'all'>(initialStatus);
  const [outcomeFilter, setOutcomeFilter] = useState<SystemOutcome | 'all'>(initialOutcome);

  const [rfq, setRfq] = useState<RFQ | null>(null);
  const [items, setItems] = useState<LineItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<{ message: string; requestId?: string } | null>(null);

  // Incomplete export modal state
  const [showIncompleteModal, setShowIncompleteModal] = useState(false);
  const [pendingCountForModal, setPendingCountForModal] = useState(0);
  const [exportFormatPending, setExportFormatPending] = useState<'csv' | 'json'>('csv');
  const [exporting, setExporting] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [rfqData, itemsData] = await Promise.all([
        getRFQ(rfqId),
        listLineItems(rfqId, statusFilter, outcomeFilter, 200, 0),
      ]);
      setRfq(rfqData.rfq);
      setItems(itemsData.items);
    } catch (err) {
      if (err instanceof APIClientError) {
        setError({ message: err.message, requestId: err.requestId });
      } else {
        setError({ message: 'Failed to load RFQ data', requestId: '' });
      }
    } finally {
      setLoading(false);
    }
  }, [rfqId, statusFilter, outcomeFilter]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const updateFilters = (newStatus: ReviewStatus | 'all', newOutcome: SystemOutcome | 'all') => {
    setStatusFilter(newStatus);
    setOutcomeFilter(newOutcome);
    const params = new URLSearchParams();
    if (newStatus !== 'pending') params.set('status', newStatus);
    if (newOutcome !== 'all') params.set('outcome', newOutcome);
    router.replace(`/rfqs/${rfqId}${params.toString() ? `?${params.toString()}` : ''}`);
  };

  const handleExport = async (format: 'csv' | 'json', allowIncomplete: boolean = false) => {
    setExporting(true);
    try {
      const { blob, filename } = await downloadExport(rfqId, format, allowIncomplete);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      setShowIncompleteModal(false);
    } catch (err) {
      if (err instanceof APIClientError && err.code === 'RFQ_INCOMPLETE') {
        const pendingDetail = err.details?.find((d) => d.code === 'PENDING_LINES') as { pending_count?: number } | undefined;
        setPendingCountForModal(typeof pendingDetail?.pending_count === 'number' ? pendingDetail.pending_count : 1);
        setExportFormatPending(format);
        setShowIncompleteModal(true);
      } else if (err instanceof APIClientError) {
        alert(`Export failed: ${err.message} (${err.code})`);
      } else {
        alert('Export failed. Please try again.');
      }
    } finally {
      setExporting(false);
    }
  };

  // Find next pending item
  const nextPendingItem = items.find((it) => it.review_status === 'pending');

  return (
    <div className="space-y-6">
      {/* Header */}
      {rfq && (
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <div className="flex items-center gap-3">
                <h1 className="text-2xl font-bold text-gray-900">{rfq.name}</h1>
                <span className="inline-flex items-center px-2.5 py-0.5 rounded text-xs font-semibold bg-gray-100 text-gray-800 uppercase">
                  {rfq.source_type}
                </span>
                {rfq.counts?.complete ? (
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-green-100 text-green-800 border border-green-200">
                    ✓ Complete
                  </span>
                ) : (
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-800 border border-amber-200">
                    ⏳ Incomplete
                  </span>
                )}
              </div>
              <div className="mt-1 flex flex-wrap items-center gap-x-4 text-xs text-gray-500">
                <span>Created {new Date(rfq.created_at).toLocaleString()}</span>
                <span>•</span>
                <span>Total Items: {rfq.counts?.total_lines ?? 0}</span>
                <span>•</span>
                <span>Catalog: {rfq.catalog_version}</span>
              </div>
            </div>

            {/* Top action buttons: Next Pending & Export */}
            <div className="flex flex-wrap items-center gap-3">
              {nextPendingItem && (
                <Link
                  href={`/rfqs/${rfqId}/items/${nextPendingItem.id}`}
                  className="inline-flex items-center justify-center px-4 py-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                >
                  Next Pending Line →
                </Link>
              )}
              <div className="relative inline-flex rounded-md shadow-sm">
                <button
                  type="button"
                  onClick={() => handleExport('csv', false)}
                  disabled={exporting}
                  className="inline-flex items-center px-3.5 py-2 border border-gray-300 rounded-l-md bg-white text-sm font-medium text-gray-700 hover:bg-gray-50 focus:z-10 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                >
                  Export CSV
                </button>
                <button
                  type="button"
                  onClick={() => handleExport('json', false)}
                  disabled={exporting}
                  className="-ml-px inline-flex items-center px-3.5 py-2 border border-gray-300 rounded-r-md bg-white text-sm font-medium text-gray-700 hover:bg-gray-50 focus:z-10 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                >
                  JSON
                </button>
              </div>
            </div>
          </div>

          {/* Skipped lines banner */}
          {rfq.skipped_count > 0 && (
            <div
              className="rounded-md bg-amber-50 p-3 border border-amber-200 text-xs text-amber-900 flex items-center justify-between"
              role="alert"
            >
              <span>
                <strong>Import Note:</strong> {rfq.skipped_count} invalid line(s) were skipped during creation and not saved.
              </span>
            </div>
          )}

          {/* Counts breakdown summary */}
          <div className="pt-4 border-t border-gray-100 grid grid-cols-2 sm:grid-cols-5 gap-3 text-center">
            <div className="bg-gray-50 p-2.5 rounded border border-gray-200">
              <div className="text-xs text-gray-500 font-medium">Pending</div>
              <div className="text-lg font-bold text-gray-900">{rfq.counts?.by_review_status?.pending ?? 0}</div>
            </div>
            <div className="bg-emerald-50 p-2.5 rounded border border-emerald-200">
              <div className="text-xs text-emerald-800 font-medium">Approved</div>
              <div className="text-lg font-bold text-emerald-950">{rfq.counts?.by_review_status?.approved ?? 0}</div>
            </div>
            <div className="bg-indigo-50 p-2.5 rounded border border-indigo-200">
              <div className="text-xs text-indigo-800 font-medium">Corrected</div>
              <div className="text-lg font-bold text-indigo-950">{rfq.counts?.by_review_status?.corrected ?? 0}</div>
            </div>
            <div className="bg-rose-50 p-2.5 rounded border border-rose-200">
              <div className="text-xs text-rose-800 font-medium">Rejected</div>
              <div className="text-lg font-bold text-rose-950">{rfq.counts?.by_review_status?.rejected ?? 0}</div>
            </div>
            <div className="bg-purple-50 p-2.5 rounded border border-purple-200">
              <div className="text-xs text-purple-800 font-medium">No Match</div>
              <div className="text-lg font-bold text-purple-950">{rfq.counts?.by_review_status?.no_match ?? 0}</div>
            </div>
          </div>
        </div>
      )}

      {/* Filter Toolbar */}
      <div className="bg-white p-4 rounded-lg border border-gray-200 shadow-sm flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-2">
            <label htmlFor="filter-status" className="text-xs font-semibold text-gray-700">
              Review Status:
            </label>
            <select
              id="filter-status"
              value={statusFilter}
              onChange={(e) => updateFilters(e.target.value as ReviewStatus | 'all', outcomeFilter)}
              className="text-xs border border-gray-300 rounded px-2.5 py-1.5 focus:border-blue-500 focus:ring-blue-500 bg-white"
            >
              <option value="pending">Pending (default queue)</option>
              <option value="all">All statuses</option>
              <option value="approved">Approved</option>
              <option value="corrected">Corrected</option>
              <option value="rejected">Rejected</option>
              <option value="no_match">No match</option>
            </select>
          </div>

          <div className="flex items-center gap-2">
            <label htmlFor="filter-outcome" className="text-xs font-semibold text-gray-700">
              System Outcome:
            </label>
            <select
              id="filter-outcome"
              value={outcomeFilter}
              onChange={(e) => updateFilters(statusFilter, e.target.value as SystemOutcome | 'all')}
              className="text-xs border border-gray-300 rounded px-2.5 py-1.5 focus:border-blue-500 focus:ring-blue-500 bg-white"
            >
              <option value="all">All outcomes</option>
              <option value="proposed">Suggested</option>
              <option value="ambiguous">Ambiguous</option>
              <option value="unmatched">Unmatched</option>
            </select>
          </div>
        </div>

        <div className="text-xs text-gray-500">
          Showing <strong>{items.length}</strong> line item{items.length !== 1 ? 's' : ''}
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="rounded-md bg-red-50 p-4 border border-red-200" role="alert" aria-live="polite">
          <h3 className="text-sm font-semibold text-red-800">Error: {error.message}</h3>
          {error.requestId && (
            <p className="mt-1 text-xs text-red-600 font-mono">Request ID: {error.requestId}</p>
          )}
          <button
            type="button"
            onClick={loadData}
            className="mt-2 text-xs font-semibold text-red-800 underline hover:text-red-900"
          >
            Retry
          </button>
        </div>
      )}

      {/* Loading state */}
      {loading && (
        <div className="space-y-3" role="status" aria-label="Loading lines">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-16 bg-white border border-gray-200 rounded-md animate-pulse"></div>
          ))}
          <span className="sr-only">Loading lines...</span>
        </div>
      )}

      {/* Empty state */}
      {!loading && !error && items.length === 0 && (
        <div className="text-center py-12 bg-white rounded-lg border border-gray-200 p-8">
          <p className="text-sm font-medium text-gray-700">No lines match these filters.</p>
          <button
            type="button"
            onClick={() => updateFilters('all', 'all')}
            className="mt-3 text-xs font-semibold text-blue-600 hover:underline"
          >
            Clear filters
          </button>
        </div>
      )}

      {/* Line items: Desktop Table (hidden < 768px), Mobile Stacked Cards (block < 768px) */}
      {!loading && !error && items.length > 0 && (
        <>
          {/* Desktop Table */}
          <div className="hidden md:block overflow-x-auto bg-white border border-gray-200 rounded-lg shadow-sm">
            <table className="min-w-full divide-y divide-gray-200 text-xs">
              <thead className="bg-gray-50 text-gray-700 font-semibold uppercase tracking-wider">
                <tr>
                  <th scope="col" className="px-3 py-3 text-left w-12">#</th>
                  <th scope="col" className="px-3 py-3 text-left">Original Description</th>
                  <th scope="col" className="px-3 py-3 text-left">Normalized Description</th>
                  <th scope="col" className="px-3 py-3 text-left">Qty / Unit</th>
                  <th scope="col" className="px-3 py-3 text-left">System Outcome</th>
                  <th scope="col" className="px-3 py-3 text-left">Review Status</th>
                  <th scope="col" className="px-3 py-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 bg-white">
                {items.map((item) => (
                  <tr key={item.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-3 py-3.5 font-mono text-gray-500 font-semibold">{item.line_no}</td>
                    <td className="px-3 py-3.5 font-medium text-gray-900 max-w-xs break-words">
                      {item.description_raw}
                    </td>
                    <td className="px-3 py-3.5 text-gray-600 font-mono max-w-xs break-words">
                      {item.description_normalized}
                      {item.issues.length > 0 && (
                        <div className="mt-1 flex flex-wrap gap-1">
                          {item.issues.map((iss, i) => (
                            <span
                              key={i}
                              className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${
                                iss.severity === 'blocking'
                                  ? 'bg-red-100 text-red-800'
                                  : 'bg-yellow-100 text-yellow-800'
                              }`}
                              title={iss.detail}
                            >
                              {iss.code}
                            </span>
                          ))}
                        </div>
                      )}
                    </td>
                    <td className="px-3 py-3.5 text-gray-700 whitespace-nowrap">
                      {item.quantity !== null && item.quantity !== undefined ? (
                        <span>
                          <strong>{item.quantity}</strong> {item.unit || ''}
                        </span>
                      ) : (
                        <span className="text-gray-400 italic">None</span>
                      )}
                    </td>
                    <td className="px-3 py-3.5 whitespace-nowrap">
                      <SystemOutcomeBadge outcome={item.system_outcome} />
                    </td>
                    <td className="px-3 py-3.5 whitespace-nowrap">
                      <ReviewStatusBadge status={item.review_status} />
                    </td>
                    <td className="px-3 py-3.5 text-right whitespace-nowrap">
                      <Link
                        href={`/rfqs/${rfqId}/items/${item.id}`}
                        className="inline-flex items-center px-2.5 py-1 border border-gray-300 rounded text-xs font-semibold text-blue-600 bg-white hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      >
                        Review →
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Mobile Stacked Cards (< 768px) */}
          <div className="md:hidden space-y-4">
            {items.map((item) => (
              <div
                key={item.id}
                className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm space-y-3"
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs font-bold text-gray-500">
                    Line #{item.line_no}
                  </span>
                  <ReviewStatusBadge status={item.review_status} />
                </div>
                <div>
                  <div className="text-xs text-gray-500 uppercase font-semibold">Original:</div>
                  <div className="text-sm font-medium text-gray-900 break-words">
                    {item.description_raw}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-gray-500 uppercase font-semibold">Normalized:</div>
                  <div className="text-xs font-mono text-gray-700 break-words">
                    {item.description_normalized}
                  </div>
                </div>
                <div className="flex items-center justify-between text-xs pt-2 border-t border-gray-100">
                  <div>
                    <span className="text-gray-500">Qty: </span>
                    <span className="font-semibold text-gray-800">
                      {item.quantity ?? 'None'} {item.unit ?? ''}
                    </span>
                  </div>
                  <div>
                    <SystemOutcomeBadge outcome={item.system_outcome} />
                  </div>
                </div>
                <div className="pt-2">
                  <Link
                    href={`/rfqs/${rfqId}/items/${item.id}`}
                    className="block w-full text-center py-2 px-3 border border-gray-300 rounded-md text-xs font-semibold text-blue-600 bg-blue-50 hover:bg-blue-100"
                  >
                    Review Line Item →
                  </Link>
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {/* Incomplete Export Modal per PRD Section F */}
      {showIncompleteModal && (
        <div
          className="fixed inset-0 z-50 overflow-y-auto bg-gray-500 bg-opacity-75 flex items-center justify-center p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="incomplete-modal-title"
        >
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6 space-y-4">
            <div className="flex items-center gap-3">
              <span className="text-amber-600 text-2xl font-bold" aria-hidden="true">
                ⚠
              </span>
              <h3 id="incomplete-modal-title" className="text-lg font-bold text-gray-900">
                RFQ Is Incomplete
              </h3>
            </div>
            <p className="text-sm text-gray-600">
              This RFQ has <strong>{pendingCountForModal}</strong> pending line item{pendingCountForModal !== 1 ? 's' : ''}.
              By default, incomplete RFQs cannot be exported unless you explicitly choose to export only finalized lines.
            </p>
            <div className="flex items-center justify-end gap-3 pt-4 border-t border-gray-200">
              <button
                type="button"
                onClick={() => setShowIncompleteModal(false)}
                className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={exporting}
                onClick={() => handleExport(exportFormatPending, true)}
                className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {exporting ? 'Exporting...' : 'Export Finalized Lines Only'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
