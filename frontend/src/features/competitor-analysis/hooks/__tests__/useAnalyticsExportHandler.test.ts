import { renderHook, act } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'

import type { ComparisonSubjectRequest } from '@/types'
import { useAnalyticsExportHandler } from '../useAnalyticsExportHandler'

vi.mock('react-hot-toast', () => {
  const success = vi.fn()
  const error = vi.fn()
  return {
    default: { success, error },
    success,
    error,
  }
})

describe('useAnalyticsExportHandler', () => {
  const comparisonSubjects: ComparisonSubjectRequest[] = [
    { subject_type: 'company', reference_id: '1' },
  ]

  const noopApplyFiltersToPayload = (<T extends Record<string, unknown>>(payload: T) =>
    payload as any) as any

  const baseProps = {
    analysisData: { companies: [{ id: '1', name: 'Acme' }] } as any,
    selectedCompany: { id: '1', name: 'Acme' } as any,
    comparisonSubjects,
    comparisonPeriod: 'daily' as const,
    comparisonLookback: 30,
    analysisRange: null,
    applyFiltersToPayload: noopApplyFiltersToPayload,
  }

  it('builds payload and calls export handler', async () => {
    const exportAnalytics = vi.fn().mockResolvedValue(undefined)

    const { result } = renderHook(() =>
      useAnalyticsExportHandler({
        ...baseProps,
        exportAnalytics,
      })
    )

    await act(async () => {
      await result.current('json')
    })

    expect(exportAnalytics).toHaveBeenCalledWith(
      expect.objectContaining({
        format: 'json',
        export_format: 'json',
        include: expect.objectContaining({
          include_notifications: true,
          include_presets: true,
        }),
      })
    )
  })

  it('skips export when analysis data missing', async () => {
    const exportAnalytics = vi.fn()

    const { result } = renderHook(() =>
      useAnalyticsExportHandler({
        ...baseProps,
        analysisData: null,
        exportAnalytics,
      })
    )

    await act(async () => {
      await result.current('json')
    })

    expect(exportAnalytics).not.toHaveBeenCalled()
  })
})













