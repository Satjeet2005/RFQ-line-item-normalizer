'use client';

import React, { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { getLineItem, listLineItems, makeDecision, searchCatalog, APIClientError } from '../../../../../lib/api';
import { CatalogProduct, DecisionType, LineItem, LineItemDetail } from '../../../../../lib/types';
import { ReviewStatusBadge, SystemOutcomeBadge } from '../../../../../components/StatusBadge';

export default function LineItemReviewPage() {
  const params = useParams();
  const rfqId = params.id as string;
  const itemId = params.itemId as string;

  const [item, setItem] = useState<LineItemDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<{ code: string; message: string; requestId?: string } | null>(null);
  const [staleVersionItem, setStaleVersionItem] = useState<LineItem | null>(null);

  // Form states
  const [selectedCandidateSku, setSelectedCandidateSku] = useState<string>('');
  const [overrideQuantity, setOverrideQuantity] = useState<string>('');
  const [overrideUnit, setOverrideUnit] = useState<string>('');
  const [note, setNote] = useState<string>('');

  // Catalog search state for corrections
  const [catalogQuery, setCatalogQuery] = useState('');
  const [catalogResults, setCatalogResults] = useState<CatalogProduct[]>([]);
  const [selectedCorrectionProduct, setSelectedCorrectionProduct] = useState<CatalogProduct | null>(null);
  const [searchingCatalog, setSearchingCatalog] = useState(false);

  // Next pending item ID
  const [nextPendingId, setNextPendingId] = useState<string | null>(null);

  const loadItem = useCallback(async () => {
    setLoading(true);
    setError(null);
    setStaleVersionItem(null);
    try {
      const itemData = await getLineItem(rfqId, itemId);
      setItem(itemData);

      // Invariant: For proposed lines, preselect top candidate.
      // For ambiguous or unmatched lines, do NOT preselect any candidate!
      if (itemData.system_outcome === 'proposed' && itemData.candidates.length > 0) {
        setSelectedCandidateSku(itemData.candidates[0].sku);
      } else {
        setSelectedCandidateSku('');
      }

      // Prefill quantity and unit
      setOverrideQuantity(itemData.quantity !== null && itemData.quantity !== undefined ? itemData.quantity.toString() : '');
      setOverrideUnit(itemData.unit || '');
      setNote('');

      // Find next pending line in RFQ
      const listRes = await listLineItems(rfqId, 'pending', 'all', 200, 0);
      const nextPending = listRes.items.find((it) => it.id !== itemId);
      setNextPendingId(nextPending ? nextPending.id : null);
    } catch (err) {
      if (err instanceof APIClientError) {
        setError({ code: err.code, message: err.message, requestId: err.requestId });
      } else {
        setError({ code: 'LOAD_ERROR', message: 'Failed to load line item.' });
      }
    } finally {
      setLoading(false);
    }
  }, [rfqId, itemId]);

  useEffect(() => {
    loadItem();
  }, [loadItem]);

  // Handle Catalog Search
  useEffect(() => {
    if (!catalogQuery.trim()) {
      setCatalogResults([]);
      return;
    }
    const timer = setTimeout(async () => {
      setSearchingCatalog(true);
      try {
        const res = await searchCatalog(catalogQuery.trim(), 10);
        setCatalogResults(res.items);
      } catch {
        // search failure
      } finally {
        setSearchingCatalog(false);
      }
    }, 250);
    return () => clearTimeout(timer);
  }, [catalogQuery]);

  const handleDecision = async (decisionType: DecisionType) => {
    if (!item) return;
    setSubmitting(true);
    setError(null);
    setStaleVersionItem(null);

    let chosenSku: string | null = null;
    if (decisionType === 'approve') {
      if (!selectedCandidateSku) {
        setError({
          code: 'SELECTION_REQUIRED',
          message: 'Please select a candidate product to approve.',
        });
        setSubmitting(false);
        return;
      }
      chosenSku = selectedCandidateSku;
    } else if (decisionType === 'correct') {
      if (!selectedCorrectionProduct) {
        setError({
          code: 'PRODUCT_REQUIRED',
          message: 'Please search and select a catalog product to correct to.',
        });
        setSubmitting(false);
        return;
      }
      chosenSku = selectedCorrectionProduct.sku;
    } else if (decisionType === 'reject') {
      if (!note.trim() || note.trim().length < 3) {
        setError({
          code: 'NOTE_REQUIRED',
          message: 'A note of at least 3 characters is required to reject.',
        });
        setSubmitting(false);
        return;
      }
    }

    try {
      await makeDecision(rfqId, itemId, {
        decision_type: decisionType,
        expected_version: item.version,
        sku: chosenSku,
        quantity: overrideQuantity.trim() ? overrideQuantity.trim() : null,
        unit: overrideUnit.trim() ? overrideUnit.trim() : null,
        note: note.trim() ? note.trim() : null,
      });

      // Reload item to reflect update
      await loadItem();
    } catch (err) {
      if (err instanceof APIClientError) {
        if (err.code === 'STALE_VERSION') {
          setStaleVersionItem(err.item || null);
          setError({
            code: err.code,
            message: 'This line item was modified concurrently by another decision.',
            requestId: err.requestId,
          });
        } else {
          setError({
            code: err.code,
            message: err.message,
            requestId: err.requestId,
          });
        }
      } else {
        setError({
          code: 'SUBMISSION_ERROR',
          message: 'Failed to record decision.',
        });
      }
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-4" role="status" aria-label="Loading item details">
        <div className="h-8 bg-gray-200 rounded w-1/4 animate-pulse"></div>
        <div className="h-40 bg-white border border-gray-200 rounded-md animate-pulse"></div>
        <span className="sr-only">Loading item details...</span>
      </div>
    );
  }

  if (error && !item) {
    return (
      <div className="rounded-md bg-red-50 p-6 border border-red-200 text-center">
        <h3 className="text-base font-semibold text-red-800">Error: {error.message}</h3>
        <p className="mt-2">
          <Link href={`/rfqs/${rfqId}`} className="text-sm font-semibold text-blue-600 underline">
            ← Back to RFQ
          </Link>
        </p>
      </div>
    );
  }

  if (!item) return null;

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Breadcrumb & Navigation */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-gray-200 pb-4">
        <div className="flex items-center gap-2 text-sm text-gray-600">
          <Link href={`/rfqs/${rfqId}`} className="text-blue-600 hover:underline font-medium">
            ← Back to RFQ Lines
          </Link>
          <span>/</span>
          <span className="font-bold text-gray-900">Line Item #{item.line_no}</span>
        </div>
        <div className="flex items-center gap-3">
          <ReviewStatusBadge status={item.review_status} />
          {nextPendingId && (
            <Link
              href={`/rfqs/${rfqId}/items/${nextPendingId}`}
              className="inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-semibold rounded shadow-sm text-white bg-blue-600 hover:bg-blue-700"
            >
              Next Pending Line →
            </Link>
          )}
        </div>
      </div>

      {/* 409 STALE_VERSION Banner */}
      {staleVersionItem && (
        <div
          className="rounded-md bg-amber-100 p-4 border-2 border-amber-400"
          role="alert"
          aria-live="assertive"
        >
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-amber-900">
                ⚠ This line was modified elsewhere (Stale Version Conflict)
              </h3>
              <p className="mt-1 text-xs text-amber-800">
                Another user or window updated this line item (current version: {staleVersionItem.version}).
                Please reload to view current data before deciding.
              </p>
            </div>
            <button
              type="button"
              onClick={loadItem}
              className="px-3.5 py-1.5 bg-amber-800 text-white rounded text-xs font-semibold hover:bg-amber-900 focus:outline-none focus:ring-2 focus:ring-amber-500"
            >
              Reload Item
            </button>
          </div>
        </div>
      )}

      {/* General Error Banner */}
      {error && !staleVersionItem && (
        <div className="rounded-md bg-red-50 p-4 border border-red-200" role="alert" aria-live="polite">
          <div className="flex">
            <span className="text-red-500 font-bold mr-2">✕</span>
            <div>
              <h3 className="text-sm font-bold text-red-800">{error.code}: {error.message}</h3>
              {error.requestId && (
                <p className="mt-1 text-xs text-red-600 font-mono">Request ID: {error.requestId}</p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Raw Input vs Normalized Comparison */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Raw Input Block */}
        <div className="bg-white border border-gray-200 rounded-lg p-5 shadow-sm space-y-2">
          <div className="text-xs font-bold text-gray-500 uppercase tracking-wider">
            Raw Input (Exact Byte-for-Byte)
          </div>
          <div className="p-3 bg-gray-50 rounded border border-gray-200 font-mono text-sm text-gray-900 whitespace-pre-wrap break-all">
            {item.raw_input}
          </div>
          <div className="text-xs text-gray-500">
            Source Row: <strong>{item.source_row}</strong>
          </div>
        </div>

        {/* Normalized Block */}
        <div className="bg-white border border-gray-200 rounded-lg p-5 shadow-sm space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-gray-500 uppercase tracking-wider">
              Normalized Output
            </span>
            <SystemOutcomeBadge outcome={item.system_outcome} />
          </div>

          <div>
            <span className="text-xs text-gray-500">Description:</span>
            <div className="p-2.5 bg-blue-50/50 rounded border border-blue-200 font-mono text-sm text-gray-900 font-medium">
              {item.description_normalized}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2 text-xs">
            <div>
              <span className="text-gray-500">Extracted Quantity:</span>
              <div className="font-semibold text-gray-800">
                {item.quantity !== null && item.quantity !== undefined ? item.quantity : <span className="italic text-gray-400">Missing</span>}
              </div>
            </div>
            <div>
              <span className="text-gray-500">Canonical Unit:</span>
              <div className="font-semibold text-gray-800">
                {item.unit || <span className="italic text-gray-400">Missing</span>}
              </div>
            </div>
          </div>

          {/* Normalization Issues */}
          {item.issues.length > 0 && (
            <div className="pt-2 border-t border-gray-100">
              <span className="text-xs font-bold text-gray-700 block mb-1">Detected Issues:</span>
              <div className="flex flex-wrap gap-1.5">
                {item.issues.map((iss, i) => (
                  <span
                    key={i}
                    className={`px-2 py-0.5 rounded text-xs font-medium border ${
                      iss.severity === 'blocking'
                        ? 'bg-red-50 text-red-900 border-red-200'
                        : 'bg-yellow-50 text-yellow-900 border-yellow-200'
                    }`}
                  >
                    <strong>{iss.code}</strong>: {iss.detail}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Abstention Reasons */}
          {item.reason_codes.length > 0 && (
            <div className="pt-2 border-t border-gray-100">
              <span className="text-xs font-bold text-gray-700 block mb-1">
                System Abstention Reasons:
              </span>
              <ul className="list-disc list-inside text-xs text-amber-900 space-y-0.5">
                {item.reason_codes.map((rc, idx) => (
                  <li key={idx} className="font-mono">
                    {rc}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>

      {/* Candidate Matches Section */}
      <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm space-y-4">
        <div className="flex items-center justify-between border-b border-gray-200 pb-3">
          <div>
            <h2 className="text-base font-bold text-gray-900">
              Catalog Candidates ({item.candidates.length} Listed)
            </h2>
            <p className="text-xs text-gray-500">
              {item.system_outcome === 'proposed'
                ? 'System suggested top candidate. Approval required.'
                : 'Ambiguous or unmatched line: choose explicitly or correct below.'}
            </p>
          </div>
        </div>

        {item.candidates.length === 0 ? (
          <div className="py-8 text-center text-sm text-gray-500 italic bg-gray-50 rounded border border-dashed border-gray-200">
            No candidate found in catalog meeting similarity threshold.
          </div>
        ) : (
          <fieldset className="space-y-3" aria-label="Candidate products">
            <legend className="sr-only">Candidate matches for approval</legend>
            {item.candidates.map((cand, idx) => {
              const isSuggested = item.system_outcome === 'proposed' && idx === 0;
              const isSelected = selectedCandidateSku === cand.sku;

              return (
                <label
                  key={cand.id}
                  className={`block p-4 rounded-lg border-2 cursor-pointer transition-all ${
                    isSelected
                      ? 'border-blue-600 bg-blue-50/40 ring-1 ring-blue-500'
                      : 'border-gray-200 hover:border-gray-300 bg-white'
                  }`}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-start gap-3">
                      <input
                        type="radio"
                        name="candidate_selection"
                        value={cand.sku}
                        checked={isSelected}
                        onChange={() => setSelectedCandidateSku(cand.sku)}
                        className="mt-1 h-4 w-4 text-blue-600 border-gray-300 focus:ring-blue-500"
                      />
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-mono font-bold text-sm text-gray-900">
                            {cand.sku}
                          </span>
                          <span className="text-sm font-semibold text-gray-800">
                            {cand.name}
                          </span>
                          {/* Checklist P0 R7 & PRD Section F: 'Suggested' badge ONLY on proposed top candidate */}
                          {isSuggested && (
                            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-bold bg-blue-100 text-blue-800 border border-blue-300">
                              Suggested
                            </span>
                          )}
                        </div>

                        <div className="mt-1 flex flex-wrap items-center gap-x-4 text-xs text-gray-500">
                          <span>UOM: <strong>{cand.uom}</strong></span>
                          {cand.attributes && Object.keys(cand.attributes).length > 0 && (
                            <span>
                              Attrs: {Object.entries(cand.attributes).map(([k, v]) => `${k}=${v}`).join(', ')}
                            </span>
                          )}
                          {cand.conversion && (
                            <span className="text-indigo-700 font-medium">
                              Converted: {cand.conversion.quantity_in_uom} {cand.conversion.to_uom}
                            </span>
                          )}
                        </div>

                        {/* Flags and Conflicts */}
                        {cand.flags && cand.flags.length > 0 && (
                          <div className="mt-2 flex flex-wrap gap-1">
                            {cand.flags.map((flag, fIdx) => (
                              <span
                                key={fIdx}
                                className="px-1.5 py-0.5 rounded text-[11px] font-semibold bg-rose-100 text-rose-800 border border-rose-200"
                              >
                                {flag}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Similarity Score with Tooltip per PRD Section F */}
                    <div className="text-right flex-shrink-0">
                      <div
                        className="inline-block text-xs font-semibold px-2 py-1 rounded bg-gray-100 text-gray-800 cursor-help"
                        title="Text similarity, not a probability or confirmation."
                      >
                        {cand.similarity.toFixed(4)} <span className="font-normal text-gray-600">similarity</span>
                      </div>
                    </div>
                  </div>
                </label>
              );
            })}
          </fieldset>
        )}
      </div>

      {/* Decision Panel & Catalog Search Correction */}
      <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm space-y-6">
        <h2 className="text-base font-bold text-gray-900 border-b border-gray-200 pb-3">
          Review Decision & Overrides
        </h2>

        {/* Override / Supply Missing Quantity & Unit */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label htmlFor="effective-quantity" className="block text-xs font-bold text-gray-700 mb-1">
              Effective Quantity (Required for Approve / Correct)
            </label>
            <input
              type="text"
              id="effective-quantity"
              value={overrideQuantity}
              onChange={(e) => setOverrideQuantity(e.target.value)}
              placeholder="e.g. 50"
              className="w-full text-sm rounded border border-gray-300 p-2 focus:border-blue-500 focus:ring-blue-500"
            />
          </div>
          <div>
            <label htmlFor="effective-unit" className="block text-xs font-bold text-gray-700 mb-1">
              Effective Unit (Required for Approve / Correct)
            </label>
            <input
              type="text"
              id="effective-unit"
              value={overrideUnit}
              onChange={(e) => setOverrideUnit(e.target.value)}
              placeholder="e.g. mtr, nos, kg"
              className="w-full text-sm rounded border border-gray-300 p-2 focus:border-blue-500 focus:ring-blue-500"
            />
          </div>
        </div>

        {/* Catalog Search for Corrections */}
        <div className="p-4 bg-gray-50 rounded-lg border border-gray-200 space-y-3">
          <label htmlFor="catalog-search" className="block text-xs font-bold text-gray-800">
            Correct to another catalog product (Search):
          </label>
          <input
            type="text"
            id="catalog-search"
            value={catalogQuery}
            onChange={(e) => setCatalogQuery(e.target.value)}
            placeholder="Type SKU or name (e.g. PIPE-002, Valve, Bolt)..."
            className="w-full text-sm rounded border border-gray-300 p-2 bg-white focus:border-blue-500 focus:ring-blue-500"
          />

          {searchingCatalog && <p className="text-xs text-gray-500">Searching catalog...</p>}

          {catalogResults.length > 0 && (
            <div className="max-h-48 overflow-y-auto border border-gray-200 rounded bg-white divide-y divide-gray-100 text-xs">
              {catalogResults.map((prod) => (
                <div
                  key={prod.sku}
                  onClick={() => setSelectedCorrectionProduct(prod)}
                  className={`p-2.5 cursor-pointer flex items-center justify-between hover:bg-blue-50 ${
                    selectedCorrectionProduct?.sku === prod.sku ? 'bg-blue-100 font-semibold' : ''
                  }`}
                >
                  <div>
                    <span className="font-mono font-bold mr-2 text-blue-900">{prod.sku}</span>
                    <span>{prod.name}</span>
                  </div>
                  <span className="text-gray-500 font-mono">{prod.uom}</span>
                </div>
              ))}
            </div>
          )}

          {selectedCorrectionProduct && (
            <div className="p-2 bg-indigo-50 border border-indigo-200 rounded text-xs text-indigo-900 flex items-center justify-between">
              <span>
                Selected for correction: <strong>{selectedCorrectionProduct.sku}</strong> — {selectedCorrectionProduct.name}
              </span>
              <button
                type="button"
                onClick={() => setSelectedCorrectionProduct(null)}
                className="text-xs font-bold text-rose-700 hover:underline"
              >
                Clear
              </button>
            </div>
          )}
        </div>

        {/* Rejection Note */}
        <div>
          <label htmlFor="decision-note" className="block text-xs font-bold text-gray-700 mb-1">
            Note (Required for Reject, 3–500 chars):
          </label>
          <textarea
            id="decision-note"
            rows={2}
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Reason for rejection or review comment..."
            className="w-full text-sm rounded border border-gray-300 p-2 focus:border-blue-500 focus:ring-blue-500"
            maxLength={500}
          />
        </div>

        {/* Four Decision Action Buttons per PRD Section F */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 pt-3 border-t border-gray-200">
          {/* 1. Approve */}
          <button
            type="button"
            disabled={submitting || !selectedCandidateSku}
            onClick={() => handleDecision('approve')}
            className="w-full py-2.5 px-3 rounded-md shadow-sm text-xs font-bold text-white bg-emerald-600 hover:bg-emerald-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            ✓ Approve Selected
          </button>

          {/* 2. Correct */}
          <button
            type="button"
            disabled={submitting || !selectedCorrectionProduct}
            onClick={() => handleDecision('correct')}
            className="w-full py-2.5 px-3 rounded-md shadow-sm text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            ✓✎ Correct to Product
          </button>

          {/* 3. Reject */}
          <button
            type="button"
            disabled={submitting || !note.trim() || note.trim().length < 3}
            onClick={() => handleDecision('reject')}
            className="w-full py-2.5 px-3 rounded-md shadow-sm text-xs font-bold text-white bg-rose-600 hover:bg-rose-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-rose-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            ✕ Reject
          </button>

          {/* 4. Confirm No Match */}
          <button
            type="button"
            disabled={submitting}
            onClick={() => handleDecision('confirm_no_match')}
            className="w-full py-2.5 px-3 rounded-md shadow-sm text-xs font-bold text-gray-800 bg-gray-100 hover:bg-gray-200 border border-gray-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500 disabled:opacity-50"
          >
            ∅✓ Confirm No Match
          </button>
        </div>
      </div>

      {/* Decision History Audit Trail */}
      <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm space-y-4">
        <h3 className="text-sm font-bold text-gray-900 border-b border-gray-200 pb-2">
          Decision History & Audit Trail (Append-Only)
        </h3>

        {item.decisions.length === 0 ? (
          <p className="text-xs text-gray-500 italic">No decisions recorded yet.</p>
        ) : (
          <div className="flow-root">
            <ul className="-mb-8">
              {item.decisions.map((dec, dIdx) => (
                <li key={dec.id}>
                  <div className="relative pb-8">
                    {dIdx !== item.decisions.length - 1 && (
                      <span
                        className="absolute top-4 left-4 -ml-px h-full w-0.5 bg-gray-200"
                        aria-hidden="true"
                      />
                    )}
                    <div className="relative flex space-x-3">
                      <div>
                        <span className="h-8 w-8 rounded-full bg-blue-100 text-blue-800 flex items-center justify-center ring-4 ring-white text-xs font-bold font-mono">
                          v{dec.version_before}
                        </span>
                      </div>
                      <div className="min-w-0 flex-1 pt-1.5 flex justify-between space-x-4">
                        <div>
                          <p className="text-xs font-semibold text-gray-900">
                            Decision: <span className="uppercase text-blue-700">{dec.decision_type}</span>{' '}
                            <span className="font-normal text-gray-500">
                              ({dec.status_before} → {dec.status_after})
                            </span>
                            {dec.overrode_system && (
                              <span className="ml-2 inline-flex items-center px-1.5 py-0.2 rounded text-[10px] font-bold bg-amber-100 text-amber-900">
                                Overrode System
                              </span>
                            )}
                          </p>
                          {dec.sku && (
                            <p className="mt-0.5 text-xs text-gray-700">
                              Confirmed SKU: <strong>{dec.sku}</strong> | Qty: {dec.quantity} {dec.unit}
                            </p>
                          )}
                          {dec.note && (
                            <p className="mt-1 text-xs text-gray-600 bg-gray-50 p-2 rounded border border-gray-100">
                              &ldquo;{dec.note}&rdquo;
                            </p>
                          )}
                        </div>
                        <div className="text-right text-xs whitespace-nowrap text-gray-500">
                          {new Date(dec.created_at).toLocaleString()}
                        </div>
                      </div>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
