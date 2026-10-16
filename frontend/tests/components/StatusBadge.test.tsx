import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import { ReviewStatusBadge, SystemOutcomeBadge } from '../../components/StatusBadge';
import { ReviewStatus, SystemOutcome } from '../../lib/types';

describe('StatusBadge accessibility & visual rules (Checklist P1 U2)', () => {
  const outcomes: Array<{ outcome: SystemOutcome; text: string; icon: string }> = [
    { outcome: 'proposed', text: 'Suggested: needs approval', icon: '◇' },
    { outcome: 'ambiguous', text: 'Ambiguous: choose or reject', icon: '⚠' },
    { outcome: 'unmatched', text: 'Unmatched', icon: '∅' },
  ];

  outcomes.forEach(({ outcome, text, icon }) => {
    it(`renders outcome '${outcome}' with text '${text}' and icon '${icon}'`, () => {
      render(<SystemOutcomeBadge outcome={outcome} />);
      const el = screen.getByTestId(`outcome-badge-${outcome}`);
      expect(el).toHaveTextContent(text);
      expect(el).toHaveTextContent(icon);
    });
  });

  const statuses: Array<{ status: ReviewStatus; text: string; icon: string }> = [
    { status: 'pending', text: 'Pending review', icon: '⏳' },
    { status: 'approved', text: 'Approved', icon: '✓' },
    { status: 'corrected', text: 'Corrected', icon: '✓✎' },
    { status: 'rejected', text: 'Rejected', icon: '✕' },
    { status: 'no_match', text: 'Confirmed no match', icon: '∅✓' },
  ];

  statuses.forEach(({ status, text, icon }) => {
    it(`renders status '${status}' with text '${text}' and icon '${icon}'`, () => {
      render(<ReviewStatusBadge status={status} />);
      const el = screen.getByTestId(`status-badge-${status}`);
      expect(el).toHaveTextContent(text);
      expect(el).toHaveTextContent(icon);
    });
  });
});
