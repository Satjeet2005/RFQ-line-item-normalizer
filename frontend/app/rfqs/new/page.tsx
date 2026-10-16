'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { createRFQ, APIClientError } from '../../../lib/api';
import { SourceType } from '../../../lib/types';

const SAMPLE_PASTE = `# Bundled Synthetic RFQ Sample
GI Pipe 25mm Class B 100 mtr
Brass ball valve 1 inch | 10 | nos
MS hex bolt M12 x 50 100 nos
PVC pipe 50mm 20 mtr
Welding electrodes 3.15mm 25 kg
PTFE Teflon tape 12mm 50 roll
`;

export default function NewRFQPage() {
  const router = useRouter();
  const [name, setName] = useState('');
  const [sourceType, setSourceType] = useState<SourceType>('paste');
  const [content, setContent] = useState('');
  const [fileName, setFileName] = useState('');
  const [loading, setLoading] = useState(false);
  const [fileError, setFileError] = useState<{ code: string; message: string; requestId?: string } | null>(null);
  const [rowErrors, setRowErrors] = useState<Array<{ row: number; code: string; message: string; raw: string }>>([]);

  const handleLoadSample = () => {
    setName('Sample Procurement Order');
    setSourceType('paste');
    setContent(SAMPLE_PASTE);
    setFileError(null);
    setRowErrors([]);
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.name.endsWith('.csv')) {
      setFileError({
        code: 'INVALID_FILE_TYPE',
        message: 'Only .csv files are supported. Please select a valid CSV file.',
      });
      return;
    }

    setFileName(file.name);
    setFileError(null);
    setRowErrors([]);

    const reader = new FileReader();
    reader.onload = (event) => {
      const text = event.target?.result as string;
      setContent(text);
      if (!name) {
        const defaultName = file.name.replace(/\.csv$/i, '');
        setName(defaultName.slice(0, 80));
      }
    };
    reader.onerror = () => {
      setFileError({
        code: 'FILE_READ_ERROR',
        message: 'Failed to read the selected file.',
      });
    };
    reader.readAsText(file, 'utf-8');
  };

  const handleSubmit = async (skipInvalid: boolean = false) => {
    const trimmedName = name.trim();
    if (!trimmedName) {
      setFileError({
        code: 'VALIDATION_ERROR',
        message: 'RFQ Name is required (1-80 characters).',
      });
      return;
    }
    if (trimmedName.length > 80) {
      setFileError({
        code: 'VALIDATION_ERROR',
        message: 'RFQ Name cannot exceed 80 characters.',
      });
      return;
    }
    if (!content.trim()) {
      setFileError({
        code: 'EMPTY_CONTENT',
        message: 'Please provide pasted lines or upload a CSV file with content.',
      });
      return;
    }

    setLoading(true);
    setFileError(null);
    if (!skipInvalid) setRowErrors([]);

    try {
      const res = await createRFQ(trimmedName, sourceType, content, skipInvalid);
      router.push(`/rfqs/${res.rfq.id}`);
    } catch (err) {
      if (err instanceof APIClientError) {
        if (err.code === 'ROW_ERRORS') {
          setRowErrors((err.details as unknown as Array<{ row: number; code: string; message: string; raw: string }>) || []);
          setFileError({
            code: err.code,
            message: err.message,
            requestId: err.requestId,
          });
        } else {
          setFileError({
            code: err.code,
            message: err.message,
            requestId: err.requestId,
          });
          setRowErrors([]);
        }
      } else {
        setFileError({
          code: 'CLIENT_ERROR',
          message: 'An unexpected error occurred while submitting the RFQ.',
        });
      }
    } finally {
      setLoading(false);
    }
  };

  const totalInputLines = content
    .split('\n')
    .filter((l) => l.trim() && !l.trim().startsWith('#')).length;
  const validCount = Math.max(0, totalInputLines - rowErrors.length);

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="border-b border-gray-200 pb-5">
        <h1 className="text-2xl font-bold tracking-tight text-gray-900">Create New RFQ</h1>
        <p className="mt-1 text-sm text-gray-500">
          Import line items from pasted text or a standard CSV spreadsheet.
        </p>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6 space-y-6">
        {/* Name Input */}
        <div>
          <label htmlFor="rfq-name" className="block text-sm font-semibold text-gray-900">
            RFQ Name <span className="text-red-500">*</span>
          </label>
          <div className="mt-1">
            <input
              type="text"
              id="rfq-name"
              name="rfq-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Project Phase 2 Hardware & Piping"
              maxLength={80}
              className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm p-2.5 border"
              required
            />
          </div>
          <p className="mt-1 text-xs text-gray-500">
            Maximum 80 characters.
          </p>
        </div>

        {/* Source Type Tabs */}
        <div>
          <div className="flex border-b border-gray-200" role="tablist">
            <button
              type="button"
              role="tab"
              aria-selected={sourceType === 'paste'}
              onClick={() => {
                setSourceType('paste');
                setFileError(null);
                setRowErrors([]);
              }}
              className={`py-2 px-4 text-sm font-medium border-b-2 focus:outline-none ${
                sourceType === 'paste'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Paste Text
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={sourceType === 'csv'}
              onClick={() => {
                setSourceType('csv');
                setFileError(null);
                setRowErrors([]);
              }}
              className={`py-2 px-4 text-sm font-medium border-b-2 focus:outline-none ${
                sourceType === 'csv'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              CSV File
            </button>
          </div>

          <div className="mt-4">
            {sourceType === 'paste' ? (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <label htmlFor="pasted-content" className="block text-xs font-medium text-gray-700">
                    One line item per line. Delimit with pipe (<code className="bg-gray-100 px-1">|</code>) or tab, or write free text with trailing quantity.
                  </label>
                  <button
                    type="button"
                    onClick={handleLoadSample}
                    className="text-xs font-semibold text-blue-600 hover:text-blue-800 underline focus:outline-none"
                  >
                    Load Sample RFQ
                  </button>
                </div>
                <textarea
                  id="pasted-content"
                  rows={8}
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  placeholder={`GI pipe 25mm class B 100 mtr\nBrass ball valve 1 inch | 10 | nos\nMS hex bolt M12 x 50`}
                  className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 font-mono text-sm p-3 border"
                />
              </div>
            ) : (
              <div className="space-y-4">
                <div className="rounded-md bg-gray-50 p-4 border border-gray-200 text-xs text-gray-700 space-y-1">
                  <p className="font-semibold text-gray-900">CSV Requirements:</p>
                  <p>• Required columns: <code className="bg-gray-200 px-1">description</code>, <code className="bg-gray-200 px-1">quantity</code></p>
                  <p>• Optional columns: <code className="bg-gray-200 px-1">unit</code>, <code className="bg-gray-200 px-1">line_ref</code></p>
                  <p>• Encoding: UTF-8 (BOM supported), maximum 200 lines, 256 KB</p>
                </div>
                <div>
                  <label htmlFor="csv-upload" className="block text-sm font-medium text-gray-700 mb-1">
                    Upload CSV File
                  </label>
                  <input
                    type="file"
                    id="csv-upload"
                    accept=".csv,text/csv"
                    onChange={handleFileUpload}
                    className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 cursor-pointer"
                  />
                  {fileName && (
                    <p className="mt-2 text-xs text-green-700 font-medium">
                      ✓ Selected file: {fileName}
                    </p>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* File-Level Error Banner */}
        {fileError && fileError.code !== 'ROW_ERRORS' && (
          <div
            className="rounded-md bg-red-50 p-4 border border-red-200"
            role="alert"
            aria-live="polite"
          >
            <div className="flex">
              <span className="text-red-600 font-bold mr-2">✕</span>
              <div>
                <h3 className="text-sm font-semibold text-red-800">
                  {fileError.code}: {fileError.message}
                </h3>
                {fileError.requestId && (
                  <p className="mt-1 text-xs text-red-600 font-mono">
                    Request ID: {fileError.requestId}
                  </p>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Row Errors Table */}
        {rowErrors.length > 0 && (
          <div className="space-y-3" role="alert" aria-live="polite">
            <div className="rounded-md bg-amber-50 p-4 border border-amber-200">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-bold text-amber-900">
                    Row Errors Detected ({rowErrors.length} invalid line{rowErrors.length > 1 ? 's' : ''})
                  </h3>
                  <p className="mt-1 text-xs text-amber-800">
                    Atomic import failed. Nothing was saved. You can fix the errors above or choose to skip invalid rows.
                  </p>
                </div>
                <div>
                  <button
                    type="button"
                    disabled={loading || validCount === 0}
                    onClick={() => handleSubmit(true)}
                    className="inline-flex items-center px-3.5 py-1.5 border border-transparent text-xs font-semibold rounded shadow-sm text-white bg-amber-600 hover:bg-amber-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-amber-500 disabled:opacity-50"
                  >
                    Import {validCount} valid line{validCount !== 1 ? 's' : ''}, skip {rowErrors.length}
                  </button>
                </div>
              </div>
            </div>

            <div className="overflow-x-auto border border-gray-200 rounded-md">
              <table className="min-w-full divide-y divide-gray-200 text-xs">
                <thead className="bg-gray-50 text-gray-700 font-semibold">
                  <tr>
                    <th scope="col" className="px-3 py-2 text-left">Row #</th>
                    <th scope="col" className="px-3 py-2 text-left">Error Code</th>
                    <th scope="col" className="px-3 py-2 text-left">Message</th>
                    <th scope="col" className="px-3 py-2 text-left">Raw Input</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 bg-white">
                  {rowErrors.map((err, idx) => (
                    <tr key={idx} className="hover:bg-gray-50">
                      <td className="px-3 py-2 font-mono font-medium text-gray-900">{err.row}</td>
                      <td className="px-3 py-2 font-semibold text-rose-700">{err.code}</td>
                      <td className="px-3 py-2 text-gray-800">{err.message}</td>
                      <td className="px-3 py-2 font-mono text-gray-600 break-all">{err.raw}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex items-center justify-end gap-3 pt-4 border-t border-gray-200">
          <button
            type="button"
            onClick={() => {
              setName('');
              setContent('');
              setFileName('');
              setFileError(null);
              setRowErrors([]);
            }}
            className="px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            Clear
          </button>
          <button
            type="button"
            disabled={loading}
            aria-busy={loading}
            onClick={() => handleSubmit(false)}
            className="inline-flex items-center px-5 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
          >
            {loading ? 'Creating...' : 'Create RFQ'}
          </button>
        </div>
      </div>
    </div>
  );
}
