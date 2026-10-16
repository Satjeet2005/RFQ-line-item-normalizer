import React from 'react';
import Link from 'next/link';

export function Navbar() {
  return (
    <header className="border-b border-gray-200 bg-white">
      {/* Synthetic Demo Banner per PRD Section N */}
      <div className="bg-amber-100 border-b border-amber-200 px-4 py-1.5 text-center text-xs text-amber-900 font-medium">
        Synthetic Demo Data. Do not enter real or proprietary procurement data.
      </div>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div className="flex items-center gap-8">
          <Link
            href="/"
            className="flex items-center gap-2 text-gray-900 font-bold text-lg hover:text-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 rounded px-1"
          >
            <span className="p-1.5 bg-blue-600 text-white rounded font-mono text-sm font-semibold">
              RFQ
            </span>
            <span>Line-Item Normalizer</span>
          </Link>
          <nav className="hidden sm:flex items-center gap-4" aria-label="Main navigation">
            <Link
              href="/"
              className="text-sm font-medium text-gray-700 hover:text-gray-900 px-3 py-2 rounded-md hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              All RFQs
            </Link>
            <Link
              href="/rfqs/new"
              className="text-sm font-medium text-gray-700 hover:text-gray-900 px-3 py-2 rounded-md hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              Import RFQ
            </Link>
          </nav>
        </div>
        <div>
          <Link
            href="/rfqs/new"
            className="inline-flex items-center justify-center px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 shadow-sm transition-colors"
          >
            + Create New RFQ
          </Link>
        </div>
      </div>
    </header>
  );
}
