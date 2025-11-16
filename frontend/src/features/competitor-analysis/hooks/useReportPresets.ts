import { useQuery, UseQueryOptions, UseQueryResult } from '@tanstack/react-query'

import { ApiService } from '@/services/api'
import type { ReportPreset } from '@/types'
import { competitorAnalysisKeys } from '../queryKeys'

type UseReportPresetsOptions = Pick<UseQueryOptions<ReportPreset[], unknown, ReportPreset[]>, 'enabled'>

export const useReportPresetsQuery = (
  options?: UseReportPresetsOptions
): UseQueryResult<ReportPreset[], unknown> =>
  useQuery({
    queryKey: competitorAnalysisKeys.reportPresets(),
    queryFn: () => ApiService.listReportPresets(),
    staleTime: 2 * 60 * 1000,
    refetchOnWindowFocus: false,
    ...options
  })

