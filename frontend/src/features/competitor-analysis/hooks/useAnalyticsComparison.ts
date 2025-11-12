import { useMutation, useQueryClient } from '@tanstack/react-query'

import { ApiService } from '@/services/api'
import type { ComparisonRequestPayload, ComparisonResponse } from '@/types'
import { competitorAnalysisKeys } from '../queryKeys'

const comparisonKey = (payload: ComparisonRequestPayload) =>
  competitorAnalysisKeys.comparison({
    ...payload,
    subjects: payload.subjects,
    filters: payload.filters
  })

export const useAnalyticsComparisonMutation = () => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (payload: ComparisonRequestPayload) =>
      ApiService.getAnalyticsComparison(payload),
    onSuccess: (data: ComparisonResponse, variables) => {
      queryClient.setQueryData(comparisonKey(variables), data)
    }
  })
}

export const getCachedComparison = (
  queryClient: ReturnType<typeof useQueryClient>,
  payload: ComparisonRequestPayload
) =>
  queryClient.getQueryData<ComparisonResponse>(comparisonKey(payload)) ?? null

