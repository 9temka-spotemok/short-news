import { render, screen, fireEvent } from '@testing-library/react'
import { vi, describe, it, expect } from 'vitest'

import { withQueryClient } from '@/test/utils'
import type { Company } from '@/types'
import { AnalyticsTabs } from '../AnalyticsTabs'

vi.mock('../../PersistentMetricsBoard', () => ({
  PersistentMetricsBoard: ({ selectedCompany }: { selectedCompany: { name: string } }) => (
    <div data-testid="persistent-board">{selectedCompany?.name}</div>
  ),
}))

vi.mock('../../CurrentSignalsBoard', () => ({
  CurrentSignalsBoard: ({ selectedCompany }: { selectedCompany: { name: string } }) => (
    <div data-testid="signals-board">{selectedCompany?.name} signals</div>
  ),
}))

vi.mock('../../ChangeEventsSection', () => ({
  ChangeEventsSection: () => <div data-testid="change-events" />,
}))

vi.mock('../../hooks/useChangeLog', () => ({
  useChangeLog: () => ({
    data: { pages: [{ events: [] }] },
    isLoading: false,
    error: null,
    hasNextPage: false,
    refetch: vi.fn(),
    fetchNextPage: vi.fn(),
    isFetchingNextPage: false,
  }),
}))

vi.mock('../../hooks/useKnowledgeGraph', () => ({
  useKnowledgeGraph: () => ({
    data: [],
    isLoading: false,
    error: null,
  }),
}))

const defaultCompany: Company = {
  id: 'c1',
  name: 'Acme',
  website: '',
  description: '',
  logo_url: '',
  category: '',
  twitter_handle: '',
  github_org: '',
  created_at: '',
  updated_at: '',
}

const baseProps = {
  metricsTab: 'persistent' as const,
  onTabChange: vi.fn(),
  selectedCompany: defaultCompany,
  analysisData: { metrics: {} },
  themesData: {},
  comparisonData: null,
  comparisonPeriod: 'daily' as const,
  comparisonLookback: 30,
  comparisonLoading: false,
  comparisonError: null,
  subjectColorMap: new Map<string, string>(),
  impactSnapshot: null,
  impactSeries: null,
  focusedImpactPoint: null,
  onComparisonPeriodChange: vi.fn(),
  onComparisonLookbackChange: vi.fn(),
  onSnapshotHover: vi.fn(),
  filtersSnapshot: { topics: [], sentiments: [], source_types: [], min_priority: null },
  comparisonSubjects: [],
  analyticsEdges: [],
  reportPresets: [],
  pendingPresetId: '',
  onPendingPresetChange: vi.fn(),
  onAddPresetToComparison: vi.fn(),
  abSelection: { left: null, right: null },
  onAbSelectionChange: vi.fn(),
  changeEvents: [],
  changeEventsLoading: false,
  changeEventsError: null,
  onRefreshChangeEvents: vi.fn(),
  onRecomputeChangeEvent: vi.fn(),
  recomputingEventId: null,
}

describe('AnalyticsTabs', () => {
  it('renders persistent metrics tab by default', () => {
    render(withQueryClient(<AnalyticsTabs {...baseProps} />))

    expect(screen.getByTestId('persistent-board')).toHaveTextContent('Acme')
    expect(screen.queryByTestId('signals-board')).not.toBeInTheDocument()
  })

  it('switches to signals tab on click', () => {
    const handleTabChange = vi.fn()
    render(withQueryClient(<AnalyticsTabs {...baseProps} onTabChange={handleTabChange} />))

    const signalsTab = screen.getByRole('button', { name: /current signals/i })
    fireEvent.click(signalsTab)

    expect(handleTabChange).toHaveBeenCalledWith('signals')
  })

  it('renders signals tab content when metricsTab=signals', () => {
    render(withQueryClient(<AnalyticsTabs {...baseProps} metricsTab="signals" />))

    expect(screen.getByTestId('signals-board')).toHaveTextContent('Acme signals')
    expect(screen.getByTestId('change-events')).toBeInTheDocument()
  })
})
