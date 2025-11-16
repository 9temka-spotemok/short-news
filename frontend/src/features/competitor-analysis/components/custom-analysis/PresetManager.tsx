import { useMemo } from 'react'

import type { ReportPreset } from '@/types'

import { FiltersPanel } from '../FiltersPanel'
import { ActiveFiltersSummary, type ActiveFilters } from '../ActiveFiltersSummary'

const CARD_CLASSES = 'bg-white rounded-lg shadow-md p-6'

export type PresetManagerProps = {
  reportPresets: ReportPreset[]
  presetsLoading: boolean
  presetsError: string | null
  newPresetName: string
  onPresetNameChange: (value: string) => void
  onCreatePreset: () => void
  savingPreset: boolean
  presetApplyingId: string | null
  onApplyPreset: (preset: ReportPreset) => void
  filtersSnapshot: ActiveFilters
  filtersPanelProps: {
    sourceTypeFilters: string[]
    topicFilters: string[]
    sentimentFilters: string[]
    minPriorityFilter: number | null
    hasActiveFilters: boolean
    onToggleSourceType: (value: string) => void
    onToggleTopic: (value: string) => void
    onToggleSentiment: (value: string) => void
    onMinPriorityChange: (value: number | null) => void
    onClearFilters: () => void
  }
}

export const PresetManager = ({
  reportPresets,
  presetsLoading,
  presetsError,
  newPresetName,
  onPresetNameChange,
  onCreatePreset,
  savingPreset,
  presetApplyingId,
  onApplyPreset,
  filtersSnapshot,
  filtersPanelProps
}: PresetManagerProps) => {
  const sortedPresets = useMemo(
    () => [...reportPresets].sort((a, b) => a.name.localeCompare(b.name)),
    [reportPresets]
  )

  return (
    <div className={CARD_CLASSES}>
      <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
        <div className="flex-1 space-y-4">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Report Presets</h3>
            <p className="text-sm text-gray-600">
              Save and reuse analysis configurations (companies + filters + visualization options).
            </p>
          </div>

          <div className="space-y-3">
            <label className="block text-sm font-medium text-gray-700">
              Preset name
              <input
                type="text"
                value={newPresetName}
                onChange={event => onPresetNameChange(event.target.value)}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
                placeholder="AI competitor watch (Q4)"
              />
            </label>
            <button
              onClick={onCreatePreset}
              disabled={savingPreset || !newPresetName.trim()}
              className="bg-primary-600 text-white px-4 py-2 rounded-md hover:bg-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {savingPreset ? 'Saving…' : 'Save preset'}
            </button>
          </div>
        </div>

        <div className="flex-1">
          <h4 className="text-sm font-semibold text-gray-800 mb-2">Available presets</h4>
          {presetsLoading ? (
            <p className="text-sm text-gray-500">Loading presets…</p>
          ) : presetsError ? (
            <p className="text-sm text-red-600">{presetsError}</p>
          ) : sortedPresets.length ? (
            <ul className="space-y-2">
              {sortedPresets.map(preset => (
                <li key={preset.id} className="flex items-center justify-between border border-gray-200 rounded-md px-3 py-2">
                  <div>
                    <p className="text-sm font-medium text-gray-900">{preset.name}</p>
                    <p className="text-xs text-gray-500">
                      Companies: {preset.companies?.length ?? 0}
                    </p>
                  </div>
                  <button
                    onClick={() => onApplyPreset(preset)}
                    disabled={presetApplyingId === preset.id}
                    className="text-primary-600 hover:text-primary-700 text-sm font-medium"
                  >
                    {presetApplyingId === preset.id ? 'Applying…' : 'Apply'}
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-gray-500">No presets saved yet. Create one above to reuse later.</p>
          )}
        </div>
      </div>

      <div className="mt-6 space-y-4">
        <FiltersPanel {...filtersPanelProps} />
        <ActiveFiltersSummary filters={filtersSnapshot} />
      </div>
    </div>
  )
}











