import { renderHook, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

import { ApiService } from '@/services/api'
import type { Company, ReportPreset } from '@/types'
import { useReportPresetActions } from '../useReportPresetActions'

vi.mock('@/services/api')
vi.mock('react-hot-toast', () => {
  const success = vi.fn()
  const error = vi.fn()
  return {
    default: { success, error },
    success,
    error,
  }
})

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

const defaultFilters = {
  sourceTypes: [],
  topics: [],
  sentiments: [],
  minPriority: null,
}

describe('useReportPresetActions', () => {
  const refetchReportPresets = vi.fn().mockResolvedValue(undefined)
  const setAnalysisMode = vi.fn()
  const setSelectedCompany = vi.fn()
  const setSelectedCompetitors = vi.fn()
  const setManuallyAddedCompetitors = vi.fn()
  const setSuggestedCompetitors = vi.fn()
  const setFilters = vi.fn()
  const runAnalysis = vi.fn().mockResolvedValue(undefined)

  const renderUseReportPresetActions = (overrides = {}) =>
    renderHook(() =>
      useReportPresetActions({
        selectedCompany: primaryCompany,
        selectedCompetitors: [competitorCompany.id],
        filtersState: defaultFilters,
        refetchReportPresets,
        setAnalysisMode,
        setSelectedCompany,
        setSelectedCompetitors,
        setManuallyAddedCompetitors,
        setSuggestedCompetitors,
        setFilters,
        runAnalysis,
        ...overrides,
      })
    )

  beforeEach(() => {
    vi.resetAllMocks()
  })

  afterEach(() => {
    refetchReportPresets.mockClear()
    setAnalysisMode.mockClear()
    setSelectedCompany.mockClear()
    setSelectedCompetitors.mockClear()
    setManuallyAddedCompetitors.mockClear()
    setSuggestedCompetitors.mockClear()
    setFilters.mockClear()
    runAnalysis.mockClear()
  })

  it('creates preset and resets name', async () => {
    mockApi.createReportPreset.mockResolvedValueOnce({} as ReportPreset)

    const { result } = renderUseReportPresetActions()

    act(() => {
      result.current.setNewPresetName('  Analysts ')
    })

    await act(async () => {
      await result.current.createPreset()
    })

    expect(mockApi.createReportPreset).toHaveBeenCalledWith(
      expect.objectContaining({
        name: 'Analysts',
        companies: ['1', '2'],
      })
    )
    expect(refetchReportPresets).toHaveBeenCalled()
    expect(result.current.newPresetName).toBe('')
  })

  it('applies preset and runs analysis', async () => {
    mockApi.getCompaniesByIds.mockResolvedValueOnce([primaryCompany, competitorCompany])

    const preset: ReportPreset = {
      id: 'preset-1',
      user_id: 'u1',
      name: 'Competitors',
      description: '',
      companies: ['1', '2'],
      filters: {},
      visualization_config: {},
      is_favorite: false,
      created_at: '',
      updated_at: '',
    }

    const { result } = renderUseReportPresetActions({
      reportPresets: [preset],
    })

    await act(async () => {
      await result.current.applyPreset(preset)
    })

    expect(mockApi.getCompaniesByIds).toHaveBeenCalledWith(['1', '2'])
    expect(setAnalysisMode).toHaveBeenCalledWith('custom')
    expect(setSelectedCompany).toHaveBeenCalledWith(primaryCompany)
    expect(setSelectedCompetitors).toHaveBeenCalledWith(['2'])
    expect(runAnalysis).toHaveBeenCalledWith(
      expect.objectContaining({
        primaryCompany,
        competitorIds: ['2'],
      })
    )
  })
})













