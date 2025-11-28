import { History, Newspaper, Sparkles, TrendingUp } from 'lucide-react'

import ThemeAnalysis from '@/components/ThemeAnalysis'
import MonitoringSourcesCard from '@/components/monitoring/MonitoringSourcesCard'
import { ApiService } from '@/services/api'
import type {
    Company,
    CompanyAnalyticsSnapshot,
    ComparisonMetricSummary,
    ComparisonSubjectRequest,
    ComparisonSubjectSummary,
    CompetitorChangeEvent,
    KnowledgeGraphEdge,
    NewsItem,
    ReportPreset,
} from '@/types'
import { useQuery } from '@tanstack/react-query'
import { formatLabel } from '../utils/formatters'

type AbSelection = {
  left: string | null
  right: string | null
}

type CurrentSignalsBoardProps = {
  selectedCompany: Company
  analysisData: any
  themesData: any
  comparisonData: any
  comparisonSubjects: ComparisonSubjectRequest[]
  comparisonLoading: boolean
  analyticsEdges: KnowledgeGraphEdge[]
  impactSnapshot: CompanyAnalyticsSnapshot | null
  reportPresets: ReportPreset[]
  pendingPresetId: string
  onPendingPresetChange: (value: string) => void
  onAddPresetToComparison: (presetId: string) => void
  abSelection: AbSelection
  onAbSelectionChange: (position: 'left' | 'right', subjectKey: string) => void
  subjectColorMap: Map<string, string>
}

