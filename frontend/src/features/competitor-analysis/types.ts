export type FilterStateSnapshot = {
  sourceTypes: string[]
  topics: string[]
  sentiments: string[]
  minPriority: number | null
}

export type FilterOverrides = Partial<FilterStateSnapshot>

export type FiltersStateReturn = FilterStateSnapshot & {
  hasActiveFilters: boolean
}












