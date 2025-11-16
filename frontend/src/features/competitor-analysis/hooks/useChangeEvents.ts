import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { ApiService } from '@/services/api'
import type { ChangeProcessingStatus, CompetitorChangeEvent } from '@/types'
import { competitorAnalysisKeys } from '../queryKeys'

type ChangeEventsQueryOptions = {
  companyId?: string | null
  limit?: number
  status?: ChangeProcessingStatus
  enabled?: boolean
}

export const useChangeEventsQuery = ({
  companyId,
  limit = 10,
  status,
  enabled = true
}: ChangeEventsQueryOptions) =>
  useQuery({
    queryKey: competitorAnalysisKeys.changeEvents(companyId, limit, status),
    queryFn: async () => {
      if (!companyId) {
        return { events: [] as CompetitorChangeEvent[], total: 0 }
      }
      return ApiService.getCompetitorChangeEvents(companyId, { limit, status })
    },
    enabled: enabled && Boolean(companyId),
    staleTime: 60 * 1000
  })

type RecomputeVariables = {
  companyId: string
  eventId: string
  limit?: number
  status?: ChangeProcessingStatus
}

export const useRecomputeChangeEventMutation = () => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ eventId }: RecomputeVariables) => ApiService.recomputeCompetitorChangeEvent(eventId),
    onSuccess: (updatedEvent, variables) => {
      const limit = variables.limit ?? 10
      const status = variables.status
      const queryKey = competitorAnalysisKeys.changeEvents(
        variables.companyId,
        limit,
        status
      )
      queryClient.setQueryData(queryKey, (previous: { events: CompetitorChangeEvent[]; total: number } | undefined) => {
        if (!previous) {
          return previous
        }
        return {
          ...previous,
          events: previous.events.map(event => (event.id === updatedEvent.id ? updatedEvent : event))
        }
      })
    }
  })
}

