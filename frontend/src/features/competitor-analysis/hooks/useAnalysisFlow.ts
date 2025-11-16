import { useCallback, useState } from 'react'
import toast from 'react-hot-toast'

import { ApiService } from '@/services/api'
import type {
  AnalyticsPeriod,
  Company,
  ComparisonSubjectRequest
} from '@/types'
import type { FilterOverrides, FilterStateSnapshot } from '../types'
import type { FilteredPayload } from '../utils/filterPayload'

type ApplyFiltersToPayload = <T extends Record<string, unknown>>(
  payload: T,
  overrides?: FilterOverrides
) => FilteredPayload<T>

type FetchComparisonDataFn = (
  subjects: ComparisonSubjectRequest[],
  overrides?: {
    period?: AnalyticsPeriod
    lookback?: number
    range?: { from: string; to: string } | null
  }
) => Promise<void>

type SuggestedCompetitor = {
  company: Company
  similarity_score: number
  common_categories: string[]
  reason: string
}

export type RunAnalysisOverride = {
  primaryCompany: Company
  competitorIds: string[]
  filters?: {
    source_types?: string[]
    topics?: string[]
    sentiments?: string[]
    min_priority?: number | null
  }
}

type UseAnalysisFlowParams = {
  applyFiltersToPayload: ApplyFiltersToPayload
  fetchComparisonData: FetchComparisonDataFn
  setComparisonRange: (range: { from: string; to: string } | null) => void
  resetComparison: () => void
  comparisonPeriod: AnalyticsPeriod
  comparisonLookback: number
  filtersState: FilterStateSnapshot
  onAnalysisStart?: () => void
  onAnalysisComplete?: (primaryCompanyId: string | null) => Promise<void> | void
}

