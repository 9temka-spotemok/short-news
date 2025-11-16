import { Activity, BarChart3, Clock, TrendingUp } from 'lucide-react'

import { ErrorBanner } from '@/components/ErrorBanner'
import ImpactTrendChart from '@/components/ImpactTrendChart'
import { LoadingOverlay } from '@/components/LoadingOverlay'
import MultiImpactTrendChart, {
  MultiImpactSeriesDescriptor
} from '@/components/MultiImpactTrendChart'
import type {
  Company,
  CompanyAnalyticsSnapshot,
  ComparisonSubjectSummary
} from '@/types'

type DailyActivityPoint = {
  date: string
  value: number
}

type PersistentMetricsBoardProps = {
  selectedCompany: Company
  analysisData: any
  comparisonData: any
  comparisonPeriod: 'daily' | 'weekly' | 'monthly'
  comparisonLookback: number
  comparisonLoading: boolean
  comparisonError: string | null
  subjectColorMap: Map<string, string>
  impactSnapshot: CompanyAnalyticsSnapshot | null
  impactSeries: { snapshots: CompanyAnalyticsSnapshot[] } | null
  focusedImpactPoint: CompanyAnalyticsSnapshot | null
  onComparisonPeriodChange: (period: 'daily' | 'weekly' | 'monthly') => void
  onComparisonLookbackChange: (lookback: number) => void
  onSnapshotHover: (snapshot: CompanyAnalyticsSnapshot | null) => void
}

