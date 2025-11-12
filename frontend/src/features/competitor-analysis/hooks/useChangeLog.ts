import { useInfiniteQuery } from '@tanstack/react-query'

import { ApiService } from '@/services/api'
import type { AnalyticsPeriod, CompetitorChangeEvent, ComparisonFilters } from '@/types'
import type { FilterStateSnapshot } from '../types'
import { competitorAnalysisKeys } from '../queryKeys'

const toComparisonFilters = (filterState?: FilterStateSnapshot): ComparisonFilters | undefined => {
  if (!filterState) {
    return undefined
  }

  const filters: ComparisonFilters = {
    topics: filterState.topics ?? [],
    sentiments: filterState.sentiments ?? [],
    source_types: filterState.sourceTypes ?? [],
  }

  if (filterState.minPriority !== undefined && filterState.minPriority !== null) {
    filters.min_priority = filterState.minPriority
  }

  return filters
}

export type UseChangeLogOptions = {
  companyId?: string | null
  subjectKey?: string | null
  period?: AnalyticsPeriod | null
  filterState?: FilterStateSnapshot
  limit?: number
  enabled?: boolean
}

export type ChangeLogPage = {
  events: CompetitorChangeEvent[]
  next_cursor: string | null
  total: number
}

export const useChangeLog = ({
  companyId,
  subjectKey,
  period,
  filterState,
  limit = 20,
  enabled = true,
}: UseChangeLogOptions) =>
  useInfiniteQuery<ChangeLogPage>({
    queryKey: competitorAnalysisKeys.changeLog({
      companyId: companyId ?? null,
      subjectKey: subjectKey ?? null,
      period: period ?? null,
      filterState,
      limit,
    }),
    queryFn: ({ pageParam }) =>
      ApiService.getAnalyticsChangeLog({
        companyId: companyId ?? undefined,
        subjectKey: subjectKey ?? undefined,
        period: period ?? undefined,
        cursor: (pageParam as string | undefined) ?? undefined,
        limit,
        filters: toComparisonFilters(filterState),
      }),
    getNextPageParam: (lastPage) => lastPage.next_cursor ?? undefined,
    keepPreviousData: true,
    enabled: enabled && Boolean(companyId),
  })



