import { renderHook, act } from '@testing-library/react'
import { QueryClient } from '@tanstack/react-query'
import { describe, it, expect, beforeEach, vi } from 'vitest'

import { ApiService } from '@/services/api'
import type { ComparisonRequestPayload, ComparisonResponse } from '@/types'
import { withQueryClient, createTestQueryClient } from '@/test/utils'
import { useComparisonManager } from '../useComparisonManager'

vi.mock('@/services/api')

const mockComparisonResponse: ComparisonResponse = {
  generated_at: new Date().toISOString(),
  period: 'daily',
  lookback: 30,
  date_from: new Date().toISOString(),
  date_to: new Date().toISOString(),
  subjects: [],
  metrics: [],
  series: [],
  change_log: {},
  knowledge_graph: {},
}

const comparisonRequest: ComparisonRequestPayload = {
  subjects: [
    {
      subject_type: 'company',
      reference_id: '1',
    },
  ],
  period: 'daily',
  lookback: 30,
}

describe('useComparisonManager', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    vi.resetAllMocks()
    queryClient = createTestQueryClient()
  })

  const renderUseComparisonManager = () =>
    renderHook(
      () =>
        useComparisonManager({
          applyFiltersToPayload: payload => payload,
        }),
      {
        wrapper: ({ children }) => withQueryClient(children, queryClient),
      }
    )

  it('fetches comparison data', async () => {
    vi.spyOn(ApiService, 'getAnalyticsComparison').mockResolvedValueOnce(mockComparisonResponse)

    const { result } = renderUseComparisonManager()

    await act(async () => {
      await result.current.fetchComparisonData(comparisonRequest.subjects)
    })

    expect(ApiService.getAnalyticsComparison).toHaveBeenCalled()
    expect(result.current.comparisonData).toEqual(mockComparisonResponse)
  })

  it('handles fetch error', async () => {
    vi.spyOn(ApiService, 'getAnalyticsComparison').mockRejectedValueOnce(new Error('fail'))

    const { result } = renderUseComparisonManager()

    await act(async () => {
      await result.current.fetchComparisonData(comparisonRequest.subjects)
    })

    expect(result.current.comparisonError).toBe('Failed to load comparison data')
  })
})


