import { ArrowLeft } from 'lucide-react'

import { ExportMenu } from '@/components/ExportMenu'

import type { Company } from '@/types'

import { ActiveFiltersSummary, type ActiveFilters } from '../ActiveFiltersSummary'

const WRAPPER_CLASSES = 'max-w-6xl mx-auto space-y-6'

type AnalysisResultsStepProps = {
  selectedCompany: Company | null
  loading: boolean
  analysisData: any
  filtersSnapshot: ActiveFilters
  onBack: () => void
  onExport: (format: 'json' | 'pdf' | 'csv') => void | Promise<void>
  children: React.ReactNode
}

export const AnalysisResultsStep = ({
  selectedCompany,
  loading,
  analysisData,
  filtersSnapshot,
  onBack,
  onExport,
  children
}: AnalysisResultsStepProps) => (
  <div className={WRAPPER_CLASSES}>
    <div className="flex items-center justify-between">
      <div>
        <h2 className="text-xl font-semibold text-gray-900">Analysis Results</h2>
        <p className="text-gray-600 mt-1">
          Comprehensive analysis of {selectedCompany?.name ?? 'selected company'} and its competitors
        </p>
      </div>
      <div className="flex space-x-3">
        <button onClick={onBack} className="text-gray-600 hover:text-gray-800 flex items-center">
          <ArrowLeft className="w-4 h-4 mr-1" />
          Back
        </button>
        <ExportMenu onExport={onExport} />
      </div>
    </div>

    {loading && (
      <div className="text-center py-8">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto" />
        <p className="mt-4 text-gray-600">Analyzing competitors...</p>
      </div>
    )}

    {analysisData && (
      <div className="space-y-6">
        <ActiveFiltersSummary filters={filtersSnapshot} />
        {children}
      </div>
    )}
  </div>
)
