import { FilterOverrides, FilterStateSnapshot } from '../types'

export type FilteredPayload<T> = T & {
  source_types?: string[]
  topics?: string[]
  sentiments?: string[]
  min_priority?: number
}

const createSnapshot = (
  state: FilterStateSnapshot,
  overrides: FilterOverrides = {}
): FilterStateSnapshot => ({
  sourceTypes: overrides.sourceTypes ?? state.sourceTypes,
  topics: overrides.topics ?? state.topics,
  sentiments: overrides.sentiments ?? state.sentiments,
  minPriority:
    overrides.minPriority === undefined ? state.minPriority : overrides.minPriority
})

export const applyFiltersToPayload = <T extends Record<string, unknown>>(
  payload: T,
  state: FilterStateSnapshot,
  overrides?: FilterOverrides
): FilteredPayload<T> => {
  const snapshot = createSnapshot(state, overrides)

  const nextPayload: FilteredPayload<T> = { ...payload }

  if (snapshot.sourceTypes.length) {
    nextPayload.source_types = snapshot.sourceTypes
  }
  if (snapshot.topics.length) {
    nextPayload.topics = snapshot.topics
  }
  if (snapshot.sentiments.length) {
    nextPayload.sentiments = snapshot.sentiments
  }
  if (snapshot.minPriority !== null && snapshot.minPriority !== undefined) {
    nextPayload.min_priority = Number(snapshot.minPriority.toFixed(2))
  }

  return nextPayload
}












