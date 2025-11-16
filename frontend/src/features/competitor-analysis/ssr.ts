import { QueryClient, dehydrate } from '@tanstack/react-query'

import { ApiService } from '@/services/api'
import type { ComparisonRequestPayload } from '@/types'
import { competitorAnalysisKeys } from './queryKeys'
import {
  companyAnalyticsInsightsQueryKey,
  fetchCompanyAnalyticsInsights
} from './hooks/useCompanyAnalyticsInsights'

type PrefetchOptions = {
  companyId?: string | null
  comparisonPayload?: ComparisonRequestPayload | null
}

export const buildCompetitorAnalysisState = async ({
  companyId,
  comparisonPayload
}: PrefetchOptions) => {
  const queryClient = new QueryClient()

  if (companyId) {
    await queryClient.prefetchQuery({
      queryKey: companyAnalyticsInsightsQueryKey(companyId),
      queryFn: () => fetchCompanyAnalyticsInsights(companyId),
      staleTime: 60 * 1000
    })
  }

  if (comparisonPayload) {
    await queryClient.prefetchQuery({
      queryKey: competitorAnalysisKeys.comparison(comparisonPayload),
      queryFn: () => ApiService.getAnalyticsComparison(comparisonPayload),
      staleTime: 2 * 60 * 1000
    })
  }

  return {
    queryClient,
    dehydratedState: dehydrate(queryClient)
  }
}













