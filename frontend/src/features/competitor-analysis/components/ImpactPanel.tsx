import { BarChart3, Gauge, LineChart, Users } from 'lucide-react'
import { useState } from 'react'

import { ErrorBanner } from '@/components/ErrorBanner'
import { LoadingOverlay } from '@/components/LoadingOverlay'
import type { CompanyAnalyticsSnapshot, KnowledgeGraphEdge } from '../../../types'
import { formatLabel } from '../utils/formatters'

type ImpactPanelProps = {
  impactSnapshot: CompanyAnalyticsSnapshot | null
  impactSeries: { snapshots: CompanyAnalyticsSnapshot[] } | null
  analyticsEdges: KnowledgeGraphEdge[]
  analyticsLoading: boolean
  analyticsError: string | null
  onRecompute: () => void | Promise<void>
  onSyncKnowledgeGraph: () => void | Promise<void>
}

export const ImpactPanel = ({
  impactSnapshot,
  impactSeries,
  analyticsEdges,
  analyticsLoading,
  analyticsError,
  onRecompute,
  onSyncKnowledgeGraph
}: ImpactPanelProps) => {
  const [isRecomputing, setIsRecomputing] = useState(false)
  const [isSyncing, setIsSyncing] = useState(false)

  const recentSnapshots = impactSeries?.snapshots?.slice(-8) ?? []
  const maxImpact = recentSnapshots.length ? Math.max(...recentSnapshots.map(snapshot => snapshot.impact_score)) : 0
  const minImpact = recentSnapshots.length ? Math.min(...recentSnapshots.map(snapshot => snapshot.impact_score)) : 0
  const previousScore = recentSnapshots.length > 1 ? recentSnapshots[recentSnapshots.length - 2].impact_score : null
  const trendDeltaPercent =
    typeof impactSnapshot?.trend_delta === 'number' ? impactSnapshot.trend_delta * 100 : null
  const absoluteChange =
    previousScore !== null && impactSnapshot ? impactSnapshot.impact_score - previousScore : null

  const handleRecompute = async () => {
    setIsRecomputing(true)
    try {
      await onRecompute()
    } finally {
      setIsRecomputing(false)
    }
  }

  const handleSyncGraph = async () => {
    setIsSyncing(true)
    try {
      await onSyncKnowledgeGraph()
    } finally {
      setIsSyncing(false)
    }
  }

  if (!impactSnapshot && !analyticsLoading && !analyticsError) {
    return null
  }

  return (
    <div className="bg-white rounded-lg shadow-md border border-gray-200 p-6">
      <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4 mb-4">
        <div>
          <div className="flex items-center space-x-2">
            <Gauge className="w-5 h-5 text-blue-600" />
            <h3 className="text-lg font-semibold text-gray-900">Impact Score</h3>
          </div>
          <p className="text-xs text-gray-500 mt-1">
            Weighted blend of news, pricing and product signals for the selected company.
          </p>
          {impactSnapshot && (
            <p className="text-xs text-gray-400 mt-1">
              Snapshot range {new Date(impactSnapshot.period_start).toLocaleDateString()} —{' '}
              {new Date(impactSnapshot.period_end).toLocaleDateString()}
            </p>
          )}
        </div>
        <div className="flex items-center space-x-2">
          <button
            type="button"
            onClick={handleRecompute}
            disabled={isRecomputing || isSyncing}
            className="text-xs px-3 py-1.5 rounded-md border border-blue-200 text-blue-600 hover:bg-blue-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
          >
            {isRecomputing ? (
              <>
                <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-blue-600 mr-1.5" />
                Recomputing...
              </>
            ) : (
              'Recompute'
            )}
          </button>
          <button
            type="button"
            onClick={handleSyncGraph}
            disabled={!impactSnapshot || isRecomputing || isSyncing}
            className="text-xs px-3 py-1.5 rounded-md border border-indigo-200 text-indigo-600 hover:bg-indigo-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
          >
            {isSyncing ? (
              <>
                <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-indigo-600 mr-1.5" />
                Syncing...
              </>
            ) : (
              'Sync graph'
            )}
          </button>
        </div>
      </div>

      {analyticsError ? (
          <ErrorBanner
            className="mb-4 text-xs"
            compact
            message={analyticsError}
            onRetry={handleRecompute}
            retryLabel="Recompute"
          />
      ) : null}

      {analyticsLoading && !impactSnapshot ? (
        <LoadingOverlay
          className="py-6"
          label="Loading analytics insights…"
          description="Collecting the latest impact snapshot"
        />
      ) : impactSnapshot ? (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 rounded-lg bg-blue-50 border border-blue-100">
              <p className="text-xs uppercase text-blue-600 font-semibold">Impact Score</p>
              <p className="text-3xl font-bold text-blue-900 mt-2">{impactSnapshot.impact_score.toFixed(2)}</p>
              <p className="text-xs text-blue-700 mt-1">Composite score across signal types</p>
            </div>
            <div className="p-4 rounded-lg bg-emerald-50 border border-emerald-100">
              <p className="text-xs uppercase text-emerald-600 font-semibold">Trend</p>
              <p
                className={`text-3xl font-bold mt-2 ${
                  trendDeltaPercent !== null && trendDeltaPercent >= 0 ? 'text-emerald-700' : 'text-red-600'
                }`}
              >
                {trendDeltaPercent !== null ? `${trendDeltaPercent >= 0 ? '+' : ''}${trendDeltaPercent.toFixed(1)}%` : 'n/a'}
              </p>
              <p className="text-xs text-emerald-700 mt-1">
                {absoluteChange !== null
                  ? `${absoluteChange >= 0 ? '+' : ''}${absoluteChange.toFixed(2)} points vs previous snapshot`
                  : 'Awaiting history for comparison'}
              </p>
            </div>
            <div className="p-4 rounded-lg bg-purple-50 border border-purple-100">
              <p className="text-xs uppercase text-purple-600 font-semibold">Signals</p>
              <p className="text-sm text-purple-700 mt-2">
                {impactSnapshot.news_total} news · {impactSnapshot.pricing_changes} pricing ·{' '}
                {impactSnapshot.feature_updates} features
              </p>
              <p className="text-xs text-purple-500 mt-1">
                Sentiment balance {(impactSnapshot.news_average_sentiment * 100).toFixed(1)}%
              </p>
            </div>
          </div>

          <div className="mt-6 grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div className="border border-gray-200 rounded-lg p-4">
              <h4 className="text-sm font-semibold text-gray-800 mb-3 flex items-center">
                <BarChart3 className="w-4 h-4 text-blue-500 mr-2" />
                Impact breakdown
              </h4>
              <div className="space-y-2">
                {(impactSnapshot.components || []).slice(0, 4).map(component => (
                  <div key={component.id} className="flex items-center justify-between text-sm">
                    <div>
                      <p className="font-medium text-gray-800">{formatLabel(component.component_type)}</p>
                      <p className="text-xs text-gray-500">Weight {(component.weight * 100).toFixed(0)}%</p>
                    </div>
                    <div className="text-right">
                      <p className="font-semibold text-gray-900">{component.score_contribution.toFixed(2)}</p>
                      {component.metadata?.pricing_changes !== undefined && (
                        <p className="text-xs text-gray-500">{component.metadata.pricing_changes} pricing changes</p>
                      )}
                      {component.metadata?.feature_updates !== undefined && (
                        <p className="text-xs text-gray-500">{component.metadata.feature_updates} feature updates</p>
                      )}
                    </div>
                  </div>
                ))}
                {(!impactSnapshot.components || impactSnapshot.components.length === 0) && (
                  <p className="text-xs text-gray-500">Recompute analytics to populate component breakdown.</p>
                )}
              </div>
            </div>

            <div className="border border-gray-200 rounded-lg p-4">
              <h4 className="text-sm font-semibold text-gray-800 mb-3 flex items-center">
                <LineChart className="w-4 h-4 text-purple-500 mr-2" />
                Recent trend
              </h4>
              {recentSnapshots.length === 0 ? (
                <p className="text-xs text-gray-500">No historical snapshots yet.</p>
              ) : (
                <div className="space-y-2">
                  {recentSnapshots.map(snapshot => {
                    const normalized =
                      maxImpact !== minImpact ? (snapshot.impact_score - minImpact) / (maxImpact - minImpact) : 0.5

                    return (
                      <div key={snapshot.id}>
                        <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
                          <span>{new Date(snapshot.period_start).toLocaleDateString()}</span>
                          <span className="font-medium text-gray-800">{snapshot.impact_score.toFixed(2)}</span>
                        </div>
                        <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                          <div
                            className="h-2 bg-gradient-to-r from-blue-400 to-blue-600 rounded-full"
                            style={{ width: `${Math.max(10, normalized * 100)}%` }}
                          />
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          </div>

          {analyticsEdges.length > 0 && (
            <div className="mt-6 border border-gray-200 rounded-lg p-4">
              <h4 className="text-sm font-semibold text-gray-800 mb-3 flex items-center">
                <Users className="w-4 h-4 text-indigo-500 mr-2" />
                Knowledge graph links
              </h4>
              <div className="space-y-2 text-xs text-gray-600">
                {analyticsEdges.slice(0, 5).map(edge => (
                  <div
                    key={edge.id}
                    className="flex flex-col sm:flex-row sm:items-center sm:justify-between border-b border-gray-100 pb-2 last:border-b-0 gap-1"
                  >
                    <div>
                      <span className="font-semibold text-gray-800">{formatLabel(edge.source_entity_type)}</span>
                      <span className="mx-2 text-gray-400">→</span>
                      <span className="font-semibold text-gray-800">{formatLabel(edge.target_entity_type)}</span>
                      <span className="ml-2 text-gray-500">
                        ({formatLabel(edge.relationship_type)} · {(edge.confidence * 100).toFixed(0)}%)
                      </span>
                    </div>
                    <div className="flex items-center space-x-2 text-gray-400">
                      {edge.metadata?.category && <span>{formatLabel(edge.metadata.category)}</span>}
                      {edge.metadata?.change_detected_at && (
                        <span>{new Date(edge.metadata.change_detected_at).toLocaleDateString()}</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      ) : null}
    </div>
  )
}

