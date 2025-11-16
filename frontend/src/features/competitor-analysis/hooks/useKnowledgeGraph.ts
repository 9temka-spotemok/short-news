import { useQuery } from '@tanstack/react-query'

import { ApiService } from '@/services/api'
import type { KnowledgeGraphEdge } from '@/types'
import { competitorAnalysisKeys, type KnowledgeGraphKeyParams } from '../queryKeys'

type UseKnowledgeGraphOptions = KnowledgeGraphKeyParams & {
  enabled?: boolean
}

export const useKnowledgeGraph = ({
  companyId,
  relationship,
  limit = 50,
  enabled = true,
}: UseKnowledgeGraphOptions) =>
  useQuery<KnowledgeGraphEdge[]>({
    queryKey: competitorAnalysisKeys.knowledgeGraph({
      companyId: companyId ?? null,
      relationship: relationship ?? null,
      limit,
    }),
    queryFn: () => ApiService.getAnalyticsGraph(companyId ?? undefined, relationship ?? undefined, limit),
    enabled: enabled && Boolean(companyId),
    staleTime: 2 * 60 * 1000,
    refetchOnWindowFocus: false,
  })













