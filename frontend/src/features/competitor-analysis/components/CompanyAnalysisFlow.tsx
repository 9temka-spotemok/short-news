import { ArrowLeft, BarChart3 } from 'lucide-react'
import { useMemo } from 'react'

import CompanySelector from '@/components/CompanySelector'
import { ErrorBanner } from '@/components/ErrorBanner'
import { ExportMenu } from '@/components/ExportMenu'
import type {
    Company,
    CompanyAnalyticsSnapshot,
    KnowledgeGraphEdge,
    SnapshotSeries
} from '@/types'

import { ActiveFiltersSummary, type ActiveFilters } from './ActiveFiltersSummary'
import { CompanyDeepDive } from './CompanyDeepDive'
import { FiltersPanel } from './FiltersPanel'
import { ImpactPanel } from './ImpactPanel'

type CompanyAnalysisFlowProps = {
  selectedCompany: Company | null
  onSelectCompany: (company: Company | null) => void
  onBack: () => void
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
  error: string | null
  loading: boolean
  onAnalyze: () => void | Promise<void>
  analysisData: any
  suggestedCompetitors: Array<{
    company: Company
    similarity_score: number
    common_categories: string[]
    reason: string
  }>
  onExport: (format: 'json' | 'pdf' | 'csv') => void | Promise<void>
  filtersSnapshot: ActiveFilters
  impactSnapshot: CompanyAnalyticsSnapshot | null
  impactSeries: SnapshotSeries | null
  analyticsEdges: KnowledgeGraphEdge[]
  analyticsLoading: boolean
  analyticsError: string | null
  onRecomputeAnalytics: () => void | Promise<void>
  onSyncKnowledgeGraph: () => void | Promise<void>
}

export const CompanyAnalysisFlow = ({
  selectedCompany,
  onSelectCompany,
  onBack,
  sourceTypeFilters,
  topicFilters,
  sentimentFilters,
  minPriorityFilter,
  hasActiveFilters,
  onToggleSourceType,
  onToggleTopic,
  onToggleSentiment,
  onMinPriorityChange,
  onClearFilters,
  error,
  loading,
  onAnalyze,
  analysisData,
  suggestedCompetitors,
  onExport,
  filtersSnapshot,
  impactSnapshot,
  impactSeries,
  analyticsEdges,
  analyticsLoading,
  analyticsError,
  onRecomputeAnalytics,
  onSyncKnowledgeGraph
}: CompanyAnalysisFlowProps) => {
  const canAnalyze = useMemo(() => Boolean(selectedCompany), [selectedCompany])

  return (
    <div className="max-w-6xl mx-auto space-y-4 sm:space-y-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex-1">
          <h2 className="text-lg sm:text-xl font-semibold text-gray-900">Company Analysis</h2>
          <p className="text-sm sm:text-base text-gray-600 mt-1">
            Quick analysis with AI-suggested competitors and configurable filters
          </p>
        </div>
        <button onClick={onBack} className="text-sm sm:text-base text-gray-600 hover:text-gray-800 flex items-center w-full sm:w-auto justify-center sm:justify-start">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Menu
        </button>
      </div>

      <div className="bg-white rounded-lg shadow-md p-4 sm:p-6 space-y-4 sm:space-y-6">
        <div>
          <h3 className="text-base sm:text-lg font-semibold text-gray-900 mb-3 sm:mb-4">Select company to analyse</h3>
          <CompanySelector onSelect={onSelectCompany} selectedCompany={selectedCompany} />
        </div>

        <FiltersPanel
          sourceTypeFilters={sourceTypeFilters}
          topicFilters={topicFilters}
          sentimentFilters={sentimentFilters}
          minPriorityFilter={minPriorityFilter}
          hasActiveFilters={hasActiveFilters}
          onToggleSourceType={onToggleSourceType}
          onToggleTopic={onToggleTopic}
          onToggleSentiment={onToggleSentiment}
          onMinPriorityChange={onMinPriorityChange}
          onClearFilters={onClearFilters}
        />

        {selectedCompany ? (
          <div className="space-y-4">
            {error ? <ErrorBanner className="text-sm" message={error} /> : null}

            <div className="flex justify-end">
              <button
                onClick={onAnalyze}
                disabled={loading || !canAnalyze}
                className="bg-primary-600 text-white px-4 sm:px-6 py-2 sm:py-3 rounded-lg hover:bg-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center w-full sm:w-auto text-sm sm:text-base"
              >
                {loading ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2" />
                    Analysing…
                  </>
                ) : (
                  <>
                    <BarChart3 className="w-4 h-4 mr-2" />
                    Analyze Company
                  </>
                )}
              </button>
            </div>
          </div>
        ) : null}
      </div>

      {analysisData && selectedCompany ? (
        <div className="space-y-4 sm:space-y-6">
          <div className="bg-white rounded-lg shadow-md p-4 sm:p-6">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-4">
              <div>
                <h2 className="text-xl sm:text-2xl font-bold text-gray-900">{selectedCompany.name}</h2>
                <p className="text-sm sm:text-base text-gray-600">Competitor analysis report</p>
              </div>
              <ExportMenu onExport={onExport} />
            </div>
          </div>

          <ActiveFiltersSummary filters={filtersSnapshot} />

          <ImpactPanel
            impactSnapshot={impactSnapshot}
            impactSeries={impactSeries}
            analyticsEdges={analyticsEdges}
            analyticsLoading={analyticsLoading}
            analyticsError={analyticsError}
            onRecompute={onRecomputeAnalytics}
            onSyncKnowledgeGraph={onSyncKnowledgeGraph}
          />

          <CompanyDeepDive
            company={selectedCompany}
            analysisData={analysisData}
            suggestedCompetitors={suggestedCompetitors}
          />
        </div>
      ) : null}
    </div>
  )
}
