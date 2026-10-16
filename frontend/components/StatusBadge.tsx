import React from 'react';
import { ReviewStatus, SystemOutcome } from '../lib/types';

interface SystemOutcomeBadgeProps {
  outcome: SystemOutcome;
  className?: string;
}

export function SystemOutcomeBadge({ outcome, className = '' }: SystemOutcomeBadgeProps) {
  let label = '';
  let icon = '';
  let borderClass = '';
  let bgClass = '';
  let textClass = '';

  switch (outcome) {
    case 'proposed':
      label = 'Suggested: needs approval';
      icon = '◇';
      borderClass = 'border-2 border-dashed border-blue-600 rounded-md';
      bgClass = 'bg-blue-50';
      textClass = 'text-blue-900';
      break;
    case 'ambiguous':
      label = 'Ambiguous: choose or reject';
      icon = '⚠';
      borderClass = 'border-2 border-dotted border-amber-600 rounded-lg';
      bgClass = 'bg-amber-50';
      textClass = 'text-amber-900';
      break;
    case 'unmatched':
      label = 'Unmatched';
      icon = '∅';
      borderClass = 'border border-solid border-gray-500 rounded-full';
      bgClass = 'bg-gray-100';
      textClass = 'text-gray-900';
      break;
  }

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium tracking-wide ${borderClass} ${bgClass} ${textClass} ${className}`}
      data-testid={`outcome-badge-${outcome}`}
      role="status"
    >
      <span aria-hidden="true" className="font-bold text-sm">
        {icon}
      </span>
      <span>{label}</span>
    </span>
  );
}

interface ReviewStatusBadgeProps {
  status: ReviewStatus;
  className?: string;
}

export function ReviewStatusBadge({ status, className = '' }: ReviewStatusBadgeProps) {
  let label = '';
  let icon = '';
  let borderClass = '';
  let bgClass = '';
  let textClass = '';

  switch (status) {
    case 'pending':
      label = 'Pending review';
      icon = '⏳';
      borderClass = 'border border-dashed border-gray-400 rounded';
      bgClass = 'bg-gray-50';
      textClass = 'text-gray-800';
      break;
    case 'approved':
      label = 'Approved';
      icon = '✓';
      borderClass = 'border-2 border-solid border-emerald-600 rounded-md';
      bgClass = 'bg-emerald-50';
      textClass = 'text-emerald-950 font-semibold';
      break;
    case 'corrected':
      label = 'Corrected';
      icon = '✓✎';
      borderClass = 'border-2 border-solid border-indigo-600 rounded-md';
      bgClass = 'bg-indigo-50';
      textClass = 'text-indigo-950 font-semibold';
      break;
    case 'rejected':
      label = 'Rejected';
      icon = '✕';
      borderClass = 'border-2 border-solid border-rose-600 rounded-sm';
      bgClass = 'bg-rose-50';
      textClass = 'text-rose-950 font-semibold';
      break;
    case 'no_match':
      label = 'Confirmed no match';
      icon = '∅✓';
      borderClass = 'border-2 border-solid border-purple-600 rounded-full';
      bgClass = 'bg-purple-50';
      textClass = 'text-purple-950 font-semibold';
      break;
  }

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-xs tracking-wide ${borderClass} ${bgClass} ${textClass} ${className}`}
      data-testid={`status-badge-${status}`}
      role="status"
    >
      <span aria-hidden="true" className="font-bold">
        {icon}
      </span>
      <span>{label}</span>
    </span>
  );
}
