import {
    useQuery,
    type UseQueryOptions,
    type UseQueryResult
} from '@tanstack/react-query'
import axios from 'axios'

import { ApiService } from '@/services/api'
import type {
    CompanyAnalyticsSnapshot,
    KnowledgeGraphEdge,
    SnapshotSeries
} from '@/types'

export type CompanyAnalyticsInsights = {
  snapshot: CompanyAnalyticsSnapshot | null
  series: SnapshotSeries | null
  edges: KnowledgeGraphEdge[]
  message: string | null
}

export const companyAnalyticsInsightsQueryKey = (companyId: string | null) =>
  ['competitor-analysis', 'company-analytics', companyId] as const

export const fetchCompanyAnalyticsInsights = async (
  companyId: string
): Promise<CompanyAnalyticsInsights> => {
  const [snapshotResult, seriesResult, edgesResult] = await Promise.allSettled([
    ApiService.getLatestAnalyticsSnapshot(companyId),
    ApiService.getAnalyticsSnapshots(companyId, 'daily', 60),
    ApiService.getAnalyticsGraph(companyId, undefined, 25)
  ])

  let snapshot: CompanyAnalyticsSnapshot | null = null
  let series: SnapshotSeries | null = null
  let edges: KnowledgeGraphEdge[] = []
  let message: string | null = null

  if (snapshotResult.status === 'fulfilled') {
    snapshot = snapshotResult.value
  } else {
    const reason = snapshotResult.reason
    if (axios.isAxiosError(reason) && reason.response?.status === 404) {
      message =
        'Аналитика ещё не построена. Запустите пересчёт, чтобы получить метрики.'
    } else {
      console.error('Failed to load latest analytics snapshot:', reason)
      const fallback =
        (reason as { response?: { data?: { detail?: string } }; message?: string })?.response
          ?.data?.detail || (reason as { message?: string }).message
      message = fallback ?? 'Failed to load analytics insights'
    }
  }

  if (seriesResult.status === 'fulfilled') {
    series = seriesResult.value
  } else {
    const reason = seriesResult.reason
    if (!(axios.isAxiosError(reason) && reason.response?.status === 404)) {
      console.error('Failed to load analytics snapshot series:', reason)
      const fallback =
        (reason as { response?: { data?: { detail?: string } }; message?: string })?.response
          ?.data?.detail || (reason as { message?: string }).message
      message = message ?? fallback ?? 'Failed to load analytics insights'
    }
  }

  if (edgesResult.status === 'fulfilled') {
    edges = edgesResult.value
  } else {
    const reason = edgesResult.reason
    if (!(axios.isAxiosError(reason) && reason.response?.status === 404)) {
      console.error('Failed to load analytics edges:', reason)
      const fallback =
        (reason as { response?: { data?: { detail?: string } }; message?: string })?.response
          ?.data?.detail || (reason as { message?: string }).message
      message = message ?? fallback ?? 'Failed to load analytics insights'
    }
  }

  return {
    snapshot,
    series,
    edges,
    message
  }
}

type UseCompanyAnalyticsInsightsOptions = Omit<
  UseQueryOptions<CompanyAnalyticsInsights, unknown, CompanyAnalyticsInsights>,
  'queryKey' | 'queryFn'
>

export const useCompanyAnalyticsInsights = (
  companyId: string | null,
  options?: UseCompanyAnalyticsInsightsOptions
): UseQueryResult<CompanyAnalyticsInsights, unknown> =>
  useQuery({
    queryKey: companyAnalyticsInsightsQueryKey(companyId),
    queryFn: () => {
      if (!companyId) {
        throw new Error('Company id is required to load analytics insights')
      }
      return fetchCompanyAnalyticsInsights(companyId)
    },
    enabled: Boolean(companyId),
    staleTime: 60 * 1000,
    refetchOnWindowFocus: false,
    ...options
  })













