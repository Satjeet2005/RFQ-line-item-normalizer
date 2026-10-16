import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import React from 'react';
import LineItemReviewPage from '../../app/rfqs/[id]/items/[itemId]/page';
import * as api from '../../lib/api';
import axe from 'axe-core';

vi.mock('next/navigation', () => ({
  useParams: () => ({ id: 'mock-rfq-1', itemId: 'mock-item-1' }),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}));

describe('Item Review Screen (Checklist P0 R7, P1 U1, P1 U3, P1 U7)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders ambiguous line with NO preselected candidate and NO Suggested label (Checklist P0 R7)', async () => {
    vi.spyOn(api, 'getLineItem').mockResolvedValueOnce({
      id: 'mock-item-1',
      rfq_id: 'mock-rfq-1',
      line_no: 1,
      source_row: 1,
      raw_input: 'GI pipe 25mm 100 mtr',
      description_raw: 'GI pipe 25mm',
      description_normalized: 'gi pipe 25mm',
      spec: {},
      quantity: 100,
      unit: 'mtr',
      issues: [],
      system_outcome: 'ambiguous', // Ambiguous!
      reason_codes: ['SPEC_MISSING_DISCRIMINATOR'],
      review_status: 'pending',
      version: 1,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      candidates: [
        {
          id: 'c1',
          rank: 1,
          sku: 'PIPE-001',
          name: 'GI Pipe 25mm Class A',
          uom: 'mtr',
          attributes: {},
          similarity: 0.85,
          disqualified: false,
          flags: [],
        },
        {
          id: 'c2',
          rank: 2,
          sku: 'PIPE-002',
          name: 'GI Pipe 25mm Class B',
          uom: 'mtr',
          attributes: {},
          similarity: 0.85,
          disqualified: false,
          flags: [],
        },
      ],
      decisions: [],
    });

    vi.spyOn(api, 'listLineItems').mockResolvedValueOnce({ items: [], total: 0 });

    const { container } = render(<LineItemReviewPage />);

    await waitFor(() => {
      expect(screen.getByText('Line Item #1')).toBeInTheDocument();
    });

    // Check: NO "Suggested" label anywhere on ambiguous lines
    expect(screen.queryByText('Suggested')).toBeNull();

    // Check: Radio buttons are NOT checked
    const radios = screen.getAllByRole('radio');
    expect(radios.length).toBe(2);
    expect(radios[0]).not.toBeChecked();
    expect(radios[1]).not.toBeChecked();

    // Check: "Approve Selected" button is DISABLED
    const approveBtn = screen.getByRole('button', { name: /approve selected/i });
    expect(approveBtn).toBeDisabled();

    // Check: Similarity tooltip and label (Checklist P1 U7)
    const simElements = screen.getAllByTitle('Text similarity, not a probability or confirmation.');
    expect(simElements.length).toBe(2);
    expect(simElements[0]).toHaveTextContent('similarity');

    // Accessibility check: axe on the rendered page
    const axeResult = await axe.run(container, {
      rules: {
        // disable rules that require real full-page environment if needed
        'color-contrast': { enabled: true },
      },
    });
    const severeViolations = axeResult.violations.filter(
      (v) => v.impact === 'serious' || v.impact === 'critical'
    );
    expect(severeViolations).toHaveLength(0);
  });
});
