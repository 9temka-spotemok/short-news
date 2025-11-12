import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'

import { CompanyAnalysisFlow } from '../CompanyAnalysisFlow'

vi.mock('@/components/CompanySelector', () => ({
  default: ({ onSelect }: { onSelect: (value: any) => void }) => (
    <button onClick={() => onSelect({ id: 'c1', name: 'Acme' })}>
      Mock Company Selector
    </button>
  ),
}))

vi.mock('../FiltersPanel', () => ({
  FiltersPanel: () => <div data-testid="filters-panel" />,
}))

vi.mock('../CompanyDeepDive', () => ({
  CompanyDeepDive: () => <div data-testid="company-deep-dive" />,
}))

vi.mock('../ActiveFiltersSummary', () => ({
  ActiveFiltersSummary: () => <div data-testid="filters-summary" />,
}))

const defaultProps = {
  selectedCompany: null,
  onSelectCompany: vi.fn(),
  onBack: vi.fn(),
  sourceTypeFilters: [],
  topicFilters: [],
  sentimentFilters: [],
  minPriorityFilter: null,
  hasActiveFilters: false,
  onToggleSourceType: vi.fn(),
  onToggleTopic: vi.fn(),
  onToggleSentiment: vi.fn(),
  onMinPriorityChange: vi.fn(),
  onClearFilters: vi.fn(),
  loading: false,
  onAnalyze: vi.fn(),
  analysisData: null,
  suggestedCompetitors: [],
  onExport: vi.fn(),
  filtersSnapshot: { topics: [], sentiments: [], source_types: [], min_priority: null },
}

describe('CompanyAnalysisFlow', () => {
  it('triggers company selection and analyze action', () => {
    const onSelectCompany = vi.fn()
    const onAnalyze = vi.fn()

    render(
      <CompanyAnalysisFlow
        {...defaultProps}
        onSelectCompany={onSelectCompany}
        onAnalyze={onAnalyze}
        selectedCompany={{ id: 'c1', name: 'Acme' }}
      />
    )

    fireEvent.click(screen.getByRole('button', { name: /analyze company/i }))
    expect(onAnalyze).toHaveBeenCalled()
  })

  it('renders analysis section when data is provided', () => {
    render(
      <CompanyAnalysisFlow
        {...defaultProps}
        selectedCompany={{ id: 'c1', name: 'Acme' }}
        analysisData={{}}
      />
    )

    expect(screen.getByTestId('filters-summary')).toBeInTheDocument()
    expect(screen.getByTestId('company-deep-dive')).toBeInTheDocument()
  })
})


