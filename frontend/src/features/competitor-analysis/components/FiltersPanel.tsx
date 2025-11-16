import { Filter } from 'lucide-react'

import {
  SENTIMENT_OPTIONS,
  SOURCE_TYPE_OPTIONS,
  TOPIC_OPTIONS
} from '../constants'

type FiltersPanelProps = {
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

export const FiltersPanel = ({
  sourceTypeFilters,
  topicFilters,
  sentimentFilters,
  minPriorityFilter,
  hasActiveFilters,
  onToggleSourceType,
  onToggleTopic,
  onToggleSentiment,
  onMinPriorityChange,
  onClearFilters
}: FiltersPanelProps) => (
  <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
    <div className="flex items-center justify-between mb-4">
      <div className="flex items-center space-x-3">
        <div className="p-2 bg-primary-100 rounded-lg">
          <Filter className="w-5 h-5 text-primary-600" />
        </div>
        <div>
          <h4 className="text-sm font-semibold text-gray-900">Advanced Filters</h4>
          <p className="text-xs text-gray-500">
            Fine-tune analytics results by source, topic, sentiment and priority
          </p>
        </div>
      </div>
      <button
        onClick={onClearFilters}
        disabled={!hasActiveFilters}
        className="text-sm text-gray-500 hover:text-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        Reset
      </button>
    </div>

    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div>
        <h5 className="text-xs font-medium text-gray-600 uppercase mb-3">Source Types</h5>
        <div className="space-y-2">
          {SOURCE_TYPE_OPTIONS.map(option => (
            <label
              key={option.value}
              className="flex items-center space-x-2 text-sm text-gray-700"
            >
              <input
                type="checkbox"
                className="h-4 w-4 text-primary-600 border-gray-300 rounded"
                checked={sourceTypeFilters.includes(option.value)}
                onChange={() => onToggleSourceType(option.value)}
              />
              <span>{option.label}</span>
            </label>
          ))}
        </div>
      </div>

      <div>
        <h5 className="text-xs font-medium text-gray-600 uppercase mb-3">Topics</h5>
        <div className="grid grid-cols-2 gap-2">
          {TOPIC_OPTIONS.map(option => (
            <button
              key={option.value}
              type="button"
              onClick={() => onToggleTopic(option.value)}
              className={`px-3 py-1 text-xs rounded-full border transition-colors ${
                topicFilters.includes(option.value)
                  ? 'bg-blue-100 border-blue-300 text-blue-700'
                  : 'bg-gray-100 border-gray-200 text-gray-600 hover:border-gray-300'
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      <div className="space-y-4">
        <div>
          <h5 className="text-xs font-medium text-gray-600 uppercase mb-3">Sentiment</h5>
          <div className="space-y-2">
            {SENTIMENT_OPTIONS.map(option => (
              <label
                key={option.value}
                className="flex items-center space-x-2 text-sm text-gray-700"
              >
                <input
                  type="checkbox"
                  className="h-4 w-4 text-primary-600 border-gray-300 rounded"
                  checked={sentimentFilters.includes(option.value)}
                  onChange={() => onToggleSentiment(option.value)}
                />
                <span>{option.label}</span>
              </label>
            ))}
          </div>
        </div>

        <div>
          <h5 className="text-xs font-medium text-gray-600 uppercase mb-2">Minimum Priority</h5>
          <div className="flex items-center space-x-3">
            <input
              type="range"
              min={0}
              max={1}
              step={0.05}
              value={minPriorityFilter ?? 0}
              onChange={event => {
                const value = Number(event.target.value)
                onMinPriorityChange(value <= 0 ? null : value)
              }}
              className="w-full"
            />
            <span className="text-sm font-medium text-gray-700 w-12 text-right">
              {minPriorityFilter !== null ? minPriorityFilter.toFixed(2) : 'Off'}
            </span>
          </div>
          <p className="text-xs text-gray-500 mt-1">
            Filter out low-priority news items below the selected threshold.
          </p>
        </div>
      </div>
    </div>
  </div>
)












