import { BarChart3 } from 'lucide-react'
import { useMemo } from 'react'

import { ExportMenu } from '@/components/ExportMenu'
import CompanySelector from '@/components/CompanySelector'
import type { Company } from '@/types'

import { CompanyDeepDive } from './CompanyDeepDive'
import { FiltersPanel } from './FiltersPanel'
import { ActiveFiltersSummary, type ActiveFilters } from './ActiveFiltersSummary'

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
  loading: boolean
  onAnalyze: () => void | Promise<void>
  analysisData: any
  suggestedCompetitors: any[]
  onExport: (format: 'json' | 'pdf' | 'csv') => void | Promise<void>
  filtersSnapshot: ActiveFilters
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
  loading,
  onAnalyze,
  analysisData,
  suggestedCompetitors,
  onExport,
  filtersSnapshot
}: CompanyAnalysisFlowProps) => {
  const canAnalyze = useMemo(() => Boolean(selectedCompany), [selectedCompany])

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">Company Analysis</h2>
          <p className="text-gray-600 mt-1">Quick analysis with AI-suggested competitors</p>
        </div>
        <button onClick={onBack} className="text-gray-600 hover:text-gray-800 flex items-center">
          Back to Menu
        </button>
      </div>

      <div className="bg-white rounded-lg shadow-md p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Select Company to Analyze</h3>
        <CompanySelector onSelect={onSelectCompany} selectedCompany={selectedCompany} />

        <div className="mt-6">
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
        </div>

        {selectedCompany && (
          <div className="mt-6">
            <button
              onClick={onAnalyze}
              disabled={loading || !canAnalyze}
              className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
            >
              {loading ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  Analyzing...
                </>
              ) : (
                <>
                  <BarChart3 className="w-4 h-4 mr-2" />
                  Analyze Company
                </>
              )}
            </button>
          </div>
        )}
      </div>

      {analysisData && selectedCompany && (
        <div className="space-y-6">
          <div className="bg-white rounded-lg shadow-md p-6">
            <div className="flex justify-between items-center mb-4">
              <div>
                <h2 className="text-2xl font-bold text-gray-900">{selectedCompany.name}</h2>
                <p className="text-gray-600">Competitor Analysis Report</p>
              </div>
              <ExportMenu onExport={onExport} />
            </div>
          </div>

          <ActiveFiltersSummary filters={filtersSnapshot} />

          <CompanyDeepDive
            company={selectedCompany}
            analysisData={analysisData}
            suggestedCompetitors={suggestedCompetitors}
          />
        </div>
      )}
    </div>
  )
}
