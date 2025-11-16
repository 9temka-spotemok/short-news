import { useCallback, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'

import type {
  AnalyticsPeriod,
  ComparisonResponse,
  ComparisonSubjectRequest
} from '../../../types'
import type { FilterOverrides } from '../types'
import type { FilteredPayload } from '../utils/filterPayload'
import { buildComparisonPayload } from '../utils/comparisonPayload'
import { getCachedComparison, useAnalyticsComparisonMutation } from './useAnalyticsComparison'

type ApplyFiltersToPayload = <T extends Record<string, unknown>>(
  payload: T,
  overrides?: FilterOverrides
) => FilteredPayload<T>

type FetchOverrides = {
  period?: AnalyticsPeriod
  lookback?: number
  range?: { from: string; to: string } | null
}

type AbSelection = { left: string | null; right: string | null }

export const useComparisonManager = ({
  applyFiltersToPayload
}: {
  applyFiltersToPayload: ApplyFiltersToPayload
}) => {
  const queryClient = useQueryClient()
  const analyticsComparisonMutation = useAnalyticsComparisonMutation()

  const [comparisonData, setComparisonData] = useState<ComparisonResponse | null>(null)
  const [comparisonLoading, setComparisonLoading] = useState(false)
  const [comparisonError, setComparisonError] = useState<string | null>(null)
  const [comparisonSubjects, setComparisonSubjects] = useState<ComparisonSubjectRequest[]>([])
  const [comparisonPeriod, setComparisonPeriod] = useState<AnalyticsPeriod>('daily')
  const [comparisonLookback, setComparisonLookback] = useState(30)
  const [analysisRange, setAnalysisRange] = useState<{ from: string; to: string } | null>(null)
  const [abSelection, setAbSelection] = useState<AbSelection>({ left: null, right: null })

  const resetComparison = useCallback(() => {
    setComparisonData(null)
    setComparisonError(null)
    setComparisonSubjects([])
    setAbSelection({ left: null, right: null })
  }, [])

  const fetchComparisonData = useCallback(
    async (subjects: ComparisonSubjectRequest[], overrides: FetchOverrides = {}) => {
      if (!subjects.length) {
        return
      }

      const nextPeriod = overrides.period ?? comparisonPeriod
      const nextLookback = overrides.lookback ?? comparisonLookback
      const range = overrides.range ?? analysisRange

      setComparisonLoading(true)
      setComparisonError(null)

      try {
        const filtersPayload = applyFiltersToPayload({})
        const payload = buildComparisonPayload({
          subjects,
          period: nextPeriod,
          lookback: nextLookback,
          range,
          filters: filtersPayload
        })

        let response = getCachedComparison(queryClient, payload)
        if (!response) {
          response = await analyticsComparisonMutation.mutateAsync(payload)
        }

        setComparisonData(response)
        setComparisonSubjects(subjects)
        setComparisonPeriod(nextPeriod)
        setComparisonLookback(nextLookback)
        if (range) {
          setAnalysisRange(range)
        } else if (payload.date_from && payload.date_to) {
          setAnalysisRange({ from: payload.date_from, to: payload.date_to })
        }

        const subjectKeys = response.subjects.map(subject => subject.subject_key)
        setAbSelection(prev => ({
          left: prev.left && subjectKeys.includes(prev.left) ? prev.left : subjectKeys[0] ?? null,
          right:
            prev.right && subjectKeys.includes(prev.right)
              ? prev.right
              : subjectKeys[1] ?? subjectKeys[0] ?? null
        }))
      } catch (error: any) {
        console.error('Failed to load comparison data:', error)
        setComparisonError(error?.response?.data?.detail || 'Failed to load comparison data')
      } finally {
        setComparisonLoading(false)
      }
    },
    [
      analysisRange,
      analyticsComparisonMutation,
      applyFiltersToPayload,
      comparisonLookback,
      comparisonPeriod,
      queryClient
    ]
  )

  const handleComparisonPeriodChange = useCallback(
    (period: AnalyticsPeriod) => {
      if (period === comparisonPeriod) return

      setComparisonPeriod(period)
      if (comparisonSubjects.length) {
        fetchComparisonData(comparisonSubjects, { period })
      }
    },
    [comparisonPeriod, comparisonSubjects, fetchComparisonData]
  )

  const handleComparisonLookbackChange = useCallback(
    (lookback: number) => {
      if (lookback === comparisonLookback) return

      setComparisonLookback(lookback)
      if (comparisonSubjects.length) {
        fetchComparisonData(comparisonSubjects, { lookback })
      }
    },
    [comparisonLookback, comparisonSubjects, fetchComparisonData]
  )

  const handleAbSelectionChange = useCallback(
    (position: 'left' | 'right', subjectKey: string) => {
      setAbSelection(prev => ({
        ...prev,
        [position]: subjectKey
      }))
    },
    []
  )

  return {
    comparisonData,
    comparisonLoading,
    comparisonError,
    comparisonSubjects,
    comparisonPeriod,
    comparisonLookback,
    analysisRange,
    abSelection,
    setAnalysisRange,
    resetComparison,
    fetchComparisonData,
    handleComparisonPeriodChange,
    handleComparisonLookbackChange,
    handleAbSelectionChange
  }
}













