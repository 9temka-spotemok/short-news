import { useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, BarChart3 } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import toast from 'react-hot-toast'
import ProgressSteps from '../components/ProgressSteps'
import {
  AnalysisModeSelection,
  AnalysisResultsStep,
  AnalyticsTabs,
  CompanyAnalysisFlow,
  companyAnalyticsInsightsQueryKey,
  CompanySelectionStep,
  CompetitorSuggestionStep,
  fetchCompanyAnalyticsInsights,
  ImpactPanel,
  PresetManager,
  useAnalysisFlow,
  useAnalyticsExportHandler,
  useChangeEventsQuery,
  useCompanyAnalyticsInsights,
  useComparisonManager,
  useExportAnalyticsMutation,
  useFiltersState,
  usePrefetchAnalytics,
  useRecomputeChangeEventMutation,
  useReportPresetActions,
  useReportPresetsQuery
} from '../features/competitor-analysis'
import { ApiService } from '../services/api'
import {
  CompanyAnalyticsSnapshot,
  ComparisonSubjectRequest,
  ReportPreset
} from '../types'

type AnalysisMode = 'company' | 'custom'
type Step = 'select' | 'suggest' | 'analyze'

export default function CompetitorAnalysisPage() {
  const [analysisMode, setAnalysisMode] = useState<AnalysisMode | null>(null)
  const [step, setStep] = useState<Step>('select')
  const [recomputingEventId, setRecomputingEventId] = useState<string | null>(null)
  const [metricsTab, setMetricsTab] = useState<'persistent' | 'signals'>('persistent')
  const [focusedImpactPoint, setFocusedImpactPoint] = useState<CompanyAnalyticsSnapshot | null>(null)
  const [pendingPresetId, setPendingPresetId] = useState('')
  const [pendingTaskId, setPendingTaskId] = useState<string | null>(null)

  const {
    sourceTypeFilters,
    topicFilters,
    sentimentFilters,
    minPriorityFilter,
    hasActiveFilters,
    toggleSourceType,
    toggleTopic: toggleTopicFilter,
    toggleSentiment: toggleSentimentFilter,
    updateMinPriority: updateMinPriorityFilter,
    clearFilters,
    setFilters,
    applyFiltersToPayload: applyFiltersToPayloadWithState
  } = useFiltersState()

  const queryClient = useQueryClient()

  const {
    comparisonData,
    comparisonLoading,
    comparisonError,
    comparisonSubjects,
    comparisonPeriod,
    comparisonLookback,
    analysisRange,
    abSelection,
    setAnalysisRange: setComparisonRange,
    resetComparison,
    fetchComparisonData,
    handleComparisonPeriodChange,
    handleComparisonLookbackChange,
    handleAbSelectionChange
  } = useComparisonManager({
    applyFiltersToPayload: applyFiltersToPayloadWithState
  })

  const {
    data: reportPresetsData,
    isLoading: reportPresetsInitialLoading,
    isFetching: reportPresetsFetching,
    isError: isReportPresetsError,
    error: reportPresetsError,
    refetch: refetchReportPresets
  } = useReportPresetsQuery()

  const reportPresets = reportPresetsData ?? []
  const presetsLoading = reportPresetsInitialLoading || reportPresetsFetching
  const presetsError =
    isReportPresetsError && reportPresetsError
      ? reportPresetsError instanceof Error
        ? reportPresetsError.message
        : 'Failed to load report presets'
      : null

  const filtersStateForAnalysis = useMemo(
    () => ({
      sourceTypes: sourceTypeFilters,
      topics: topicFilters,
      sentiments: sentimentFilters,
      minPriority: minPriorityFilter
    }),
    [minPriorityFilter, sentimentFilters, sourceTypeFilters, topicFilters]
  )

  const handleAnalysisComplete = useCallback(
    async (companyId: string | null) => {
      if (companyId) {
        setFocusedImpactPoint(null)
        await queryClient.fetchQuery({
          queryKey: companyAnalyticsInsightsQueryKey(companyId),
          queryFn: () => fetchCompanyAnalyticsInsights(companyId),
          staleTime: 60 * 1000
        })
      }
      await refetchReportPresets()
    },
    [queryClient, refetchReportPresets]
  )

  const {
    selectedCompany,
    setSelectedCompany,
    selectedCompetitors,
    setSelectedCompetitors,
    manuallyAddedCompetitors,
    setManuallyAddedCompetitors,
    suggestedCompetitors,
    setSuggestedCompetitors,
    analysisData,
    themesData,
    loading,
    error,
    toggleCompetitor,
    addManualCompetitor,
    loadCompetitorSuggestions,
    runAnalysis,
    runCompanyAnalysis,
    resetAnalysisState,
    clearAnalysisResults
  } = useAnalysisFlow({
    applyFiltersToPayload: applyFiltersToPayloadWithState,
    fetchComparisonData,
    setComparisonRange,
    resetComparison,
    comparisonPeriod,
    comparisonLookback,
    filtersState: filtersStateForAnalysis,
    onAnalysisStart: () => setStep('analyze'),
    onAnalysisComplete: handleAnalysisComplete
  })

  const prefetchAnalytics = usePrefetchAnalytics()

  useEffect(() => {
    if (selectedCompany) {
      prefetchAnalytics({ companyId: selectedCompany.id })
    }
  }, [prefetchAnalytics, selectedCompany?.id])

  const {
    newPresetName,
    setNewPresetName,
    savingPreset,
    presetApplyingId,
    createPreset,
    applyPreset
  } = useReportPresetActions({
    selectedCompany,
    selectedCompetitors,
    filtersState: filtersStateForAnalysis,
    reportPresets,
    refetchReportPresets,
    setAnalysisMode,
    setSelectedCompany,
    setSelectedCompetitors,
    setManuallyAddedCompetitors,
    setSuggestedCompetitors,
    setFilters,
    runAnalysis
  })

  const exportAnalyticsMutation = useExportAnalyticsMutation()

  const handleExport = useAnalyticsExportHandler({
    analysisData,
    selectedCompany,
    comparisonSubjects,
    comparisonPeriod,
    comparisonLookback,
    analysisRange,
    applyFiltersToPayload: applyFiltersToPayloadWithState,
    exportAnalytics: payload => exportAnalyticsMutation.mutateAsync(payload)
  })

  const changeEventsLimit = 10
  const {
    data: changeEventsResponse,
    isLoading: changeEventsInitialLoading,
    isFetching: changeEventsFetching,
    isError: isChangeEventsError,
    error: changeEventsQueryError,
    refetch: refetchChangeEvents
  } = useChangeEventsQuery({
    companyId: selectedCompany?.id ?? null,
    limit: changeEventsLimit,
    enabled: Boolean(selectedCompany?.id)
  })

  const changeEvents = changeEventsResponse?.events ?? []
  const changeEventsLoading = changeEventsInitialLoading || changeEventsFetching
  const changeEventsError =
    isChangeEventsError && changeEventsQueryError
      ? changeEventsQueryError instanceof Error
        ? changeEventsQueryError.message
        : 'Failed to load change history'
      : null

  const recomputeChangeEventMutation = useRecomputeChangeEventMutation()

  const {
    data: analyticsInsights,
    isLoading: analyticsInsightsLoading,
    isFetching: analyticsInsightsFetching,
    isError: isAnalyticsInsightsError,
    error: analyticsInsightsError,
    refetch: refetchAnalyticsInsights
  } = useCompanyAnalyticsInsights(selectedCompany?.id ?? null)

  const analyticsLoading = analyticsInsightsLoading || analyticsInsightsFetching
  const analyticsError =
    analyticsInsights?.message ??
    (isAnalyticsInsightsError
      ? (() => {
          if (analyticsInsightsError instanceof Error) {
            return analyticsInsightsError.message
          }
          const detail =
            (analyticsInsightsError as { response?: { data?: { detail?: string } } })?.response?.data?.detail
          return detail ?? 'Failed to load analytics insights'
        })()
      : null)
  const impactSnapshot = analyticsInsights?.snapshot ?? null
  const impactSeries = analyticsInsights?.series ?? null
  const analyticsEdges = analyticsInsights?.edges ?? []

  useEffect(() => {
    if (!pendingTaskId) {
      return
    }

    const timer = setTimeout(async () => {
      await Promise.all([
        refetchAnalyticsInsights(),
        refetchChangeEvents(),
        refetchReportPresets()
      ])
      setPendingTaskId(null)
    }, 5_000)

    return () => clearTimeout(timer)
  }, [pendingTaskId, refetchAnalyticsInsights, refetchChangeEvents, refetchReportPresets])

  const SUBJECT_COLORS = ['#2563eb', '#0ea5e9', '#10b981', '#f97316', '#8b5cf6', '#f43f5e', '#14b8a6', '#d946ef']

  const subjectColorMap = useMemo(() => {
    if (!comparisonData) {
      return new Map<string, string>()
    }
    const map = new Map<string, string>()
    comparisonData.subjects.forEach((subject, index) => {
      const color = subject.color || SUBJECT_COLORS[index % SUBJECT_COLORS.length]
      map.set(subject.subject_key, color)
    })
    return map
  }, [comparisonData])

  // Очищаем данные анализа при смене компании в режиме Company Analysis
  useEffect(() => {
    if (analysisMode === 'company' && selectedCompany) {
      clearAnalysisResults()
      setFocusedImpactPoint(null)
    }
  }, [analysisMode, clearAnalysisResults, selectedCompany])

  const handleResetToMenu = useCallback(() => {
    setAnalysisMode(null)
    resetAnalysisState()
    setStep('select')
    clearFilters()
  }, [clearFilters, resetAnalysisState])

  const handleSelectCompanyMode = useCallback(() => {
    setAnalysisMode('company')
    resetAnalysisState()
    clearFilters()
  }, [clearFilters, resetAnalysisState])

  const handleSelectCustomMode = useCallback(() => {
    setAnalysisMode('custom')
    setStep('select')
    resetAnalysisState()
    clearFilters()
  }, [clearFilters, resetAnalysisState])

  const currentFilterSnapshot = useMemo(() => ({
    topics: topicFilters,
    sentiments: sentimentFilters,
    source_types: sourceTypeFilters,
    min_priority: minPriorityFilter
  }), [topicFilters, sentimentFilters, sourceTypeFilters, minPriorityFilter])

  const handleRecomputeChange = useCallback(
    async (eventId: string) => {
      if (!selectedCompany?.id) return
      setRecomputingEventId(eventId)
      try {
        await recomputeChangeEventMutation.mutateAsync({
          companyId: selectedCompany.id,
          eventId,
          limit: changeEventsLimit
        })
        await refetchChangeEvents()
        toast.success('Recompute queued')
      } catch (err: any) {
        console.error('Error recomputing change event:', err)
        const message = err?.response?.data?.detail || err?.message || 'Unable to recompute diff'
        toast.error(message)
      } finally {
        setRecomputingEventId(null)
      }
    },
    [changeEventsLimit, recomputeChangeEventMutation, refetchChangeEvents, selectedCompany?.id]
  )

  useEffect(() => {
    setMetricsTab('persistent')
  }, [selectedCompany?.id])

  const handleAddPresetToComparison = async (presetId: string) => {
    if (!presetId) return
    const preset = reportPresets.find((item: ReportPreset) => item.id === presetId)
    if (!preset) {
      toast.error('Preset not found')
      return
    }
    if (
      comparisonSubjects.some(
        subject => subject.subject_type === 'preset' && subject.reference_id === presetId
      )
    ) {
      toast.error('Preset already added to comparison')
      setPendingPresetId('')
      return
    }

    const nextSubjects: ComparisonSubjectRequest[] = [
      ...comparisonSubjects,
      {
        subject_type: 'preset',
        reference_id: preset.id,
        label: preset.name
      }
    ]

    await fetchComparisonData(nextSubjects)
    setPendingPresetId('')
  }

  useEffect(() => {
    if (impactSnapshot) {
      setFocusedImpactPoint(impactSnapshot)
    }
  }, [impactSnapshot?.id])

  const handleRecomputeAnalytics = async () => {
    if (!selectedCompany) return
    try {
      const { task_id } = await ApiService.triggerAnalyticsRecompute(selectedCompany.id, 'daily', 60)
      toast.success('Analytics recompute queued')
      await queryClient.invalidateQueries({
        queryKey: companyAnalyticsInsightsQueryKey(selectedCompany.id)
      })
      setPendingTaskId(task_id)
    } catch (error: any) {
      console.error('Failed to queue analytics recompute:', error)
      const message = error?.response?.data?.detail || error?.message || 'Failed to queue analytics recompute'
      toast.error(message)
    }
  }

  const handleSyncKnowledgeGraph = async () => {
    if (!selectedCompany || !impactSnapshot) return
    try {
      const { task_id } = await ApiService.triggerKnowledgeGraphSync(
        selectedCompany.id,
        impactSnapshot.period_start,
        impactSnapshot.period
      )
      toast.success('Knowledge graph sync queued')
      await refetchAnalyticsInsights()
      setPendingTaskId(task_id)
    } catch (error: any) {
      console.error('Failed to sync knowledge graph:', error)
      const message = error?.response?.data?.detail || error?.message || 'Failed to sync knowledge graph'
      toast.error(message)
    }
  }

  // Режим кастомного анализа (существующий функционал)
  const renderCustomAnalysis = () => (
    <div className="max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">
            Custom Analysis
          </h2>
          <p className="text-gray-600 mt-1">
            Step-by-step competitor analysis with full control
          </p>
        </div>
        <button
          onClick={handleResetToMenu}
          className="text-gray-600 hover:text-gray-800 flex items-center"
        >
          <ArrowLeft className="w-4 h-4 mr-1" />
          Back to Menu
        </button>
      </div>

      {/* Progress Steps */}
      <ProgressSteps current={step} />
      
      {/* Content by step */}
      {step === 'select' && renderCompanySelection()}
      {step === 'suggest' && renderCompetitorSuggestion()}
      {step === 'analyze' && renderAnalysis()}
    </div>
  )

  const renderCompanySelection = () => (
    <CompanySelectionStep
      selectedCompany={selectedCompany}
      onSelectCompany={setSelectedCompany}
      onContinue={() => {
        if (selectedCompany) {
          loadCompetitorSuggestions()
          setStep('suggest')
        }
      }}
      onBackToMenu={handleResetToMenu}
    />
  )

  const renderCompetitorSuggestion = () => (
    <CompetitorSuggestionStep
      selectedCompany={selectedCompany}
      suggestions={[
        ...suggestedCompetitors,
        ...manuallyAddedCompetitors.map(company => ({
          company,
          similarity_score: 0,
          common_categories: [],
          reason: 'Manually added competitor'
        }))
      ]}
      manuallyAddedCompetitors={manuallyAddedCompetitors}
      selectedCompetitors={selectedCompetitors}
      onToggleCompetitor={toggleCompetitor}
      onAddManualCompetitor={addManualCompetitor}
      onBack={() => setStep('select')}
      onNext={() => {
        if (selectedCompetitors.length > 0) {
          runAnalysis()
        }
      }}
      filters={{
        sourceTypeFilters,
        topicFilters,
        sentimentFilters,
        minPriorityFilter,
        hasActiveFilters,
        onToggleSourceType: toggleSourceType,
        onToggleTopic: toggleTopicFilter,
        onToggleSentiment: toggleSentimentFilter,
        onMinPriorityChange: updateMinPriorityFilter,
        onClearFilters: clearFilters
      }}
      loading={loading}
      error={error}
      filtersSnapshot={currentFilterSnapshot}
    />
  )

  const renderAnalysis = () => (
    <AnalysisResultsStep
      selectedCompany={selectedCompany}
      loading={loading}
      analysisData={analysisData}
      filtersSnapshot={analysisData?.filters ?? currentFilterSnapshot}
      onBack={() => setStep('suggest')}
      onExport={handleExport}
    >
      <ImpactPanel
        impactSnapshot={impactSnapshot}
        impactSeries={impactSeries}
        analyticsEdges={analyticsEdges}
        analyticsLoading={analyticsLoading}
        analyticsError={analyticsError}
        onRecompute={handleRecomputeAnalytics}
        onSyncKnowledgeGraph={handleSyncKnowledgeGraph}
      />
      <PresetManager
        reportPresets={reportPresets}
        presetsLoading={presetsLoading}
        presetsError={presetsError}
        newPresetName={newPresetName}
        onPresetNameChange={setNewPresetName}
        onCreatePreset={createPreset}
        savingPreset={savingPreset}
        presetApplyingId={presetApplyingId}
        onApplyPreset={applyPreset}
        filtersSnapshot={analysisData?.filters ?? currentFilterSnapshot}
        filtersPanelProps={{
          sourceTypeFilters,
          topicFilters,
          sentimentFilters,
          minPriorityFilter,
          hasActiveFilters,
          onToggleSourceType: toggleSourceType,
          onToggleTopic: toggleTopicFilter,
          onToggleSentiment: toggleSentimentFilter,
          onMinPriorityChange: updateMinPriorityFilter,
          onClearFilters: clearFilters
        }}
      />
      <AnalyticsTabs
        metricsTab={metricsTab}
        onTabChange={setMetricsTab}
        selectedCompany={selectedCompany}
        analysisData={analysisData}
        themesData={themesData}
        comparisonData={comparisonData}
        comparisonPeriod={comparisonPeriod}
        comparisonLookback={comparisonLookback}
        comparisonLoading={comparisonLoading}
        comparisonError={comparisonError}
        subjectColorMap={subjectColorMap}
        impactSnapshot={impactSnapshot}
        impactSeries={impactSeries}
        focusedImpactPoint={focusedImpactPoint}
        onComparisonPeriodChange={handleComparisonPeriodChange}
        onComparisonLookbackChange={handleComparisonLookbackChange}
        onSnapshotHover={setFocusedImpactPoint}
        filtersSnapshot={analysisData?.filters ?? currentFilterSnapshot}
        comparisonSubjects={comparisonSubjects}
        analyticsEdges={analyticsEdges}
        reportPresets={reportPresets}
        pendingPresetId={pendingPresetId}
        onPendingPresetChange={setPendingPresetId}
        onAddPresetToComparison={handleAddPresetToComparison}
        abSelection={abSelection}
        onAbSelectionChange={handleAbSelectionChange}
        changeEvents={changeEvents}
        changeEventsLoading={changeEventsLoading}
        changeEventsError={changeEventsError}
        onRefreshChangeEvents={refetchChangeEvents}
        onRecomputeChangeEvent={handleRecomputeChange}
        recomputingEventId={recomputingEventId}
      />
    </AnalysisResultsStep>
  )
  
  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto py-8 px-4">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900 flex items-center">
            <BarChart3 className="w-8 h-8 mr-3" />
            Competitor Analysis
          </h1>
          <p className="text-gray-600 mt-2">
            Professional competitor analysis with AI-powered insights
          </p>
        </div>
        
        {/* Content by mode */}
        {!analysisMode && (
          <AnalysisModeSelection
            onSelectCompanyAnalysis={handleSelectCompanyMode}
            onSelectCustomAnalysis={handleSelectCustomMode}
          />
        )}
        {analysisMode === 'company' && (
          <CompanyAnalysisFlow
            selectedCompany={selectedCompany}
            onSelectCompany={company => setSelectedCompany(company)}
            onBack={handleResetToMenu}
            sourceTypeFilters={sourceTypeFilters}
            topicFilters={topicFilters}
            sentimentFilters={sentimentFilters}
            minPriorityFilter={minPriorityFilter}
            hasActiveFilters={hasActiveFilters}
            onToggleSourceType={toggleSourceType}
            onToggleTopic={toggleTopicFilter}
            onToggleSentiment={toggleSentimentFilter}
            onMinPriorityChange={updateMinPriorityFilter}
            onClearFilters={clearFilters}
            loading={loading}
            onAnalyze={runCompanyAnalysis}
            analysisData={analysisData}
            suggestedCompetitors={suggestedCompetitors}
            onExport={handleExport}
            filtersSnapshot={analysisData?.filters}
          />
        )}
        {analysisMode === 'custom' && renderCustomAnalysis()}
      </div>
    </div>
  )
}