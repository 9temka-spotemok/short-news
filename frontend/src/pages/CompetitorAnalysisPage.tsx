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

  // Prefetch аналитики только в режиме custom или после запуска анализа в режиме company
  useEffect(() => {
    if (selectedCompany && (analysisMode === 'custom' || analysisData)) {
      prefetchAnalytics({ companyId: selectedCompany.id })
    }
  }, [prefetchAnalytics, selectedCompany?.id, analysisMode, analysisData])

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

  // Загружаем аналитику только в режиме custom или после запуска анализа в режиме company
  const shouldLoadAnalytics = analysisMode === 'custom' || (analysisMode === 'company' && analysisData)
  
  const {
    data: analyticsInsights,
    isLoading: analyticsInsightsLoading,
    isFetching: analyticsInsightsFetching,
    isError: isAnalyticsInsightsError,
    error: analyticsInsightsError,
    refetch: refetchAnalyticsInsights
  } = useCompanyAnalyticsInsights(shouldLoadAnalytics ? selectedCompany?.id ?? null : null)

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

    // Prevent infinite requests by ensuring we only refetch once per task_id
    const currentTaskId = pendingTaskId
    let isCancelled = false

    const timer = setTimeout(async () => {
      // Check if this effect is still valid (task_id hasn't changed)
      if (isCancelled || currentTaskId !== pendingTaskId) {
        return
      }

      try {
        await Promise.all([
          refetchAnalyticsInsights(),
          refetchChangeEvents(),
          refetchReportPresets()
        ])
        
        // Only clear if this is still the current task
        if (!isCancelled && currentTaskId === pendingTaskId) {
          setPendingTaskId(null)
        }
      } catch (error) {
        console.error('Error refetching data after task completion:', error)
        // Clear pendingTaskId even on error to prevent infinite retries
        if (!isCancelled && currentTaskId === pendingTaskId) {
          setPendingTaskId(null)
        }
      }
    }, 5_000)

    return () => {
      isCancelled = true
      clearTimeout(timer)
    }
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
      const result = await ApiService.triggerAnalyticsRecompute(selectedCompany.id, 'daily', 60)
      
      // Validate task_id before setting pendingTaskId
      if (!result?.task_id) {
        console.error('Invalid response: task_id is missing', result)
        toast.error('Failed to queue analytics recompute: Invalid response from server')
        return
      }
      
      toast.success('Analytics recompute queued')
      await queryClient.invalidateQueries({
        queryKey: companyAnalyticsInsightsQueryKey(selectedCompany.id)
      })
      setPendingTaskId(result.task_id)
    } catch (error: any) {
      console.error('Failed to queue analytics recompute:', error)
      
      // Don't set pendingTaskId on error to prevent infinite requests
      const message = error?.response?.data?.detail || error?.message || 'Failed to queue analytics recompute'
      toast.error(message)
      
      // Clear pendingTaskId if it was set before error
      setPendingTaskId(null)
    }
  }

  const handleSyncKnowledgeGraph = async () => {
    if (!selectedCompany || !impactSnapshot) return
    try {
      const result = await ApiService.triggerKnowledgeGraphSync(
        selectedCompany.id,
        impactSnapshot.period_start,
        impactSnapshot.period
      )
      
      // Validate task_id before setting pendingTaskId
      if (!result?.task_id) {
        console.error('Invalid response: task_id is missing', result)
        toast.error('Failed to sync knowledge graph: Invalid response from server')
        return
      }
      
      toast.success('Knowledge graph sync queued')
      await refetchAnalyticsInsights()
      setPendingTaskId(result.task_id)
    } catch (error: any) {
      console.error('Failed to sync knowledge graph:', error)
      
      // Don't set pendingTaskId on error to prevent infinite requests
      const message = error?.response?.data?.detail || error?.message || 'Failed to sync knowledge graph'
      toast.error(message)
      
      // Clear pendingTaskId if it was set before error
      setPendingTaskId(null)
    }
  }

  // Режим кастомного анализа (существующий функционал)
  const renderCustomAnalysis = () => (
    <div className="max-w-6xl mx-auto">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-4 sm:mb-6">
        <div className="flex-1">
          <h2 className="text-lg sm:text-xl font-semibold text-gray-900">
            Custom Analysis
          </h2>
          <p className="text-sm sm:text-base text-gray-600 mt-1">
            Step-by-step competitor analysis with full control
          </p>
        </div>
        <button
          onClick={handleResetToMenu}
          className="text-sm sm:text-base text-gray-600 hover:text-gray-800 flex items-center w-full sm:w-auto justify-center sm:justify-start"
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
      <div className="max-w-7xl mx-auto py-4 sm:py-6 lg:py-8 px-4 sm:px-6 lg:px-8">
        <div className="mb-4 sm:mb-6">
          <h1 className="text-3xl sm:text-3xl font-bold text-gray-900 flex flex-col sm:flex-row items-start sm:items-center gap-2 sm:gap-3">
            <BarChart3 className="w-6 h-6 sm:w-8 sm:h-8" />
            <span>Competitor Analysis</span>
          </h1>
          <p className="text-sm sm:text-base text-gray-600 mt-2">
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
            error={error}
            loading={loading}
            onAnalyze={runCompanyAnalysis}
            analysisData={analysisData}
            suggestedCompetitors={suggestedCompetitors}
            onExport={handleExport}
            filtersSnapshot={analysisData?.filters ?? currentFilterSnapshot}
            impactSnapshot={impactSnapshot}
            impactSeries={impactSeries}
            analyticsEdges={analyticsEdges}
            analyticsLoading={analyticsLoading}
            analyticsError={analyticsError}
            onRecomputeAnalytics={handleRecomputeAnalytics}
            onSyncKnowledgeGraph={handleSyncKnowledgeGraph}
          />
        )}
        {analysisMode === 'custom' && renderCustomAnalysis()}
      </div>
    </div>
  )
}