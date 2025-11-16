import { useCallback } from 'react'
import { useQueryClient } from '@tanstack/react-query'

import { ApiService } from '@/services/api'
import type { ComparisonRequestPayload } from '@/types'
import { competitorAnalysisKeys } from '../queryKeys'
import {
  companyAnalyticsInsightsQueryKey,
  fetchCompanyAnalyticsInsights,
} from './useCompanyAnalyticsInsights'

type PrefetchOptions = {
  companyId?: string | null
  comparisonPayload?: ComparisonRequestPayload | null
}

export const usePrefetchAnalytics = () => {
  const queryClient = useQueryClient()

  return useCallback(
    async ({ companyId, comparisonPayload }: PrefetchOptions) => {
      const tasks: Promise<unknown>[] = []

      if (companyId) {
        tasks.push(
          queryClient.prefetchQuery({
            queryKey: companyAnalyticsInsightsQueryKey(companyId),
            queryFn: () => fetchCompanyAnalyticsInsights(companyId),
            staleTime: 60 * 1000,
          })
        )
      }

      if (comparisonPayload) {
        tasks.push(
          queryClient.prefetchQuery({
            queryKey: competitorAnalysisKeys.comparison(comparisonPayload),
            queryFn: () => ApiService.getAnalyticsComparison(comparisonPayload),
            staleTime: 2 * 60 * 1000,
          })
        )
      }

      if (tasks.length) {
        await Promise.all(tasks)
      }
    },
    [queryClient]
  )
}













