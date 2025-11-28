import { useMemo } from 'react'

import type {
    AnalyticsPeriod,
    Company,
    CompanyAnalyticsSnapshot,
    ComparisonResponse,
    ComparisonSubjectRequest,
    ReportPreset,
    SnapshotSeries
} from '@/types'
import type { FilterStateSnapshot } from '../../types'

import MonitoringSourcesCard from '@/components/monitoring/MonitoringSourcesCard'
import { ApiService } from '@/services/api'
import { useQuery } from '@tanstack/react-query'
import { useChangeLog } from '../../hooks/useChangeLog'
import { useKnowledgeGraph } from '../../hooks/useKnowledgeGraph'
import { ActiveFiltersSummary, type ActiveFilters } from '../ActiveFiltersSummary'
import { ChangeEventsSection } from '../ChangeEventsSection'
import { CurrentSignalsBoard } from '../CurrentSignalsBoard'
import { PersistentMetricsBoard } from '../PersistentMetricsBoard'

export type AnalyticsTabsProps = {
  metricsTab: 'persistent' | 'signals'
  onTabChange: (tab: 'persistent' | 'signals') => void
  selectedCompany: Company | null
  analysisData: any
  themesData: any
  comparisonData: ComparisonResponse | null
  comparisonPeriod: AnalyticsPeriod
  comparisonLookback: number
  comparisonLoading: boolean
  comparisonError: string | null
  subjectColorMap: Map<string, string>
  impactSnapshot: CompanyAnalyticsSnapshot | null
  impactSeries: SnapshotSeries | null
  focusedImpactPoint: CompanyAnalyticsSnapshot | null
  onComparisonPeriodChange: (period: AnalyticsPeriod) => void
  onComparisonLookbackChange: (lookback: number) => void
  onSnapshotHover: (snapshot: CompanyAnalyticsSnapshot | null) => void
  filtersSnapshot: ActiveFilters
  comparisonSubjects: ComparisonSubjectRequest[]
  analyticsEdges: any[]
  reportPresets: ReportPreset[]
  pendingPresetId: string
  onPendingPresetChange: (value: string) => void
  onAddPresetToComparison: (presetId: string) => void
  abSelection: { left: string | null; right: string | null }
  onAbSelectionChange: (position: 'left' | 'right', subjectKey: string) => void
  changeEvents: any[]
  changeEventsLoading: boolean
  changeEventsError: string | null
  onRefreshChangeEvents: () => void
  onRecomputeChangeEvent: (eventId: string) => void
  recomputingEventId: string | null
}

