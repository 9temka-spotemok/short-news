import { renderHook, act } from '@testing-library/react'
import { QueryClient } from '@tanstack/react-query'
import { describe, it, expect, beforeEach, vi } from 'vitest'

import { ApiService } from '@/services/api'
import { withQueryClient, createTestQueryClient } from '@/test/utils'
import { usePrefetchAnalytics } from '../usePrefetchAnalytics'

vi.mock('@/services/api')

const mockApi = vi.mocked(ApiService)

describe('usePrefetchAnalytics', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    vi.resetAllMocks()
    queryClient = createTestQueryClient()
  })

  const renderUsePrefetch = () =>
    renderHook(() => usePrefetchAnalytics(), {
      wrapper: ({ children }) => withQueryClient(children, queryClient),
    })

  it('prefetches company insights and comparison payload', async () => {
    const prefetchSpy = vi.spyOn(queryClient, 'prefetchQuery')
    mockApi.getAnalyticsComparison.mockResolvedValueOnce({} as any)

    const { result } = renderUsePrefetch()

    await act(async () => {
      await result.current({
        companyId: 'company-1',
        comparisonPayload: {
          subjects: [{ subject_type: 'company', reference_id: '1' }],
        },
      })
    })

    expect(prefetchSpy).toHaveBeenCalledTimes(2)
    expect(mockApi.getAnalyticsComparison).toHaveBeenCalled()
  })
})













