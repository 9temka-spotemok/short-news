import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient } from '@tanstack/react-query'
import { describe, it, expect, beforeEach, vi } from 'vitest'

import { ApiService } from '@/services/api'
import { withQueryClient, createTestQueryClient } from '@/test/utils'
import { useKnowledgeGraph } from '../useKnowledgeGraph'

vi.mock('@/services/api')

const mockApi = vi.mocked(ApiService)

describe('useKnowledgeGraph', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    vi.resetAllMocks()
    queryClient = createTestQueryClient()
  })

  const renderUseKnowledgeGraph = (options = {}) =>
    renderHook(
      () =>
        useKnowledgeGraph({
          companyId: 'company-1',
          enabled: true,
          ...options,
        }),
      {
        wrapper: ({ children }) => withQueryClient(children, queryClient),
      }
    )

  it('fetches knowledge graph edges', async () => {
    mockApi.getAnalyticsGraph.mockResolvedValueOnce([
      {
        id: 'edge-1',
        relationship_type: 'partnership',
        source_entity_type: 'company',
        target_entity_type: 'product',
        confidence: 0.9,
        metadata: {},
      },
    ] as any)

    const { result } = renderUseKnowledgeGraph()

    await waitFor(() =>
      expect(result.current.data).toEqual(
        expect.arrayContaining([
          expect.objectContaining({ id: 'edge-1' }),
        ])
      )
    )

    expect(mockApi.getAnalyticsGraph).toHaveBeenCalledWith(
      'company-1',
      undefined,
      50
    )
  })
})