export const AnalyticsTabs = ({
  metricsTab,
  onTabChange,
  selectedCompany,
  analysisData,
  themesData,
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
  onSnapshotHover,
  filtersSnapshot,
  comparisonSubjects,
  analyticsEdges,
  reportPresets,
  pendingPresetId,
  onPendingPresetChange,
  onAddPresetToComparison,
  abSelection,
  onAbSelectionChange,
  changeEvents,
  changeEventsLoading,
  changeEventsError,
  onRefreshChangeEvents,
  onRecomputeChangeEvent,
  recomputingEventId
}: AnalyticsTabsProps) => {
  const tabs = useMemo(
    () => [
      {
        id: 'persistent' as const,
        label: 'Persistent Metrics',
        hint: 'KPIs, baselines, historical context'
      },
      {
        id: 'signals' as const,
        label: 'Current Signals',
        hint: 'Alerts, top news, knowledge graph'
      }
    ],
    []
  )

  const filterStateForChangeLog = useMemo<FilterStateSnapshot | undefined>(() => {
    if (!filtersSnapshot) return undefined
    return {
      sourceTypes: filtersSnapshot.source_types ?? [],
      topics: filtersSnapshot.topics ?? [],
      sentiments: filtersSnapshot.sentiments ?? [],
      minPriority: filtersSnapshot.min_priority ?? null
    }
  }, [filtersSnapshot])

  const changeLogQuery = useChangeLog({
    companyId: selectedCompany?.id ?? null,
    subjectKey: null,
    period: comparisonPeriod,
    filterState: filterStateForChangeLog,
    enabled: metricsTab === 'signals'
  })

  const changeLogEvents = useMemo(
    () => changeLogQuery.data?.pages.flatMap(page => page.events) ?? [],
    [changeLogQuery.data]
  )

  const changeSectionEvents =
    metricsTab === 'signals' && changeLogEvents.length ? changeLogEvents : changeEvents

  const changeSectionLoading =
    metricsTab === 'signals'
      ? changeLogQuery.isLoading || changeEventsLoading
      : changeEventsLoading

  const changeLogErrorMessage =
    changeLogQuery.error && changeLogQuery.error instanceof Error
      ? changeLogQuery.error.message
      : null

  const changeSectionError =
    metricsTab === 'signals'
      ? changeLogErrorMessage ?? changeEventsError
      : changeEventsError

  const knowledgeGraphQuery = useKnowledgeGraph({
    companyId: selectedCompany?.id ?? null,
    limit: 75,
    enabled: metricsTab === 'signals'
  })

  const knowledgeEdges = useMemo(
    () => knowledgeGraphQuery.data ?? analyticsEdges,
    [analyticsEdges, knowledgeGraphQuery.data]
  )

  if (!analysisData || !selectedCompany) {
    return null
  }

  return (
    <div className="rounded-lg border border-gray-200 shadow-sm overflow-hidden bg-white">
      <div className="flex flex-wrap bg-gray-50 border-b border-gray-200">
        {tabs.map(tab => (
          <button
            key={tab.id}
            type="button"
            onClick={() => onTabChange(tab.id)}
            className={`flex-1 min-w-[200px] px-4 py-3 text-left transition-colors border-b-2 ${
              metricsTab === tab.id
                ? 'bg-white border-blue-500 text-blue-600'
                : 'bg-gray-50 border-transparent text-gray-600 hover:text-blue-600'
            }`}
          >
            <span className="block text-sm font-semibold">{tab.label}</span>
            <span className="block text-xs text-gray-500 mt-1">{tab.hint}</span>
          </button>
        ))}
      </div>

      <div className="p-6 space-y-6">
        <ActiveFiltersSummary filters={filtersSnapshot} />

        {metricsTab === 'persistent' ? (
          <PersistentMetricsBoard
            selectedCompany={selectedCompany}
            analysisData={analysisData}
            comparisonData={comparisonData}
            comparisonPeriod={comparisonPeriod}
            comparisonLookback={comparisonLookback}
            comparisonLoading={comparisonLoading}
            comparisonError={comparisonError}
            subjectColorMap={subjectColorMap}
            impactSnapshot={impactSnapshot}
            impactSeries={impactSeries}
            focusedImpactPoint={focusedImpactPoint}
            onComparisonPeriodChange={onComparisonPeriodChange}
            onComparisonLookbackChange={onComparisonLookbackChange}
            onSnapshotHover={onSnapshotHover}
          />
        ) : (
          <>
            <CurrentSignalsBoard
              selectedCompany={selectedCompany}
              analysisData={analysisData}
              themesData={themesData}
              comparisonData={comparisonData}
              comparisonSubjects={comparisonSubjects}
              comparisonLoading={comparisonLoading}
              analyticsEdges={knowledgeEdges}
              impactSnapshot={impactSnapshot}
              reportPresets={reportPresets}
              pendingPresetId={pendingPresetId}
              onPendingPresetChange={onPendingPresetChange}
              onAddPresetToComparison={onAddPresetToComparison}
              abSelection={abSelection}
              onAbSelectionChange={onAbSelectionChange}
              subjectColorMap={subjectColorMap}
            />
            <ChangeEventsSection
              company={selectedCompany}
              events={changeSectionEvents}
              loading={changeSectionLoading}
              error={changeSectionError}
              onRefresh={() => {
                onRefreshChangeEvents()
                if (metricsTab === 'signals') {
                  changeLogQuery.refetch()
                }
              }}
              onRecompute={onRecomputeChangeEvent}
              recomputingEventId={recomputingEventId}
              hasMore={metricsTab === 'signals' ? Boolean(changeLogQuery.hasNextPage) : false}
              onLoadMore={
                metricsTab === 'signals' && changeLogQuery.hasNextPage
                  ? () => changeLogQuery.fetchNextPage()
                  : undefined
              }
              loadingMore={changeLogQuery.isFetchingNextPage}
            />
            
            {/* Monitoring Matrix Section */}
            {selectedCompany?.id && (
              <MonitoringMatrixSection companyId={selectedCompany.id} />
            )}
          </>
        )}
      </div>
    </div>
  )
}

// Monitoring Matrix Section Component
function MonitoringMatrixSection({ companyId }: { companyId: string }) {
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
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Monitoring Matrix</h3>
      <MonitoringSourcesCard matrix={monitoringMatrix as any} />
    </div>
  )
}