export const PersistentMetricsBoard = ({
  selectedCompany,
  analysisData,
  comparisonData,
  comparisonPeriod,
  comparisonLookback,
  comparisonLoading,
  comparisonError,
  subjectColorMap,
  impactSnapshot,
  impactSeries,
  focusedImpactPoint,
  onComparisonPeriodChange,
  onComparisonLookbackChange,
  onSnapshotHover
}: PersistentMetricsBoardProps) => {
  if (!analysisData) {
    return (
      <div className="text-sm text-gray-500">
        Run analysis and select a company to see persistent metrics.
      </div>
    )
  }

  const companyId = selectedCompany.id
  const newsVolume = analysisData.metrics?.news_volume?.[companyId] ?? 0
  const activityScore = analysisData.metrics?.activity_score?.[companyId] ?? 0
  const avgPriority = analysisData.metrics?.avg_priority?.[companyId] ?? 0
  const competitorTotal = (analysisData.companies?.length ?? 1) - 1

  const dailyActivityRaw: Record<string, number> =
    analysisData.metrics?.daily_activity?.[companyId] ?? {}
  const dailyActivity: DailyActivityPoint[] = Object.entries(dailyActivityRaw)
    .map(([date, value]) => ({
      date,
      value: Number(value) || 0
    }))
    .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())
  const recentActivity = dailyActivity.slice(-14)
  const maxDailyValue = recentActivity.length
    ? Math.max(...recentActivity.map(item => item.value), 0)
    : 0

  const trendSnapshots = impactSeries?.snapshots ?? []
  const defaultImpact =
    impactSnapshot ||
    (trendSnapshots.length ? trendSnapshots[trendSnapshots.length - 1] : null)
  const highlightImpact =
    focusedImpactPoint && trendSnapshots.some(snapshot => snapshot.id === focusedImpactPoint.id)
      ? focusedImpactPoint
      : defaultImpact
  const highlightIndex = highlightImpact
    ? trendSnapshots.findIndex(snapshot => snapshot.id === highlightImpact.id)
    : -1
  const previousSnapshot = highlightIndex > 0 ? trendSnapshots[highlightIndex - 1] : null
  const highlightedScore = highlightImpact?.impact_score ?? null
  const impactDelta =
    highlightedScore !== null && previousSnapshot
      ? highlightedScore - previousSnapshot.impact_score
      : null
  const trendPercent =
    typeof highlightImpact?.trend_delta === 'number' ? highlightImpact.trend_delta * 100 : null
  const highlightDateLabel = highlightImpact
    ? new Date(highlightImpact.period_start).toLocaleDateString()
    : '—'
  const subjectSummariesByKey = comparisonData
    ? new Map<string, ComparisonSubjectSummary>(
        comparisonData.subjects.map((subject: ComparisonSubjectSummary) => [
          subject.subject_key,
          subject
        ])
      )
    : new Map<string, ComparisonSubjectSummary>()
  const seriesForChart: MultiImpactSeriesDescriptor[] = comparisonData
    ? comparisonData.series
        .filter((entry: { snapshots: CompanyAnalyticsSnapshot[] }) => entry.snapshots.length > 0)
        .map((entry: { subject_key: string; snapshots: CompanyAnalyticsSnapshot[] }) => ({
          subjectKey: entry.subject_key,
          label:
            (subjectSummariesByKey.get(entry.subject_key) as { label?: string } | undefined)
              ?.label || entry.subject_key,
          color: subjectColorMap.get(entry.subject_key) || '#2563eb',
          points: entry.snapshots
        }))
    : []

  return (
    <div className="space-y-4">
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-4 space-y-4">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <h3 className="text-base sm:text-lg font-semibold text-gray-900">Comparison dashboard</h3>
            <p className="text-xs sm:text-sm text-gray-500">Aggregated metrics for selected companies</p>
          </div>
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 sm:gap-3">
            <label className="flex items-center gap-2 text-xs sm:text-sm text-gray-600">
              Period
              <select
                value={comparisonPeriod}
                onChange={event =>
                  onComparisonPeriodChange(event.target.value as 'daily' | 'weekly' | 'monthly')
                }
                className="flex-1 sm:flex-none rounded-md border border-gray-300 px-2 py-1.5 text-xs sm:text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
                <option value="monthly">Monthly</option>
              </select>
            </label>
            <label className="flex items-center gap-2 text-xs sm:text-sm text-gray-600">
              Lookback
              <select
                value={comparisonLookback}
                onChange={event => onComparisonLookbackChange(Number(event.target.value))}
                className="flex-1 sm:flex-none rounded-md border border-gray-300 px-2 py-1.5 text-xs sm:text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                <option value={30}>30 days</option>
                <option value={60}>60 days</option>
                <option value={90}>90 days</option>
              </select>
            </label>
          </div>
        </div>

        {comparisonError ? (
          <ErrorBanner className="text-xs" compact message={comparisonError} />
        ) : null}

        {comparisonLoading ? (
          <LoadingOverlay
            className="py-10"
            label="Loading comparison data…"
            description="Aggregating persistent metrics across selected subjects"
          />
        ) : comparisonData ? (
          <div className="space-y-4">
            {seriesForChart.length > 0 ? (
              <div className="overflow-hidden">
                <MultiImpactTrendChart series={seriesForChart} height={119} />
              </div>
            ) : (
              <p className="text-sm text-gray-500">
                Not enough snapshot data yet to render combined trend. Run analysis to build history.
              </p>
            )}

            <div className="overflow-x-auto -mx-4 sm:mx-0">
              <div className="inline-block min-w-full align-middle">
                <div className="overflow-hidden">
                  <table className="min-w-full divide-y divide-gray-200 text-xs sm:text-sm">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-2 sm:px-4 py-2 text-left font-semibold text-gray-700 whitespace-nowrap">Subject</th>
                        <th className="px-2 sm:px-4 py-2 text-left font-semibold text-gray-700 whitespace-nowrap">Impact</th>
                        <th className="px-2 sm:px-4 py-2 text-left font-semibold text-gray-700 whitespace-nowrap">Trend Δ</th>
                        <th className="px-2 sm:px-4 py-2 text-left font-semibold text-gray-700 whitespace-nowrap">News</th>
                        <th className="px-2 sm:px-4 py-2 text-left font-semibold text-gray-700 whitespace-nowrap">Activity</th>
                        <th className="px-2 sm:px-4 py-2 text-left font-semibold text-gray-700 whitespace-nowrap">Priority</th>
                        <th className="px-2 sm:px-4 py-2 text-left font-semibold text-gray-700 whitespace-nowrap hidden md:table-cell">Innovation</th>
                        <th className="px-2 sm:px-4 py-2 text-left font-semibold text-gray-700 whitespace-nowrap hidden lg:table-cell">Positive</th>
                        <th className="px-2 sm:px-4 py-2 text-left font-semibold text-gray-700 whitespace-nowrap hidden lg:table-cell">Negative</th>
                        <th className="px-2 sm:px-4 py-2 text-left font-semibold text-gray-700 whitespace-nowrap hidden md:table-cell">Knowledge</th>
                        <th className="px-2 sm:px-4 py-2 text-left font-semibold text-gray-700 whitespace-nowrap hidden md:table-cell">Changes</th>
                      </tr>
                    </thead>
                <tbody className="divide-y divide-gray-100">
                  {comparisonData.metrics.map((metric: any) => {
                    const subject = subjectSummariesByKey.get(metric.subject_key)
                    const snapshot = metric.snapshot
                    const knowledgeCount =
                      comparisonData.knowledge_graph?.[metric.subject_key]?.length ?? 0
                    const changeCount = comparisonData.change_log?.[metric.subject_key]?.length ?? 0
                    const trendDelta = metric.trend_delta ?? 0
                    return (
                      <tr key={metric.subject_key} className="hover:bg-gray-50">
                        <td className="whitespace-nowrap px-2 sm:px-4 py-2 font-medium text-gray-900">
                          <div className="flex items-center gap-1.5 sm:gap-2">
                            <span
                              className="inline-block h-2 w-2 rounded-sm flex-shrink-0"
                              style={{
                                backgroundColor:
                                  subjectColorMap.get(metric.subject_key) || '#2563eb'
                              }}
                            />
                            <span className="truncate max-w-[100px] sm:max-w-none">{subject?.label || metric.subject_key}</span>
                          </div>
                        </td>
                        <td className="px-2 sm:px-4 py-2 whitespace-nowrap">{metric.impact_score.toFixed(2)}</td>
                        <td className="px-2 sm:px-4 py-2 whitespace-nowrap">
                          {trendDelta >= 0 ? '+' : ''}
                          {trendDelta.toFixed(2)}%
                        </td>
                        <td className="px-2 sm:px-4 py-2 whitespace-nowrap">{metric.news_volume}</td>
                        <td className="px-2 sm:px-4 py-2 whitespace-nowrap">{metric.activity_score.toFixed(2)}</td>
                        <td className="px-2 sm:px-4 py-2 whitespace-nowrap">{metric.avg_priority.toFixed(2)}</td>
                        <td className="px-2 sm:px-4 py-2 whitespace-nowrap hidden md:table-cell">{metric.innovation_velocity.toFixed(2)}</td>
                        <td className="px-2 sm:px-4 py-2 whitespace-nowrap hidden lg:table-cell">{snapshot?.news_positive ?? 0}</td>
                        <td className="px-2 sm:px-4 py-2 whitespace-nowrap hidden lg:table-cell">{snapshot?.news_negative ?? 0}</td>
                        <td className="px-2 sm:px-4 py-2 whitespace-nowrap hidden md:table-cell">{knowledgeCount}</td>
                        <td className="px-2 sm:px-4 py-2 whitespace-nowrap hidden md:table-cell">{changeCount}</td>
                      </tr>
                    )
                  })}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <p className="text-sm text-gray-500">
            Run analysis or add presets to build comparison dashboards.
          </p>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-4 rounded-lg border border-blue-100 bg-blue-50">
          <div className="flex items-center justify-between">
            <p className="text-xs uppercase font-semibold text-blue-700">Impact Score</p>
            <TrendingUp className="w-4 h-4 text-blue-600" />
          </div>
          <p className="text-2xl font-bold text-blue-900 mt-2">
            {highlightedScore !== null ? highlightedScore.toFixed(2) : 'n/a'}
          </p>
          <p className="text-xs text-blue-700 mt-1">
            {impactDelta !== null
              ? `${impactDelta >= 0 ? '+' : ''}${impactDelta.toFixed(2)} vs previous`
              : 'Awaiting history for comparison'}
          </p>
        </div>

        <div className="p-4 rounded-lg border border-emerald-100 bg-emerald-50">
          <div className="flex items-center justify-between">
            <p className="text-xs uppercase font-semibold text-emerald-700">Activity Score</p>
            <Activity className="w-4 h-4 text-emerald-600" />
          </div>
          <p className="text-2xl font-bold text-emerald-900 mt-2">{activityScore.toFixed(2)}</p>
          <p className="text-xs text-emerald-700 mt-1">
            Benchmarked vs {Math.max(competitorTotal, 0)} competitor
            {competitorTotal === 1 ? '' : 's'}
          </p>
        </div>

        <div className="p-4 rounded-lg border border-purple-100 bg-purple-50">
          <div className="flex items-center justify-between">
            <p className="text-xs uppercase font-semibold text-purple-700">News Volume (30d)</p>
            <BarChart3 className="w-4 h-4 text-purple-600" />
          </div>
          <p className="text-2xl font-bold text-purple-900 mt-2">{newsVolume}</p>
          <p className="text-xs text-purple-700 mt-1">
            Coverage across {analysisData.companies?.length ?? 1} tracked companies
          </p>
        </div>

        <div className="p-4 rounded-lg border border-amber-100 bg-amber-50">
          <div className="flex items-center justify-between">
            <p className="text-xs uppercase font-semibold text-amber-700">Signal Priority</p>
            <Clock className="w-4 h-4 text-amber-600" />
          </div>
          <p className="text-2xl font-bold text-amber-900 mt-2">
            {avgPriority ? avgPriority.toFixed(2) : '0.00'}
          </p>
          <p className="text-xs text-amber-700 mt-1">
            Average priority score of aggregated news
          </p>
        </div>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
          <div>
            <h4 className="text-sm font-semibold text-gray-800">Impact score trend</h4>
            <p className="text-xs text-gray-500">
              Hover or tap points to inspect specific snapshots and contributions.
            </p>
          </div>
          <div className="text-right">
            <p className="text-[10px] uppercase text-gray-400">Selected snapshot</p>
            <p className="text-lg font-semibold text-gray-900">
              {highlightedScore !== null ? highlightedScore.toFixed(2) : 'n/a'}
            </p>
            <p className="text-xs text-gray-500">{highlightDateLabel}</p>
          </div>
        </div>
        <div className="mt-3 overflow-hidden">
          {trendSnapshots.length > 0 ? (
            <ImpactTrendChart
              snapshots={trendSnapshots}
              height={119}
              onPointHover={(snapshot: CompanyAnalyticsSnapshot | null) => {
                if (snapshot) {
                  onSnapshotHover(snapshot)
                  return
                }
                if (impactSnapshot) {
                  onSnapshotHover(impactSnapshot)
                } else {
                  onSnapshotHover(null)
                }
              }}
            />
          ) : (
            <p className="text-xs text-gray-500">
              Not enough data points yet. Queue analytics recompute to build the historical timeline.
            </p>
          )}
        </div>
      </div>

      {trendPercent !== null && (
        <div
          className={`p-4 rounded-lg border ${
            trendPercent >= 0 ? 'border-green-100 bg-green-50' : 'border-rose-100 bg-rose-50'
          }`}
        >
          <div className="flex items-center space-x-2">
            <TrendingUp
              className={`w-4 h-4 ${trendPercent >= 0 ? 'text-green-600' : 'text-rose-600'}`}
            />
            <span className="text-sm font-semibold text-gray-800">
              {trendPercent >= 0 ? 'Positive trend' : 'Negative trend'}:{' '}
              {trendPercent >= 0 ? '+' : ''}
              {trendPercent.toFixed(1)}%
            </span>
          </div>
          <p className="text-xs text-gray-600 mt-1">
            Change of cumulative impact over the configured period.
          </p>
        </div>
      )}

      {recentActivity.length > 0 && (
      <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center space-x-2">
              <Activity className="w-4 h-4 text-blue-600" />
              <h4 className="text-sm font-semibold text-gray-800">30-day activity timeline</h4>
            </div>
            <span className="text-xs text-gray-500">
              Last {recentActivity.length} data points
            </span>
          </div>
          <div className="space-y-2 text-xs text-gray-600">
            {recentActivity.map(({ date, value }) => (
              <div key={date} className="flex items-center space-x-3">
                <span className="w-20 text-gray-500">{new Date(date).toLocaleDateString()}</span>
                <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
                  <div
                    className="h-2 bg-gradient-to-r from-blue-300 to-blue-600 rounded-full"
                    style={{
                      width: `${maxDailyValue ? Math.max(8, (value / maxDailyValue) * 100) : 8}%`
                    }}
                  />
                </div>
                <span className="w-10 text-right text-gray-500">{value}</span>
              </div>
            ))}
          </div>
        </div>
      )}

    </div>
  )
}

