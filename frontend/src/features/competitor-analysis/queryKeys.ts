import type {
  AnalyticsPeriod,
  ComparisonFilters,
  ComparisonRequestPayload,
  ComparisonSubjectRequest,
} from '@/types'
import type { FilterStateSnapshot } from './types'
import type { ChangeProcessingStatus } from '@/types'

type Nullable<T> = T | null | undefined

const rootKey = ['competitor-analysis'] as const

const serializeSubjects = (subjects: ComparisonSubjectRequest[]) =>
  subjects
    .map(subject => `${subject.subject_type}:${subject.reference_id}`)
    .sort()
    .join('|')

const serializeFilters = (filters?: ComparisonFilters) => ({
  topics: filters?.topics?.slice().sort().join(',') ?? null,
  sentiments: filters?.sentiments?.slice().sort().join(',') ?? null,
  source_types: filters?.source_types?.slice().sort().join(',') ?? null,
  min_priority: filters?.min_priority ?? null,
})

const serializeFilterState = (filters?: FilterStateSnapshot) => ({
  topics: filters?.topics.slice().sort().join(',') ?? null,
  sentiments: filters?.sentiments.slice().sort().join(',') ?? null,
  source_types: filters?.sourceTypes.slice().sort().join(',') ?? null,
  min_priority: filters?.minPriority ?? null,
})

export type ChangeLogKeyParams = {
  companyId?: string | null
  subjectKey?: string | null
  period?: AnalyticsPeriod | null
  filterState?: FilterStateSnapshot
  limit?: number
}

export type KnowledgeGraphKeyParams = {
  companyId?: string | null
  relationship?: string | null
  limit?: number
}

export const competitorAnalysisKeys = {
  all: rootKey,
  reportPresets: () => [...rootKey, 'report-presets'] as const,
  comparison: (payload: ComparisonRequestPayload) => {
    const serialized = serializeFilters(payload.filters)
    return [
      ...rootKey,
      'comparison',
      payload.period ?? null,
      payload.lookback ?? null,
      payload.date_from ?? null,
      payload.date_to ?? null,
      serializeSubjects(payload.subjects),
      serialized.topics,
      serialized.sentiments,
      serialized.source_types,
      serialized.min_priority,
    ] as const
  },
  changeEvents: (
    companyId: Nullable<string>,
    limit: number,
    status?: ChangeProcessingStatus
  ) => [...rootKey, 'change-events', companyId ?? null, limit, status ?? 'all'] as const,
  changeLog: ({
    companyId,
    subjectKey,
    period,
    filterState,
    limit,
  }: ChangeLogKeyParams) => {
    const serialized = serializeFilterState(filterState)
    return [
      ...rootKey,
      'change-log',
      companyId ?? null,
      subjectKey ?? null,
      period ?? null,
      limit ?? null,
      serialized.topics,
      serialized.sentiments,
      serialized.source_types,
      serialized.min_priority,
    ] as const
  },
  companyAnalytics: (companyId: string | null) =>
    [...rootKey, 'company-analytics', companyId] as const,
  knowledgeGraph: ({ companyId, relationship, limit }: KnowledgeGraphKeyParams) =>
    [
      ...rootKey,
      'knowledge-graph',
      companyId ?? null,
      relationship ?? null,
      limit ?? null,
    ] as const,
}

export const serializeComparisonFilters = serializeFilters
export const serializeComparisonSubjects = serializeSubjects


