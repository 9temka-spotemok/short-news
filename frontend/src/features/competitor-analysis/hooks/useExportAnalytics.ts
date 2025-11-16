import { useMutation } from '@tanstack/react-query'

import { ApiService } from '@/services/api'
import type { AnalyticsExportRequestPayload, AnalyticsExportResponse } from '@/types'

export const useExportAnalyticsMutation = () =>
  useMutation({
    mutationFn: async (payload: AnalyticsExportRequestPayload & { format: 'json' | 'pdf' | 'csv' }) => {
      const { format, ...request } = payload
      const exportResponse: AnalyticsExportResponse = await ApiService.buildAnalyticsExport(request)
      await ApiService.exportAnalysis(exportResponse, format)
      return exportResponse
    }
  })












