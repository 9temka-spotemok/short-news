import { renderHook, act } from '@testing-library/react'
import { QueryClient } from '@tanstack/react-query'
import { vi, describe, it, expect, beforeEach } from 'vitest'

import { ApiService } from '@/services/api'
import type { Company } from '@/types'
import { withQueryClient, createTestQueryClient } from '@/test/utils'
import { useAnalysisFlow } from '../useAnalysisFlow'

vi.mock('@/services/api')

const mockApi = vi.mocked(ApiService)

const primaryCompany: Company = {
  id: '1',
  name: 'Acme',
  website: '',
  description: '',
  logo_url: '',
  category: '',
  twitter_handle: '',
  github_org: '',
  created_at: '',
  updated_at: '',
}

const competitorCompany: Company = {
  id: '2',
  name: 'Globex',
  website: '',
  description: '',
  logo_url: '',
  category: '',
  twitter_handle: '',
  github_org: '',
  created_at: '',
  updated_at: '',
}

const mockAnalysisResponse = {
  companies: [primaryCompany, competitorCompany],
}

const defaultFiltersState = {
  sourceTypes: [],
  topics: [],
  sentiments: [],
  minPriority: null,
}

describe('useAnalysisFlow', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    vi.resetAllMocks()
    queryClient = createTestQueryClient()
  })

  const noopApplyFiltersToPayload = (<T extends Record<string, unknown>>(payload: T) =>
    payload as any) as any

  const renderUseAnalysisFlow = (overrides = {}) =>
    renderHook(
      () =>
        useAnalysisFlow({
          applyFiltersToPayload: noopApplyFiltersToPayload,
          fetchComparisonData: vi.fn().mockResolvedValue(undefined),
          setComparisonRange: vi.fn(),
          resetComparison: vi.fn(),
          comparisonPeriod: 'daily',
          comparisonLookback: 30,
          filtersState: defaultFiltersState,
          ...overrides,
        }),
      {
        wrapper: ({ children }) => withQueryClient(children, queryClient),
      }
    )

  it('runs analysis and sets data', async () => {
    mockApi.compareCompanies.mockResolvedValueOnce(mockAnalysisResponse as any)
    mockApi.analyzeThemes.mockResolvedValueOnce({ themes: {} } as any)

    const { result } = renderUseAnalysisFlow()

    act(() => {
      result.current.setSelectedCompany(primaryCompany)
      result.current.setSelectedCompetitors([competitorCompany.id])
    })

    await act(async () => {
      await result.current.runAnalysis()
    })

    expect(mockApi.compareCompanies).toHaveBeenCalled()
    expect(result.current.analysisData).toEqual(mockAnalysisResponse)
  })

  it('handles error during analysis', async () => {
    mockApi.compareCompanies.mockRejectedValueOnce(new Error('fail'))

    const { result } = renderUseAnalysisFlow()

    await act(async () => {
      await result.current.runAnalysis()
    })

    expect(result.current.error).toEqual('fail')
  })

  it('suggests competitors', async () => {
    mockApi.suggestCompetitors.mockResolvedValueOnce({
      suggestions: [
        {
          company: competitorCompany,
          similarity_score: 0.9,
          common_categories: [],
          reason: 'mock',
        },
      ],
    } as any)

    const { result } = renderUseAnalysisFlow()

    act(() => {
      result.current.setSelectedCompany(primaryCompany)
    })

    await act(async () => {
      await result.current.loadCompetitorSuggestions()
    })

    expect(result.current.suggestedCompetitors).toHaveLength(1)
  })
})













