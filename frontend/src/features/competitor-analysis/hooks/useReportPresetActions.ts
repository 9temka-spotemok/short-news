import { useCallback, useState } from 'react'
import toast from 'react-hot-toast'

import { ApiService } from '@/services/api'
import type { Company, ReportPreset } from '@/types'
import type { FilterOverrides, FilterStateSnapshot } from '../types'
import type { RunAnalysisOverride } from './useAnalysisFlow'

type SuggestionsEntry = {
  company: Company
  similarity_score: number
  common_categories: string[]
  reason: string
}

type UseReportPresetActionsParams = {
  selectedCompany: Company | null
  selectedCompetitors: string[]
  filtersState: FilterStateSnapshot
  refetchReportPresets: () => Promise<unknown>
  setAnalysisMode: (mode: 'company' | 'custom' | null) => void
  setSelectedCompany: (company: Company | null) => void
  setSelectedCompetitors: (ids: string[]) => void
  setManuallyAddedCompetitors: (companies: Company[]) => void
  setSuggestedCompetitors: (entries: SuggestionsEntry[]) => void
  setFilters: (overrides: FilterOverrides) => void
  runAnalysis: (override?: RunAnalysisOverride) => Promise<void>
}

export const useReportPresetActions = ({
  selectedCompany,
  selectedCompetitors,
  filtersState,
  refetchReportPresets,
  setAnalysisMode,
  setSelectedCompany,
  setSelectedCompetitors,
  setManuallyAddedCompetitors,
  setSuggestedCompetitors,
  setFilters,
  runAnalysis
}: UseReportPresetActionsParams) => {
  const [newPresetName, setNewPresetName] = useState('')
  const [savingPreset, setSavingPreset] = useState(false)
  const [presetApplyingId, setPresetApplyingId] = useState<string | null>(null)

  const createPreset = useCallback(async () => {
    if (!selectedCompany) {
      toast.error('Select a primary company before saving a preset')
      return
    }

    const name = newPresetName.trim()
    if (!name) {
      toast.error('Preset name cannot be empty')
      return
    }

    const companyIds = [selectedCompany.id, ...selectedCompetitors]

    setSavingPreset(true)
    try {
      await ApiService.createReportPreset({
        name,
        companies: companyIds,
        filters: {
          source_types: filtersState.sourceTypes,
          topics: filtersState.topics,
          sentiments: filtersState.sentiments,
          min_priority: filtersState.minPriority
        },
        visualization_config: {
          impact_panel: true,
          comparison_chart: true
        }
      })
      toast.success('Report preset saved')
      setNewPresetName('')
      await refetchReportPresets()
    } catch (error: any) {
      console.error('Failed to save preset:', error)
      const message = error?.response?.data?.detail || error?.message || 'Failed to save preset'
      toast.error(message)
    } finally {
      setSavingPreset(false)
    }
  }, [filtersState, newPresetName, refetchReportPresets, selectedCompany, selectedCompetitors])

  const applyPreset = useCallback(
    async (preset: ReportPreset) => {
      if (!preset.companies || preset.companies.length === 0) {
        toast.error('Preset does not contain any companies')
        return
      }

      setPresetApplyingId(preset.id)

      try {
        const companies = await ApiService.getCompaniesByIds(preset.companies)
        if (!companies.length) {
          throw new Error('Preset companies could not be loaded')
        }

        const primaryId = preset.companies[0]
        const primaryCompany = companies.find(company => company.id === primaryId) ?? companies[0]

        if (!primaryCompany) {
          throw new Error('Primary company is missing in preset')
        }

        const competitorIds = preset.companies.filter(id => id !== primaryCompany.id)
        if (!competitorIds.length) {
          toast.error('Preset must include at least one competitor')
          setPresetApplyingId(null)
          return
        }

        const presetSourceTypes = Array.isArray(preset.filters?.source_types)
          ? (preset.filters?.source_types as string[])
          : []
        const presetTopics = Array.isArray(preset.filters?.topics)
          ? (preset.filters?.topics as string[])
          : []
        const presetSentiments = Array.isArray(preset.filters?.sentiments)
          ? (preset.filters?.sentiments as string[])
          : []
        const presetMinPriority =
          typeof preset.filters?.min_priority === 'number' ? preset.filters.min_priority : null

        const competitorCompanies = companies.filter(company => competitorIds.includes(company.id))

        setAnalysisMode('custom')
        setSelectedCompany(primaryCompany)
        setSelectedCompetitors(competitorIds)
        setManuallyAddedCompetitors(competitorCompanies)
        setSuggestedCompetitors(
          competitorCompanies.map(company => ({
            company,
            similarity_score: 0,
            common_categories: [],
            reason: 'Preset'
          }))
        )
        setFilters({
          sourceTypes: presetSourceTypes,
          topics: presetTopics,
          sentiments: presetSentiments,
          minPriority: presetMinPriority
        })

        await runAnalysis({
          primaryCompany,
          competitorIds,
          filters: {
            source_types: presetSourceTypes,
            topics: presetTopics,
            sentiments: presetSentiments,
            min_priority: presetMinPriority
          }
        })

        toast.success('Preset applied')
      } catch (error: any) {
        console.error('Failed to apply preset:', error)
        const message = error?.response?.data?.detail || error?.message || 'Failed to apply preset'
        toast.error(message)
      } finally {
        setPresetApplyingId(null)
      }
    },
    [
      runAnalysis,
      setAnalysisMode,
      setFilters,
      setManuallyAddedCompetitors,
      setSelectedCompany,
      setSelectedCompetitors,
      setSuggestedCompetitors
    ]
  )

  return {
    newPresetName,
    setNewPresetName,
    savingPreset,
    presetApplyingId,
    createPreset,
    applyPreset
  }
}













