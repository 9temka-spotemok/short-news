import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'

import { PresetManager } from '../PresetManager'
import type { ReportPreset } from '@/types'

vi.mock('../../FiltersPanel', () => ({
  FiltersPanel: () => <div data-testid="filters-panel" />,
}))

vi.mock('../../ActiveFiltersSummary', () => ({
  ActiveFiltersSummary: () => <div data-testid="filters-summary" />,
}))

const filtersPanelProps = {
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
}

describe('PresetManager', () => {
  it('renders presets and triggers actions', () => {
    const presets: ReportPreset[] = [{
      id: 'p1',
      user_id: 'u1',
      name: 'Preset A',
      description: null,
      companies: ['c1'],
      filters: {},
      visualization_config: {},
      is_favorite: false,
      created_at: '',
      updated_at: '',
    }]
    const handleNameChange = vi.fn()
    const handleCreate = vi.fn()
    const handleApply = vi.fn()

    render(
      <PresetManager
        reportPresets={presets}
        presetsLoading={false}
        presetsError={null}
        newPresetName="Preset A"
        onPresetNameChange={handleNameChange}
        onCreatePreset={handleCreate}
        savingPreset={false}
        presetApplyingId={null}
        onApplyPreset={handleApply}
        filtersSnapshot={{ topics: [], sentiments: [], source_types: [], min_priority: null }}
        filtersPanelProps={filtersPanelProps}
      />
    )

    fireEvent.change(screen.getByPlaceholderText(/watch/i), { target: { value: 'Preset B' } })
    expect(handleNameChange).toHaveBeenCalledWith('Preset B')

    fireEvent.click(screen.getByRole('button', { name: /save preset/i }))
    expect(handleCreate).toHaveBeenCalled()

    fireEvent.click(screen.getByRole('button', { name: /apply/i }))
    expect(handleApply).toHaveBeenCalledWith(presets[0])

    expect(screen.getByTestId('filters-panel')).toBeInTheDocument()
    expect(screen.getByTestId('filters-summary')).toBeInTheDocument()
  })

  it('shows loading and error states', () => {
    const { rerender } = render(
      <PresetManager
        reportPresets={[]}
        presetsLoading
        presetsError={null}
        newPresetName=""
        onPresetNameChange={vi.fn()}
        onCreatePreset={vi.fn()}
        savingPreset={false}
        presetApplyingId={null}
        onApplyPreset={vi.fn()}
        filtersSnapshot={{ topics: [], sentiments: [], source_types: [], min_priority: null }}
        filtersPanelProps={filtersPanelProps}
      />
    )

    expect(screen.getByText(/loading presets/i)).toBeInTheDocument()

    rerender(
      <PresetManager
        reportPresets={[]}
        presetsLoading={false}
        presetsError="Failed"
        newPresetName=""
        onPresetNameChange={vi.fn()}
        onCreatePreset={vi.fn()}
        savingPreset={false}
        presetApplyingId={null}
        onApplyPreset={vi.fn()}
        filtersSnapshot={{ topics: [], sentiments: [], source_types: [], min_priority: null }}
        filtersPanelProps={filtersPanelProps}
      />
    )

    expect(screen.getByText(/failed/i)).toBeInTheDocument()
  })
})











