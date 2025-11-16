import { ArrowLeft, ArrowRight } from 'lucide-react'

import CompetitorSuggestions from '@/components/CompetitorSuggestions'
import { ErrorBanner } from '@/components/ErrorBanner'
import { LoadingOverlay } from '@/components/LoadingOverlay'
import type { Company } from '@/types'
import { ActiveFiltersSummary, type ActiveFilters } from '../ActiveFiltersSummary'
import { FiltersPanel } from '../FiltersPanel'

const CARD_CLASSES = 'max-w-4xl mx-auto bg-white rounded-lg shadow-md p-6'

type CompetitorSuggestionStepProps = {
  selectedCompany: Company | null
  suggestions: Array<{
    company: Company
    similarity_score: number
    common_categories: string[]
    reason: string
  }>
  manuallyAddedCompetitors: Company[]
  selectedCompetitors: string[]
  onToggleCompetitor: (companyId: string) => void
  onAddManualCompetitor: (company: Company) => void
  onBack: () => void
  onNext: () => void
  filters: {
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
  loading: boolean
  error: string | null
  filtersSnapshot: ActiveFilters
}

export const CompetitorSuggestionStep = ({
  selectedCompany: _selectedCompany,
  suggestions,
  manuallyAddedCompetitors: _manuallyAddedCompetitors,
  selectedCompetitors,
  onToggleCompetitor,
  onAddManualCompetitor,
  onBack,
  onNext,
  filters,
  loading,
  error,
  filtersSnapshot
}: CompetitorSuggestionStepProps) => (
  <div className={CARD_CLASSES}>
    <div className="flex items-center justify-between mb-6">
      <div>
        <h2 className="text-xl font-semibold text-gray-900">Choose Competitors</h2>
        <p className="text-gray-600 mt-1">
          AI has suggested competitors based on similarity analysis
        </p>
      </div>
      <button onClick={onBack} className="text-gray-600 hover:text-gray-800 flex items-center">
        <ArrowLeft className="w-4 h-4 mr-1" />
        Back
      </button>
    </div>

    {error ? <ErrorBanner className="mb-4 text-sm" message={error} /> : null}

    <div className="relative">
      {loading ? (
        <LoadingOverlay
          overlay
          className="rounded-lg"
          label="Loading competitor suggestions…"
          description="We are analysing similar companies based on activity and topics"
        />
      ) : null}
      <CompetitorSuggestions
        suggestions={suggestions}
        selectedCompetitors={selectedCompetitors}
        onToggleCompetitor={onToggleCompetitor}
        onAddManual={onAddManualCompetitor}
      />
    </div>

    <div className="mt-6 space-y-4">
      <FiltersPanel
        sourceTypeFilters={filters.sourceTypeFilters}
        topicFilters={filters.topicFilters}
        sentimentFilters={filters.sentimentFilters}
        minPriorityFilter={filters.minPriorityFilter}
        hasActiveFilters={filters.hasActiveFilters}
        onToggleSourceType={filters.onToggleSourceType}
        onToggleTopic={filters.onToggleTopic}
        onToggleSentiment={filters.onToggleSentiment}
        onMinPriorityChange={filters.onMinPriorityChange}
        onClearFilters={filters.onClearFilters}
      />
      <ActiveFiltersSummary filters={filtersSnapshot} />
    </div>

    <div className="mt-6 flex justify-between">
      <button onClick={onBack} className="text-gray-600 hover:text-gray-800 flex items-center">
        <ArrowLeft className="w-4 h-4 mr-1" />
        Back
      </button>
      <button
        onClick={onNext}
        disabled={!selectedCompetitors.length || loading}
        className="bg-primary-600 text-white px-6 py-3 rounded-lg hover:bg-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
      >
        Analyze
        <ArrowRight className="w-5 h-5 ml-2" />
      </button>
    </div>
  </div>
)
