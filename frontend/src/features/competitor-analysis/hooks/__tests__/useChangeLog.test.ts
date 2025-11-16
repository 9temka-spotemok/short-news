import { QueryClient } from '@tanstack/react-query'
import { act, renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiService } from '@/services/api'
import { createTestQueryClient, withQueryClient } from '@/test/utils'
import { useChangeLog } from '../useChangeLog'

vi.mock('@/services/api')

const mockApi = vi.mocked(ApiService)

describe('useChangeLog', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    vi.resetAllMocks()
    queryClient = createTestQueryClient()
  })

  const renderUseChangeLog = (options = {}) =>
    renderHook(
      () =>
        useChangeLog({
          companyId: 'company-1',
          enabled: true,
          ...options,
        }),
      {
        wrapper: ({ children }) => withQueryClient(children, queryClient),
      }
    )

  it('fetches change log data', async () => {
    mockApi.getAnalyticsChangeLog.mockResolvedValueOnce({
      events: [{
        id: 'event-1',
        company_id: 'company-1',
        source_type: 'blog',
        change_summary: 'Price updated',
        changed_fields: [],
        raw_diff: {},
        detected_at: new Date().toISOString(),
        processing_status: 'success',
        notification_status: 'pending',
        current_snapshot: null,
        previous_snapshot: null,
      }],
      next_cursor: null,
      total: 1,
    } as any)

    const { result } = renderUseChangeLog()

    await waitFor(() =>
      expect(result.current.data?.pages[0].events).toEqual([{ id: 'event-1' }])
    )

    expect(mockApi.getAnalyticsChangeLog).toHaveBeenCalledWith({
      companyId: 'company-1',
      cursor: undefined,
      filters: undefined,
      limit: 20,
      period: undefined,
      subjectKey: undefined,
    })
  })

  it('fetches next page when cursor provided', async () => {
    mockApi.getAnalyticsChangeLog
      .mockResolvedValueOnce({
        events: [],
        next_cursor: 'cursor-1',
        total: 1,
      } as any)
      .mockResolvedValueOnce({
        events: [{
          id: 'event-2',
          company_id: 'company-1',
          source_type: 'blog',
          change_summary: 'Feature updated',
          changed_fields: [],
          raw_diff: {},
          detected_at: new Date().toISOString(),
          processing_status: 'success',
          notification_status: 'pending',
          current_snapshot: null,
          previous_snapshot: null,
        }],
        next_cursor: null,
        total: 2,
      } as any)

    const { result } = renderUseChangeLog()

    await waitFor(() => expect(result.current.hasNextPage).toBe(true))

    await act(async () => {
      await result.current.fetchNextPage()
    })

    await waitFor(() => {
      expect(result.current.data?.pages.length).toBe(2)
    })

    expect(mockApi.getAnalyticsChangeLog).toHaveBeenCalledTimes(2)
    expect(result.current.data?.pages.at(-1)?.events).toEqual([{ id: 'event-2' }])
  })
})


