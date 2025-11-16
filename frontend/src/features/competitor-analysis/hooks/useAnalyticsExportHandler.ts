import { useCallback } from 'react'
import toast from 'react-hot-toast'

import type {
  AnalyticsExportRequestPayload,
  AnalyticsPeriod,
  Company,
  ComparisonResponse,
  ComparisonSubjectRequest
} from '@/types'
import { buildComparisonPayload } from '../utils/comparisonPayload'
import type { FilterOverrides } from '../types'
import type { FilteredPayload } from '../utils/filterPayload'

type ApplyFiltersToPayload = <T extends Record<string, unknown>>(
  payload: T,
  overrides?: FilterOverrides
) => FilteredPayload<T>

type UseAnalyticsExportHandlerParams = {
  analysisData: ComparisonResponse | null
  selectedCompany: Company | null
  comparisonSubjects: ComparisonSubjectRequest[]
  comparisonPeriod: AnalyticsPeriod
  comparisonLookback: number
  analysisRange: { from: string; to: string } | null
  applyFiltersToPayload: ApplyFiltersToPayload
  exportAnalytics: (
    payload: AnalyticsExportRequestPayload & { format: 'json' | 'pdf' | 'csv' }
  ) => Promise<unknown>
}

export const useAnalyticsExportHandler = ({
  analysisData,
  selectedCompany,
  comparisonSubjects,
  comparisonPeriod,
  comparisonLookback,
  analysisRange,
  applyFiltersToPayload,
  exportAnalytics
}: UseAnalyticsExportHandlerParams) =>
  useCallback(
    async (format: 'json' | 'pdf' | 'csv') => {
      if (!analysisData || !selectedCompany) {
        toast.error('Run analysis before exporting results')
        return
      }

      const fallbackSubjects: ComparisonSubjectRequest[] = analysisData.subjects.map(subject => ({
        subject_type: subject.subject_type,
        reference_id: subject.subject_id,
        label: subject.label,
        color: subject.color ?? undefined,
      }))
      const subjects = comparisonSubjects.length ? comparisonSubjects : fallbackSubjects

      if (!subjects.length) {
        toast.error('No comparison subjects available for export')
        return
      }

      const range = analysisRange ?? {
        from: new Date(Date.now() - comparisonLookback * 24 * 60 * 60 * 1000).toISOString(),
        to: new Date().toISOString()
      }

      const filtersPayload = applyFiltersToPayload({})
      const comparisonPayload = buildComparisonPayload({
        subjects,
        period: comparisonPeriod,
        lookback: comparisonLookback,
        range,
        filters: filtersPayload
      })

      const payload: AnalyticsExportRequestPayload & { format: 'json' | 'pdf' | 'csv' } = {
        ...comparisonPayload,
        export_format: format,
        include: {
          include_notifications: true,
          include_presets: true
        },
        format
      }

      try {
        await exportAnalytics(payload)
        toast.success(`Exported analysis as ${format.toUpperCase()}`)
      } catch (err: any) {
        console.error('Export failed:', err)
        toast.error(err?.response?.data?.detail || 'Export failed. Please try again.')
      }
    },
    [
      analysisData,
      analysisRange,
      applyFiltersToPayload,
      comparisonLookback,
      comparisonPeriod,
      comparisonSubjects,
      exportAnalytics,
      selectedCompany
    ]
  )


