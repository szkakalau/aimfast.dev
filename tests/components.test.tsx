import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import TrendCard from '@/app/trends/TrendCard';
import Pagination from '@/app/trends/Pagination';
import type { TrendTerm } from '@/app/trends/types';

const mockTerm: TrendTerm = {
  id: 'trend-test-term',
  canonical: 'Test Term',
  aliases: [],
  first_seen: '2026-07-01',
  last_seen: '2026-07-15',
  stage: 'emergent',
  score: 80,
  source_count: 5,
  total_mentions: 100,
  sources: ['Reddit', 'GitHub'],
  growth_pct: 50,
  category: 'DevTools',
  tags: ['test'],
  summary_zh: '一个测试趋势',
  summary_en: 'A test trend for unit testing.',
  research_md_path: 'content/trends/test-term.md',
};

describe('TrendCard', () => {
  it('renders canonical name as heading', () => {
    render(<TrendCard term={mockTerm} />);
    expect(screen.getByText('Test Term')).toBeInTheDocument();
  });

  it('renders summary text', () => {
    render(<TrendCard term={mockTerm} />);
    expect(screen.getByText('A test trend for unit testing.')).toBeInTheDocument();
  });

  it('renders stage badge', () => {
    render(<TrendCard term={mockTerm} />);
    expect(screen.getByText('Emergent (8-30d)')).toBeInTheDocument();
  });

  it('renders meta info', () => {
    render(<TrendCard term={mockTerm} />);
    expect(screen.getByText(/5 sources/)).toBeInTheDocument();
    expect(screen.getByText(/100 mentions/)).toBeInTheDocument();
  });

  it('renders builder signals when opportunity data exists', () => {
    const withOpp: TrendTerm = {
      ...mockTerm,
      estimated_dev_days: 7,
      suggested_products: ['Chrome Extension'],
      revenue_potential: 4,
    };
    render(<TrendCard term={withOpp} />);
    expect(screen.getByText('7d MVP')).toBeInTheDocument();
    expect(screen.getByText('Chrome Extension')).toBeInTheDocument();
  });

  it('does not render builder signals when no opportunity data', () => {
    render(<TrendCard term={mockTerm} />);
    expect(screen.queryByText('d MVP')).not.toBeInTheDocument();
  });

  it('links to correct trend detail page', () => {
    render(<TrendCard term={mockTerm} />);
    const link = screen.getByRole('link');
    expect(link).toHaveAttribute('href', '/trends/test-term/');
  });
});

describe('Pagination', () => {
  it('renders page numbers for multi-page result', () => {
    render(<Pagination page={1} totalPages={5} onPage={vi.fn()} />);
    expect(screen.getByText('1')).toBeInTheDocument();
    expect(screen.getByText('5')).toBeInTheDocument();
  });

  it('returns null for single page', () => {
    const { container } = render(<Pagination page={1} totalPages={1} onPage={vi.fn()} />);
    expect(container.firstChild).toBeNull();
  });

  it('disables previous button on first page', () => {
    render(<Pagination page={1} totalPages={5} onPage={vi.fn()} />);
    expect(screen.getByLabelText('Previous page')).toBeDisabled();
  });

  it('disables next button on last page', () => {
    render(<Pagination page={5} totalPages={5} onPage={vi.fn()} />);
    expect(screen.getByLabelText('Next page')).toBeDisabled();
  });
});
