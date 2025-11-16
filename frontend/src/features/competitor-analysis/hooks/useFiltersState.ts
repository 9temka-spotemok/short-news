import { useCallback, useMemo, useState } from 'react'

import { FilterOverrides, FilterStateSnapshot } from '../types'
import { applyFiltersToPayload, FilteredPayload } from '../utils/filterPayload'

type UseFiltersStateResult = {
  sourceTypeFilters: string[]
  topicFilters: string[]
  sentimentFilters: string[]
  minPriorityFilter: number | null
  hasActiveFilters: boolean
  toggleSourceType: (value: string) => void
  toggleTopic: (value: string) => void
  toggleSentiment: (value: string) => void
  updateMinPriority: (value: number | null) => void
  clearFilters: () => void
  setFilters: (overrides: FilterOverrides) => void
  applyFiltersToPayload: <T extends Record<string, unknown>>(
    payload: T,
    overrides?: FilterOverrides
  ) => FilteredPayload<T>
}

export const useFiltersState = (): UseFiltersStateResult => {
  const [sourceTypeFilters, setSourceTypeFilters] = useState<string[]>([])
  const [topicFilters, setTopicFilters] = useState<string[]>([])
  const [sentimentFilters, setSentimentFilters] = useState<string[]>([])
  const [minPriorityFilter, setMinPriorityFilter] = useState<number | null>(null)

  const snapshot = useMemo<FilterStateSnapshot>(
    () => ({
      sourceTypes: sourceTypeFilters,
      topics: topicFilters,
      sentiments: sentimentFilters,
      minPriority: minPriorityFilter
    }),
    [minPriorityFilter, sentimentFilters, sourceTypeFilters, topicFilters]
  )

  const hasActiveFilters = useMemo(
    () =>
      snapshot.sourceTypes.length > 0 ||
      snapshot.topics.length > 0 ||
      snapshot.sentiments.length > 0 ||
      snapshot.minPriority !== null,
    [snapshot]
  )

  const toggleSourceType = useCallback((value: string) => {
    setSourceTypeFilters(prev =>
      prev.includes(value) ? prev.filter(item => item !== value) : [...prev, value]
    )
  }, [])

  const toggleTopic = useCallback((value: string) => {
    setTopicFilters(prev =>
      prev.includes(value) ? prev.filter(item => item !== value) : [...prev, value]
    )
  }, [])

  const toggleSentiment = useCallback((value: string) => {
    setSentimentFilters(prev =>
      prev.includes(value) ? prev.filter(item => item !== value) : [...prev, value]
    )
  }, [])

  const updateMinPriority = useCallback((value: number | null) => {
    if (value === null || value <= 0) {
      setMinPriorityFilter(null)
      return
    }
    setMinPriorityFilter(Number(value.toFixed(2)))
  }, [])

  const clearFilters = useCallback(() => {
    setSourceTypeFilters([])
    setTopicFilters([])
    setSentimentFilters([])
    setMinPriorityFilter(null)
  }, [])

  const setFilters = useCallback(
    ({ sourceTypes, topics, sentiments, minPriority }: FilterOverrides) => {
      if (sourceTypes !== undefined) {
        setSourceTypeFilters(sourceTypes)
      }
      if (topics !== undefined) {
        setTopicFilters(topics)
      }
      if (sentiments !== undefined) {
        setSentimentFilters(sentiments)
      }
      if (minPriority !== undefined) {
        setMinPriorityFilter(minPriority ?? null)
      }
    },
    []
  )

  const applyFilters = useCallback(
    <T extends Record<string, unknown>>(
      payload: T,
      overrides?: FilterOverrides
    ): FilteredPayload<T> => applyFiltersToPayload(payload, snapshot, overrides),
    [snapshot]
  )

  return {
    sourceTypeFilters: snapshot.sourceTypes,
    topicFilters: snapshot.topics,
    sentimentFilters: snapshot.sentiments,
    minPriorityFilter: snapshot.minPriority,
    hasActiveFilters,
    toggleSourceType,
    toggleTopic,
    toggleSentiment,
    updateMinPriority,
    clearFilters,
    setFilters,
    applyFiltersToPayload: applyFilters
  }
}

