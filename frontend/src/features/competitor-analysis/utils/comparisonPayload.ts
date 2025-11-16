import type {
  AnalyticsPeriod,
  ComparisonRequestPayload,
  ComparisonSubjectRequest
} from '../../../types'

type ComparisonRange = { from: string; to: string } | null

type FilterPayload = {
  source_types?: string[]
  topics?: string[]
  sentiments?: string[]
  min_priority?: number
}

type BuildComparisonPayloadArgs = {
  subjects: ComparisonSubjectRequest[]
  period: AnalyticsPeriod
  lookback: number
  range?: ComparisonRange
  filters?: FilterPayload
}

const hasDefinedFilters = (filters?: FilterPayload): boolean => {
  if (!filters) {
    return false
  }

  return Boolean(
    (filters.source_types && filters.source_types.length > 0) ||
      (filters.topics && filters.topics.length > 0) ||
      (filters.sentiments && filters.sentiments.length > 0) ||
      (filters.min_priority !== undefined && filters.min_priority !== null)
  )
}

export const buildComparisonPayload = ({
  subjects,
  period,
  lookback,
  range = null,
  filters
}: BuildComparisonPayloadArgs): ComparisonRequestPayload => {
  const payload: ComparisonRequestPayload = {
    subjects,
    period,
    lookback,
    include_series: true,
    include_components: true,
    include_change_log: true,
    include_knowledge_graph: true,
    change_log_limit: 8,
    knowledge_graph_limit: 20,
    top_news_limit: 6
  }

  if (range) {
    payload.date_from = range.from
    payload.date_to = range.to
  }

  if (hasDefinedFilters(filters)) {
    payload.filters = {
      topics: filters?.topics ?? [],
      sentiments: filters?.sentiments ?? [],
      source_types: filters?.source_types ?? [],
      min_priority: filters?.min_priority
    }
  }

  return payload
}












