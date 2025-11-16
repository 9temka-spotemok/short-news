import { Filter } from 'lucide-react'

import { formatLabel } from '../utils/formatters'

export type ActiveFilters = {
  topics?: string[]
  sentiments?: string[]
  source_types?: string[]
  min_priority?: number | null
} | null | undefined

export type ActiveFiltersSummaryProps = {
  filters: ActiveFilters
}

export const ActiveFiltersSummary = ({ filters }: ActiveFiltersSummaryProps) => {
  if (!filters) {
    return null
  }

  const { topics = [], sentiments = [], source_types = [], min_priority } = filters
  const hasFilters =
    topics.length || sentiments.length || source_types.length || (min_priority !== undefined && min_priority !== null)

  if (!hasFilters) {
    return null
  }

  return (
    <div className="bg-blue-50 border border-blue-100 rounded-lg p-4 flex items-start space-x-3">
      <Filter className="w-4 h-4 mt-1 text-blue-600" />
      <div className="space-y-2 text-sm text-blue-700">
        <p className="text-xs font-semibold uppercase text-blue-600">Active Filters</p>
        <div className="flex flex-wrap gap-2">
          {source_types.map(value => (
            <span key={`source-${value}`} className="px-2 py-1 text-xs bg-white border border-blue-200 text-blue-700 rounded-full">
              Source: {formatLabel(value)}
            </span>
          ))}
          {topics.map(value => (
            <span key={`topic-${value}`} className="px-2 py-1 text-xs bg-white border border-blue-200 text-blue-700 rounded-full">
              Topic: {formatLabel(value)}
            </span>
          ))}
          {sentiments.map(value => (
            <span key={`sentiment-${value}`} className="px-2 py-1 text-xs bg-white border border-blue-200 text-blue-700 rounded-full">
              Sentiment: {formatLabel(value)}
            </span>
          ))}
          {(min_priority !== undefined && min_priority !== null) && (
            <span className="px-2 py-1 text-xs bg-white border border-blue-200 text-blue-700 rounded-full">
              Min priority: {Number(min_priority).toFixed(2)}
            </span>
          )}
        </div>
      </div>
    </div>
  )
}