export const useAnalysisFlow = ({
  applyFiltersToPayload,
  fetchComparisonData,
  setComparisonRange,
  resetComparison,
  comparisonPeriod,
  comparisonLookback,
  filtersState,
  onAnalysisStart,
  onAnalysisComplete
}: UseAnalysisFlowParams) => {
  const [selectedCompany, setSelectedCompany] = useState<Company | null>(null)
  const [selectedCompetitors, setSelectedCompetitors] = useState<string[]>([])
  const [manuallyAddedCompetitors, setManuallyAddedCompetitors] = useState<Company[]>([])
  const [suggestedCompetitors, setSuggestedCompetitors] = useState<SuggestedCompetitor[]>([])
  const [analysisData, setAnalysisData] = useState<any>(null)
  const [themesData, setThemesData] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const toggleCompetitor = useCallback((companyId: string) => {
    setSelectedCompetitors(prev =>
      prev.includes(companyId) ? prev.filter(id => id !== companyId) : [...prev, companyId]
    )
  }, [])

  const addManualCompetitor = useCallback((company: Company) => {
    setManuallyAddedCompetitors(prev => {
      if (prev.some(item => item.id === company.id)) {
        return prev
      }
      return [...prev, company]
    })
    setSelectedCompetitors(prev =>
      prev.includes(company.id) ? prev : [...prev, company.id]
    )
  }, [])

  const loadCompetitorSuggestions = useCallback(
    async (companyId?: string | null) => {
      const id = companyId ?? selectedCompany?.id
      if (!id) return

      setLoading(true)
      setError(null)

      try {
        const response = await ApiService.suggestCompetitors(id, {
          limit: 5,
          days: 30
        })
        setSuggestedCompetitors(response.suggestions)
      } catch (err: any) {
        console.error('Error loading suggestions:', err)
        setError(err?.response?.data?.detail || 'Failed to load competitor suggestions')
      } finally {
        setLoading(false)
      }
    },
    [selectedCompany?.id]
  )

  const clearAnalysisResults = useCallback(() => {
    setAnalysisData(null)
    setThemesData(null)
  }, [])

  const resetAnalysisState = useCallback(() => {
    setSelectedCompany(null)
    setSelectedCompetitors([])
    setManuallyAddedCompetitors([])
    setSuggestedCompetitors([])
    setAnalysisData(null)
    setThemesData(null)
    setError(null)
    resetComparison()
    setComparisonRange(null)
  }, [resetComparison, setComparisonRange])

  const runAnalysis = useCallback(
    async (override?: RunAnalysisOverride) => {
      const primaryCompany = override?.primaryCompany ?? selectedCompany
      const competitorIds = override?.competitorIds ?? selectedCompetitors

      if (
        !primaryCompany ||
        !primaryCompany.id ||
        !Array.isArray(competitorIds) ||
        competitorIds.length === 0
      ) {
        setError('Select a primary company and at least one competitor before running analysis.')
        return
      }

      onAnalysisStart?.()
      resetComparison()
      setLoading(true)
      setError(null)
      clearAnalysisResults()

      try {
        const allCompanyIds = [primaryCompany.id, ...competitorIds].map(id => String(id))
        const dateFrom = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString()
        const dateTo = new Date().toISOString()
        setComparisonRange({ from: dateFrom, to: dateTo })

        const filterOverrides: FilterOverrides | undefined = override?.filters
          ? {
              sourceTypes: override.filters.source_types,
              topics: override.filters.topics,
              sentiments: override.filters.sentiments,
              minPriority:
                override.filters.min_priority === undefined
                  ? undefined
                  : override.filters.min_priority ?? null
            }
          : {
              sourceTypes: filtersState.sourceTypes,
              topics: filtersState.topics,
              sentiments: filtersState.sentiments,
              minPriority: filtersState.minPriority
            }

        const comparisonPayload = applyFiltersToPayload(
          {
            company_ids: allCompanyIds,
            date_from: dateFrom,
            date_to: dateTo
          },
          filterOverrides
        )

        const response = await ApiService.compareCompanies(comparisonPayload)
        setAnalysisData(response)

        const themesResponse = await ApiService.analyzeThemes(allCompanyIds, {
          date_from: dateFrom,
          date_to: dateTo
        })
        setThemesData(themesResponse)

        const subjects: ComparisonSubjectRequest[] = response.companies.map((company: Company) => ({
          subject_type: 'company',
          reference_id: company.id,
          label: company.name
        }))

        await fetchComparisonData(subjects, {
          period: comparisonPeriod,
          lookback: comparisonLookback,
          range: { from: dateFrom, to: dateTo }
        })

        await onAnalysisComplete?.(primaryCompany.id)

        await onAnalysisComplete?.(primaryCompany.id)
      } catch (err: any) {
        console.error('Error running analysis:', err)
        setError(err?.response?.data?.detail || err?.message || 'Failed to run analysis')
      } finally {
        setLoading(false)
      }
    },
    [
      applyFiltersToPayload,
      clearAnalysisResults,
      comparisonLookback,
      comparisonPeriod,
      filtersState,
      fetchComparisonData,
      onAnalysisComplete,
      onAnalysisStart,
      resetComparison,
      selectedCompany,
      selectedCompetitors,
      setComparisonRange
    ]
  )

  const runCompanyAnalysis = useCallback(async () => {
    if (!selectedCompany) return

    setError(null)

    try {
      const suggestionsResponse = await ApiService.suggestCompetitors(selectedCompany.id, {
        limit: 5,
        days: 30
      })

      const competitorIds = suggestionsResponse.suggestions.slice(0, 3).map(s => s.company.id)
      if (!competitorIds.length) {
        toast.error('Not enough competitor data to run analysis yet')
        return
      }

      setSelectedCompetitors(competitorIds)
      setManuallyAddedCompetitors(suggestionsResponse.suggestions.map(s => s.company))
      setSuggestedCompetitors(suggestionsResponse.suggestions)

      await runAnalysis({
        primaryCompany: selectedCompany,
        competitorIds,
        filters: {
          source_types: filtersState.sourceTypes,
          topics: filtersState.topics,
          sentiments: filtersState.sentiments,
          min_priority: filtersState.minPriority
        }
      })
    } catch (err: any) {
      console.error('Error running company analysis:', err)
      setError(err?.response?.data?.detail || err?.message || 'Failed to run analysis')
    }
  }, [filtersState, runAnalysis, selectedCompany])

  return {
    selectedCompany,
    setSelectedCompany,
    selectedCompetitors,
    setSelectedCompetitors,
    manuallyAddedCompetitors,
    setManuallyAddedCompetitors,
    suggestedCompetitors,
    setSuggestedCompetitors,
    analysisData,
    themesData,
    loading,
    error,
    setError,
    toggleCompetitor,
    addManualCompetitor,
    loadCompetitorSuggestions,
    runAnalysis,
    runCompanyAnalysis,
    resetAnalysisState,
    clearAnalysisResults
  }
}