export const CurrentSignalsBoard = ({
  selectedCompany,
  analysisData,
  themesData,
  comparisonData,
  comparisonSubjects,
  comparisonLoading,
  analyticsEdges,
  impactSnapshot,
  reportPresets,
  pendingPresetId,
  onPendingPresetChange,
  onAddPresetToComparison,
  abSelection,
  onAbSelectionChange,
  subjectColorMap,
}: CurrentSignalsBoardProps) => {
  if (!analysisData) {
    return (
      <div className="text-sm text-gray-500">
        Run analysis and select a company to review live signals.
      </div>
    )
  }

  const companyId = selectedCompany.id
  const topNews = (analysisData.metrics?.top_news?.[companyId] ?? []) as NewsItem[]
  const newsPreview = topNews.slice(0, 4)
  const highPriorityNews = newsPreview.filter(item => item.priority_level === 'High').length
  const components = (impactSnapshot?.components ?? []).slice(0, 4)
  const highConfidenceEdges = analyticsEdges.slice(0, 5)
  const trendPercent =
    typeof impactSnapshot?.trend_delta === 'number' ? impactSnapshot.trend_delta * 100 : null
  const comparisonSubjectsAvailable = comparisonData?.subjects ?? []
  const subjectSummariesByKey = comparisonData
    ? new Map<string, ComparisonSubjectSummary>(
        comparisonData.subjects.map((subject: ComparisonSubjectSummary) => [
          subject.subject_key,
          subject,
        ])
      )
    : new Map<string, ComparisonSubjectSummary>()
  const metricsMap = comparisonData
    ? new Map<string, ComparisonMetricSummary>(
        comparisonData.metrics.map((metric: ComparisonMetricSummary) => [
          metric.subject_key,
          metric,
        ])
      )
    : new Map<string, ComparisonMetricSummary>()
  const knowledgeMap = comparisonData?.knowledge_graph ?? {}
  const changeLogMap = comparisonData?.change_log ?? {}
  const availablePresetOptions = reportPresets.filter(
    preset =>
      !comparisonSubjects.some(
        subject => subject.subject_type === 'preset' && subject.reference_id === preset.id
      )
  )

  const resolvedLeft = (() => {
    if (!comparisonData) return null
    if (abSelection.left && metricsMap.has(abSelection.left)) {
      return abSelection.left
    }
    return comparisonSubjectsAvailable[0]?.subject_key ?? null
  })()

  const resolvedRight = (() => {
    if (!comparisonData) return null
    if (abSelection.right && metricsMap.has(abSelection.right)) {
      return abSelection.right
    }
    if (comparisonSubjectsAvailable.length > 1) {
      return (
        comparisonSubjectsAvailable[1]?.subject_key ??
        comparisonSubjectsAvailable[0]?.subject_key ??
        null
      )
    }
    return comparisonSubjectsAvailable[0]?.subject_key ?? null
  })()

  const renderAbCard = (subjectKey: string | null, title: string) => {
    if (!subjectKey || !comparisonData) {
      return (
        <div className="flex-1 rounded-lg border border-dashed border-gray-300 p-4 text-sm text-gray-500">
          Select a subject to compare.
        </div>
      )
    }
    const subject = subjectSummariesByKey.get(subjectKey)
    const metric = metricsMap.get(subjectKey)
    const knowledgeCount = knowledgeMap[subjectKey]?.length ?? 0
    const changeEvents = (changeLogMap[subjectKey] ?? []).slice(0, 3)
    const topSignals = (metric?.top_news ?? []).slice(0, 3)
    const trendDelta = metric?.trend_delta ?? null

    return (
      <div className="flex-1 rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs uppercase text-gray-500">{title}</p>
            <h4 className="text-base font-semibold text-gray-900">{subject?.label || subjectKey}</h4>
          </div>
          <span
            className="inline-block h-2 w-2 rounded-sm"
            style={{ backgroundColor: subjectColorMap.get(subjectKey) || '#2563eb' }}
            aria-hidden="true"
          />
        </div>
        <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
          <div>
            <p className="text-xs text-gray-500">Impact Score</p>
            <p className="text-lg font-semibold text-gray-900">
              {metric ? metric.impact_score.toFixed(2) : '—'}
            </p>
            <p
              className={`text-xs ${
                trendDelta !== null && trendDelta >= 0 ? 'text-emerald-600' : 'text-rose-600'
              }`}
            >
              {trendDelta !== null ? `${trendDelta >= 0 ? '+' : ''}${trendDelta.toFixed(2)}%` : '—'}
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Signals</p>
            <p className="text-lg font-semibold text-gray-900">{knowledgeCount}</p>
            <p className="text-xs text-gray-500">Knowledge graph edges</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">News Volume</p>
            <p className="text-lg font-semibold text-gray-900">{metric?.news_volume ?? '—'}</p>
            <p className="text-xs text-gray-500">
              Activity: {metric?.activity_score?.toFixed(2) ?? '—'}
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Change Log</p>
            <p className="text-lg font-semibold text-gray-900">{changeEvents.length}</p>
            <p className="text-xs text-gray-500">Recent events tracked</p>
          </div>
        </div>
        <div className="mt-4 space-y-3">
          <div>
            <p className="text-xs font-semibold uppercase text-gray-500 mb-1">Top signals</p>
            <div className="space-y-2">
              {topSignals.length ? (
                topSignals.map(news => (
                  <div key={news.id} className="rounded border border-gray-200 px-3 py-2 text-xs text-gray-600">
                    <p className="font-semibold text-gray-800">{news.title}</p>
                    <div className="mt-1 flex flex-wrap gap-2">
                      {news.category && (
                        <span className="rounded bg-blue-50 px-2 py-0.5 text-blue-600">
                          {formatLabel(news.category)}
                        </span>
                      )}
                      {news.sentiment && (
                        <span className="rounded bg-emerald-50 px-2 py-0.5 text-emerald-600">
                          {formatLabel(news.sentiment)}
                        </span>
                      )}
                      <span>{new Date(news.published_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                ))
              ) : (
                <p className="text-xs text-gray-500">No top signals yet.</p>
              )}
            </div>
          </div>
          <div>
            <p className="text-xs font-semibold uppercase text-gray-500 mb-1">Recent changes</p>
            <div className="space-y-2">
              {changeEvents.length ? (
                changeEvents.map((event: CompetitorChangeEvent) => (
                  <div key={event.id} className="rounded border border-gray-200 px-3 py-2 text-xs text-gray-600">
                    <p className="font-semibold text-gray-800">{event.change_summary}</p>
                    <p className="mt-1 text-gray-500">{new Date(event.detected_at).toLocaleString()}</p>
                  </div>
                ))
              ) : (
                <p className="text-xs text-gray-500">No change events collected.</p>
              )}
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {comparisonData && comparisonSubjectsAvailable.length > 0 && (
        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm space-y-4">
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div>
              <h3 className="text-lg font-semibold text-gray-900">Signals A/B comparison</h3>
              <p className="text-sm text-gray-500">
                Compare live signals, knowledge graph edges, and change log across selected subjects.
              </p>
            </div>
            <div className="flex flex-wrap gap-3">
              <select
                value={resolvedLeft ?? ''}
                onChange={event => onAbSelectionChange('left', event.target.value)}
                className="rounded-md border border-gray-300 px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                {comparisonSubjectsAvailable.map((subject: ComparisonSubjectSummary) => (
                  <option key={subject.subject_key} value={subject.subject_key}>
                    {subject.label}
                  </option>
                ))}
              </select>
              <select
                value={resolvedRight ?? ''}
                onChange={event => onAbSelectionChange('right', event.target.value)}
                className="rounded-md border border-gray-300 px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                {comparisonSubjectsAvailable.map((subject: ComparisonSubjectSummary) => (
                  <option key={subject.subject_key} value={subject.subject_key}>
                    {subject.label}
                  </option>
                ))}
              </select>
              <div className="flex items-center gap-2">
                <select
                  value={pendingPresetId}
                  onChange={event => onPendingPresetChange(event.target.value)}
                  className="rounded-md border border-gray-300 px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                >
                  <option value="">Add preset…</option>
                  {availablePresetOptions.map(preset => (
                    <option key={preset.id} value={preset.id}>
                      {preset.name}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={() => onAddPresetToComparison(pendingPresetId)}
                  className="rounded-md border border-primary-200 px-3 py-1 text-xs font-medium text-primary-600 transition-colors hover:bg-primary-50 disabled:opacity-50"
                  disabled={!pendingPresetId}
                >
                  Add
                </button>
              </div>
            </div>
          </div>

          {comparisonLoading ? (
            <div className="py-6 text-center text-sm text-gray-500">
              <div className="mx-auto mb-3 h-5 w-5 animate-spin rounded-full border-2 border-blue-200 border-t-blue-600" />
              Updating A/B metrics…
            </div>
          ) : (
            <div className="flex flex-col gap-4 md:flex-row">
              {renderAbCard(resolvedLeft, 'Variant A')}
              {renderAbCard(resolvedRight, 'Variant B')}
            </div>
          )}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div
          className={`p-4 rounded-lg border ${
            trendPercent !== null && trendPercent < 0
              ? 'border-rose-100 bg-rose-50'
              : 'border-emerald-100 bg-emerald-50'
          }`}
        >
          <div className="flex items-center justify-between">
            <p className="text-xs uppercase font-semibold text-gray-700">Trend Direction</p>
            <TrendingUp
              className={`w-4 h-4 ${
                trendPercent !== null && trendPercent < 0 ? 'text-rose-600' : 'text-emerald-600'
              }`}
            />
          </div>
          <p className="text-2xl font-bold mt-2 text-gray-900">
            {trendPercent !== null ? `${trendPercent >= 0 ? '+' : ''}${trendPercent.toFixed(1)}%` : 'n/a'}
          </p>
          <p className="text-xs text-gray-600 mt-1">
            Based on weighted sentiment, pricing and product signals.
          </p>
        </div>

        <div className="p-4 rounded-lg border border-indigo-100 bg-indigo-50">
          <div className="flex items-center justify-between">
            <p className="text-xs uppercase font-semibold text-indigo-700">Knowledge Links</p>
            <Sparkles className="w-4 h-4 text-indigo-600" />
          </div>
          <p className="text-2xl font-bold text-indigo-900 mt-2">{analyticsEdges.length}</p>
          <p className="text-xs text-indigo-700 mt-1">
            Knowledge graph relations discovered this period.
          </p>
        </div>

        <div className="p-4 rounded-lg border border-orange-100 bg-orange-50">
          <div className="flex items-center justify-between">
            <p className="text-xs uppercase font-semibold text-orange-700">Tracked Changes</p>
            <History className="w-4 h-4 text-orange-600" />
          </div>
          <p className="text-2xl font-bold text-orange-900 mt-2">{changeLogMap[selectedCompany.id]?.length ?? 0}</p>
          <p className="text-xs text-orange-700 mt-1">
            Pricing & feature updates in monitoring queue.
          </p>
        </div>

        <div className="p-4 rounded-lg border border-rose-100 bg-rose-50">
          <div className="flex items-center justify-between">
            <p className="text-xs uppercase font-semibold text-rose-700">High-priority News</p>
            <Newspaper className="w-4 h-4 text-rose-600" />
          </div>
          <p className="text-2xl font-bold text-rose-900 mt-2">{highPriorityNews}</p>
          <p className="text-xs text-rose-700 mt-1">
            High-priority articles from the latest batch of signals.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-white rounded-lg border border-gray-200 p-5">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center space-x-2">
              <Newspaper className="w-4 h-4 text-blue-600" />
              <h4 className="text-sm font-semibold text-gray-800">Top Recent News</h4>
            </div>
            <span className="text-xs text-gray-500">
              {newsPreview.length ? `${newsPreview.length} of ${topNews.length} shown` : 'No news yet'}
            </span>
          </div>
          {newsPreview.length > 0 ? (
            <div className="space-y-3 text-sm">
              {newsPreview.map(item => (
                <div key={item.id} className="border border-gray-100 rounded-md p-3 hover:border-blue-200 transition-colors">
                  <a
                    href={item.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-semibold text-gray-900 hover:text-blue-600"
                  >
                    {item.title}
                  </a>
                  <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-gray-500">
                    <span className="px-2 py-0.5 bg-blue-50 text-blue-600 rounded-full">
                      {item.priority_level} priority
                    </span>
                    {item.topic && (
                      <span className="px-2 py-0.5 bg-purple-50 text-purple-600 rounded-full">
                        {formatLabel(item.topic)}
                      </span>
                    )}
                    {item.sentiment && (
                      <span className="px-2 py-0.5 bg-emerald-50 text-emerald-600 rounded-full">
                        {formatLabel(item.sentiment)}
                      </span>
                    )}
                    <span>{new Date(item.published_at).toLocaleDateString()}</span>
                  </div>
                  {item.summary && (
                    <p className="text-xs text-gray-600 mt-2 line-clamp-2">
                      {item.summary}
                    </p>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-gray-500">
              No high-impact news has been ingested for the selected filters yet.
            </p>
          )}
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-5">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center space-x-2">
              <Sparkles className="w-4 h-4 text-indigo-500" />
              <h4 className="text-sm font-semibold text-gray-800">Impact Drivers & Graph Insights</h4>
            </div>
            <span className="text-xs text-gray-500">
              {highConfidenceEdges.length} graph links
            </span>
          </div>
          <div className="space-y-4">
            <div>
              <p className="text-xs uppercase font-semibold text-gray-500 mb-2">Impact contributors</p>
              {components.length > 0 ? (
                <div className="space-y-1">
                  {components.map(component => (
                    <div key={component.id} className="flex items-center justify-between text-xs text-gray-600">
                      <div>
                        <p className="font-medium text-gray-800">{formatLabel(component.component_type)}</p>
                        <p className="text-[11px] text-gray-500">
                          Weight {(component.weight * 100).toFixed(0)}%
                        </p>
                      </div>
                      <span className="px-2 py-0.5 rounded-full bg-gray-100 text-gray-700">
                        {component.score_contribution.toFixed(2)}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-gray-500">Run recompute to populate impact components.</p>
              )}
            </div>

            <div>
              <p className="text-xs uppercase font-semibold text-gray-500 mb-2">Knowledge graph highlights</p>
              {highConfidenceEdges.length > 0 ? (
                <div className="space-y-1 text-xs text-gray-600">
                  {highConfidenceEdges.map(edge => (
                    <div key={edge.id} className="flex items-center justify-between border border-gray-100 rounded-md p-2">
                      <div>
                        <p className="font-medium text-gray-800">
                          {formatLabel(edge.source_entity_type)} → {formatLabel(edge.target_entity_type)}
                        </p>
                        <p className="text-[11px] text-gray-500">
                          {formatLabel(edge.relationship_type)} · {(edge.confidence * 100).toFixed(0)}% confidence
                        </p>
                      </div>
                      <span className="text-[11px] text-gray-500">
                        {edge.metadata?.change_detected_at
                          ? new Date(edge.metadata.change_detected_at).toLocaleDateString()
                          : ''}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-gray-500">No graph edges detected for the selected filters yet.</p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Monitoring Sources Section */}
      {selectedCompany?.id && (
        <MonitoringSourcesSection companyId={selectedCompany.id} />
      )}

      {themesData && (
        <div className="bg-white rounded-lg shadow-md p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Theme Analysis
          </h3>
          <ThemeAnalysis themesData={themesData} companies={analysisData.companies} />
        </div>
      )}
    </div>
  )
}

// Monitoring Sources Section Component
function MonitoringSourcesSection({ companyId }: { companyId: string }) {
  const { data: monitoringMatrix, isLoading, error } = useQuery({
    queryKey: ['monitoring-matrix', companyId],
    queryFn: () => ApiService.getMonitoringMatrix(companyId),
    enabled: !!companyId,
    staleTime: 1000 * 60 * 5, // 5 minutes
  })

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-5">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/4 mb-4"></div>
          <div className="h-32 bg-gray-200 rounded"></div>
        </div>
      </div>
    )
  }

  if (error || !monitoringMatrix) {
    return null // Don't show error, just hide the section
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-5">
      <h3 className="text-sm font-semibold text-gray-800 mb-3">Monitoring Sources</h3>
      <MonitoringSourcesCard matrix={monitoringMatrix as any} />
    </div>
  )
}

