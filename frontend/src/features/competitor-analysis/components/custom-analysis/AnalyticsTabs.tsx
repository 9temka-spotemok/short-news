import { useMemo } from 'react'

import type {
  AnalyticsPeriod,
  ComparisonSubjectRequest,
  ComparisonResponse,
  Company,
  CompanyAnalyticsSnapshot,
  ReportPreset,
  SnapshotSeries
} from '@/types'
import type { FilterStateSnapshot } from '../../types'

import { ActiveFiltersSummary, type ActiveFilters } from '../ActiveFiltersSummary'
import { PersistentMetricsBoard } from '../PersistentMetricsBoard'
import { CurrentSignalsBoard } from '../CurrentSignalsBoard'
import { ChangeEventsSection } from '../ChangeEventsSection'
import { useChangeLog } from '../../hooks/useChangeLog'
import { useKnowledgeGraph } from '../../hooks/useKnowledgeGraph'

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
          </>
        )}
      </div>
    </div>
  )
}
