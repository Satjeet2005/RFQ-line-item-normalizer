'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { listRFQs, APIClientError } from '../lib/api';
import { RFQ } from '../lib/types';

export default function RFQListPage() {
  const [rfqs, setRfqs] = useState<RFQ[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<{ message: string; requestId: string } | null>(null);

  const fetchRFQs = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listRFQs(50, 0);
      setRfqs(data.items);
    } catch (err) {
      if (err instanceof APIClientError) {
        setError({ message: err.message, requestId: err.requestId });
      } else {
        setError({ message: 'Failed to load RFQs', requestId: '' });
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRFQs();
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-gray-200 pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-gray-900">RFQs</h1>
          <p className="mt-1 text-sm text-gray-500">
            Select an RFQ to view line item normalization, candidates, and review decisions.
          </p>
        </div>
        <div>
          <Link
            href="/rfqs/new"
            className="inline-flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            + Import New RFQ
          </Link>
        </div>
      </div>

      {/* Loading state */}
      {loading && (
        <div className="space-y-4" role="status" aria-label="Loading RFQs">
          {[1, 2, 3].map((i) => (
            <div key={i} className="bg-white p-6 rounded-lg border border-gray-200 animate-pulse space-y-3">
              <div className="h-5 bg-gray-200 rounded w-1/4"></div>
              <div className="h-4 bg-gray-100 rounded w-1/2"></div>
              <div className="h-6 bg-gray-100 rounded w-1/3"></div>
            </div>
          ))}
          <span className="sr-only">Loading RFQs...</span>
        </div>
      )}

      {/* Error state */}
      {!loading && error && (
        <div
          className="rounded-md bg-red-50 p-4 border border-red-200"
          role="alert"
          aria-live="polite"
        >
          <div className="flex">
            <div className="flex-shrink-0">
              <span className="text-red-500 font-bold">✕</span>
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">Error loading RFQs</h3>
              <div className="mt-1 text-sm text-red-700">{error.message}</div>
              {error.requestId && (
                <div className="mt-1 text-xs text-red-600 font-mono">
                  Request ID: {error.requestId}
                </div>
              )}
              <div className="mt-3">
                <button
                  type="button"
                  onClick={fetchRFQs}
                  className="rounded-md bg-red-100 px-3 py-1.5 text-xs font-medium text-red-800 hover:bg-red-200 focus:outline-none focus:ring-2 focus:ring-red-500"
                >
                  Retry
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Empty state */}
      {!loading && !error && rfqs.length === 0 && (
        <div className="text-center py-16 bg-white rounded-lg border-2 border-dashed border-gray-300 p-12">
          <span className="text-4xl text-gray-400 block mb-2" aria-hidden="true">
            📋
          </span>
          <h3 className="mt-2 text-base font-semibold text-gray-900">No RFQs found</h3>
          <p className="mt-1 text-sm text-gray-500">
            Get started by importing an RFQ from pasted text or a CSV file.
          </p>
          <div className="mt-6">
            <Link
              href="/rfqs/new"
              className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              + Create First RFQ
            </Link>
          </div>
        </div>
      )}

      {/* List */}
      {!loading && !error && rfqs.length > 0 && (
        <div className="space-y-4">
          {rfqs.map((rfq) => {
            const counts = rfq.counts;
            const isComplete = counts?.complete ?? false;
            const totalLines = counts?.total_lines ?? 0;
            const pendingCount = counts?.by_review_status?.pending ?? 0;
            const approvedCount = counts?.by_review_status?.approved ?? 0;
            const correctedCount = counts?.by_review_status?.corrected ?? 0;
            const rejectedCount = counts?.by_review_status?.rejected ?? 0;
            const noMatchCount = counts?.by_review_status?.no_match ?? 0;

            return (
              <div
                key={rfq.id}
                className="bg-white rounded-lg border border-gray-200 hover:border-gray-300 shadow-sm p-6 transition-all"
              >
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-3">
                      <h2 className="text-lg font-bold text-gray-900">
                        <Link
                          href={`/rfqs/${rfq.id}`}
                          className="hover:text-blue-600 focus:outline-none focus:underline"
                        >
                          {rfq.name}
                        </Link>
                      </h2>
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-800 uppercase tracking-wider">
                        {rfq.source_type}
                      </span>
                      {isComplete ? (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-green-100 text-green-800 border border-green-200">
                          ✓ Complete
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-800 border border-amber-200">
                          ⏳ {pendingCount} Pending
                        </span>
                      )}
                    </div>
                    <div className="mt-1 flex flex-wrap items-center gap-x-4 text-xs text-gray-500">
                      <span>Created {new Date(rfq.created_at).toLocaleString()}</span>
                      <span>•</span>
                      <span>Total Lines: {totalLines}</span>
                      {rfq.skipped_count > 0 && (
                        <>
                          <span>•</span>
                          <span className="text-amber-700 font-medium">
                            {rfq.skipped_count} lines skipped on import
                          </span>
                        </>
                      )}
                    </div>
                  </div>
                  <div>
                    <Link
                      href={`/rfqs/${rfq.id}`}
                      className="inline-flex items-center justify-center px-3.5 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                    >
                      Review RFQ →
                    </Link>
                  </div>
                </div>

                {/* Status counts breakdown */}
                <div className="mt-4 pt-4 border-t border-gray-100 flex flex-wrap items-center gap-2 text-xs">
                  <span className="text-gray-500 font-medium mr-1">Status breakdown:</span>
                  <span className="px-2 py-0.5 bg-gray-100 rounded text-gray-700">
                    Pending: <strong>{pendingCount}</strong>
                  </span>
                  <span className="px-2 py-0.5 bg-emerald-100 text-emerald-900 rounded font-medium">
                    Approved: <strong>{approvedCount}</strong>
                  </span>
                  <span className="px-2 py-0.5 bg-indigo-100 text-indigo-900 rounded font-medium">
                    Corrected: <strong>{correctedCount}</strong>
                  </span>
                  <span className="px-2 py-0.5 bg-rose-100 text-rose-900 rounded font-medium">
                    Rejected: <strong>{rejectedCount}</strong>
                  </span>
                  <span className="px-2 py-0.5 bg-purple-100 text-purple-900 rounded font-medium">
                    No Match: <strong>{noMatchCount}</strong>
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
