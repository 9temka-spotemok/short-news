import axios from 'axios'
import { Activity, ArrowLeft, ArrowRight, BarChart3, Building2, Clock, Filter, Gauge, History, LineChart, Newspaper, PieChart, RefreshCw, Smile, Sparkles, TrendingUp, Users } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import toast from 'react-hot-toast'
import BrandPreview from '../components/BrandPreview'
import { BusinessIntelligence } from '../components/BusinessIntelligence'
import CompanySelector from '../components/CompanySelector'
import CompetitorSuggestions from '../components/CompetitorSuggestions'
import { ExportMenu } from '../components/ExportMenu'
import ImpactTrendChart from '../components/ImpactTrendChart'
import { InnovationMetrics } from '../components/InnovationMetrics'
import { MarketPosition } from '../components/MarketPosition'
import MultiImpactTrendChart, { MultiImpactSeriesDescriptor } from '../components/MultiImpactTrendChart'
import ProgressSteps from '../components/ProgressSteps'
import { TeamInsights } from '../components/TeamInsights'
import ThemeAnalysis from '../components/ThemeAnalysis'
import { ApiService } from '../services/api'
import {
  AnalyticsExportRequestPayload,
  AnalyticsPeriod,
  ChangeProcessingStatus,
  Company,
  CompanyAnalyticsSnapshot,
  ComparisonMetricSummary,
  ComparisonRequestPayload,
  ComparisonResponse,
  ComparisonSubjectRequest,
  ComparisonSubjectSummary,
  CompetitorChangeEvent,
  KnowledgeGraphEdge,
  NewsItem,
  ReportPreset,
  SnapshotSeries
} from '../types'

type AnalysisMode = 'company' | 'custom'
type Step = 'select' | 'suggest' | 'analyze'

const SOURCE_TYPE_OPTIONS = [
  { value: 'blog', label: 'Blog' },
  { value: 'news_site', label: 'News Site' },
  { value: 'press_release', label: 'Press Release' },
  { value: 'twitter', label: 'Twitter/X' },
  { value: 'github', label: 'GitHub' },
  { value: 'reddit', label: 'Reddit' }
]

const SENTIMENT_OPTIONS = [
  { value: 'positive', label: 'Positive' },
  { value: 'neutral', label: 'Neutral' },
  { value: 'negative', label: 'Negative' },
  { value: 'mixed', label: 'Mixed' }
]

const TOPIC_OPTIONS = [
  { value: 'product', label: 'Product & Launches' },
  { value: 'strategy', label: 'Strategy' },
  { value: 'finance', label: 'Finance' },
  { value: 'technology', label: 'Technology' },
  { value: 'security', label: 'Security' },
  { value: 'research', label: 'Research' },
  { value: 'community', label: 'Community' },
  { value: 'talent', label: 'Talent' },
  { value: 'regulation', label: 'Regulation' },
  { value: 'market', label: 'Market' },
  { value: 'other', label: 'Other' }
]

const formatLabel = (value: string) =>
  value
    .replace(/_/g, ' ')
    .replace(/\b\w/g, letter => letter.toUpperCase())

const formatPriceDisplay = (amount: number | null | undefined, currency?: string | null) => {
  if (amount === null || amount === undefined) {
    return currency ?? 'n/a'
  }
  const formatter = new Intl.NumberFormat(undefined, {
    minimumFractionDigits: amount % 1 === 0 ? 0 : 2,
    maximumFractionDigits: 2
  })
  const formatted = formatter.format(amount)
  return currency ? `${currency} ${formatted}` : formatted
}

export default function CompetitorAnalysisPage() {
  const [analysisMode, setAnalysisMode] = useState<AnalysisMode | null>(null)
  const [step, setStep] = useState<Step>('select')
  const [selectedCompany, setSelectedCompany] = useState<Company | null>(null)
  const [suggestedCompetitors, setSuggestedCompetitors] = useState<any[]>([])
  const [selectedCompetitors, setSelectedCompetitors] = useState<string[]>([])
  const [manuallyAddedCompetitors, setManuallyAddedCompetitors] = useState<Company[]>([])
  const [analysisData, setAnalysisData] = useState<any>(null)
  const [themesData, setThemesData] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [sourceTypeFilters, setSourceTypeFilters] = useState<string[]>([])
  const [topicFilters, setTopicFilters] = useState<string[]>([])
  const [sentimentFilters, setSentimentFilters] = useState<string[]>([])
  const [minPriorityFilter, setMinPriorityFilter] = useState<number | null>(null)
  const [changeEvents, setChangeEvents] = useState<CompetitorChangeEvent[]>([])
  const [changeEventsLoading, setChangeEventsLoading] = useState(false)
  const [changeEventsError, setChangeEventsError] = useState<string | null>(null)
  const [recomputingEventId, setRecomputingEventId] = useState<string | null>(null)
  const [impactSnapshot, setImpactSnapshot] = useState<CompanyAnalyticsSnapshot | null>(null)
  const [impactSeries, setImpactSeries] = useState<SnapshotSeries | null>(null)
  const [analyticsEdges, setAnalyticsEdges] = useState<KnowledgeGraphEdge[]>([])
  const [analyticsLoading, setAnalyticsLoading] = useState(false)
  const [analyticsError, setAnalyticsError] = useState<string | null>(null)
  const [reportPresets, setReportPresets] = useState<ReportPreset[]>([])
  const [presetsLoading, setPresetsLoading] = useState(false)
  const [presetsError, setPresetsError] = useState<string | null>(null)
  const [newPresetName, setNewPresetName] = useState('')
  const [savingPreset, setSavingPreset] = useState(false)
  const [presetApplyingId, setPresetApplyingId] = useState<string | null>(null)
  const [metricsTab, setMetricsTab] = useState<'persistent' | 'signals'>('persistent')
  const [focusedImpactPoint, setFocusedImpactPoint] = useState<CompanyAnalyticsSnapshot | null>(null)
  const [comparisonData, setComparisonData] = useState<ComparisonResponse | null>(null)
  const [comparisonLoading, setComparisonLoading] = useState(false)
  const [comparisonError, setComparisonError] = useState<string | null>(null)
  const [comparisonSubjects, setComparisonSubjects] = useState<ComparisonSubjectRequest[]>([])
  const [comparisonPeriod, setComparisonPeriod] = useState<AnalyticsPeriod>('daily')
  const [comparisonLookback, setComparisonLookback] = useState(30)
  const [abSelection, setAbSelection] = useState<{ left: string | null; right: string | null }>({ left: null, right: null })
  const [pendingPresetId, setPendingPresetId] = useState('')
  const [analysisRange, setAnalysisRange] = useState<{ from: string; to: string } | null>(null)

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
      setAnalysisData(null)
      setThemesData(null)
      setImpactSnapshot(null)
      setImpactSeries(null)
      setAnalyticsEdges([])
      setAnalyticsError(null)
      setFocusedImpactPoint(null)
    }
  }, [selectedCompany, analysisMode])

  const toggleSourceType = (value: string) => {
    setSourceTypeFilters(prev =>
      prev.includes(value) ? prev.filter(item => item !== value) : [...prev, value]
    )
  }

  const toggleTopicFilter = (value: string) => {
    setTopicFilters(prev =>
      prev.includes(value) ? prev.filter(item => item !== value) : [...prev, value]
    )
  }

  const toggleSentimentFilter = (value: string) => {
    setSentimentFilters(prev =>
      prev.includes(value) ? prev.filter(item => item !== value) : [...prev, value]
    )
  }

  const clearFilters = () => {
    setSourceTypeFilters([])
    setTopicFilters([])
    setSentimentFilters([])
    setMinPriorityFilter(null)
  }

  type FilteredPayload<T> = T & {
    source_types?: string[]
    topics?: string[]
    sentiments?: string[]
    min_priority?: number
  }

  type FilterOptions = {
    sourceTypes?: string[]
    topics?: string[]
    sentiments?: string[]
    minPriority?: number | null
  }
  
  const applyFiltersToPayload = <T extends Record<string, unknown>>(
    payload: T,
    options: FilterOptions = {}
  ): FilteredPayload<T> => {
    const {
      sourceTypes = sourceTypeFilters,
      topics = topicFilters,
      sentiments = sentimentFilters,
      minPriority = minPriorityFilter
    } = options

    const nextPayload: FilteredPayload<T> = { ...payload }
    if (sourceTypes.length) {
      nextPayload.source_types = sourceTypes
    }
    if (topics.length) {
      nextPayload.topics = topics
    }
    if (sentiments.length) {
      nextPayload.sentiments = sentiments
    }
    if (minPriority !== null && minPriority !== undefined) {
      nextPayload.min_priority = Number(minPriority.toFixed(2))
    }
    return nextPayload
  }

  const buildComparisonPayload = (
    subjects: ComparisonSubjectRequest[],
    period: AnalyticsPeriod,
    lookback: number,
    range: { from: string; to: string } | null
  ): ComparisonRequestPayload => {
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

    const filtersPayload = applyFiltersToPayload({}, {})
    if (filtersPayload.source_types || filtersPayload.topics || filtersPayload.sentiments || filtersPayload.min_priority !== undefined) {
      payload.filters = {
        topics: filtersPayload.topics ?? [],
        sentiments: filtersPayload.sentiments ?? [],
        source_types: filtersPayload.source_types ?? [],
        min_priority: filtersPayload.min_priority
      }
    }

    return payload
  }

  const renderFilterControls = () => (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-primary-100 rounded-lg">
            <Filter className="w-5 h-5 text-primary-600" />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-gray-900">Advanced Filters</h4>
            <p className="text-xs text-gray-500">Fine-tune analytics results by source, topic, sentiment and priority</p>
          </div>
        </div>
        <button
          onClick={clearFilters}
          disabled={!sourceTypeFilters.length && !topicFilters.length && !sentimentFilters.length && minPriorityFilter === null}
          className="text-sm text-gray-500 hover:text-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Reset
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div>
          <h5 className="text-xs font-medium text-gray-600 uppercase mb-3">Source Types</h5>
          <div className="space-y-2">
            {SOURCE_TYPE_OPTIONS.map(option => (
              <label key={option.value} className="flex items-center space-x-2 text-sm text-gray-700">
                <input
                  type="checkbox"
                  className="h-4 w-4 text-primary-600 border-gray-300 rounded"
                  checked={sourceTypeFilters.includes(option.value)}
                  onChange={() => toggleSourceType(option.value)}
                />
                <span>{option.label}</span>
              </label>
            ))}
          </div>
        </div>

        <div>
          <h5 className="text-xs font-medium text-gray-600 uppercase mb-3">Topics</h5>
          <div className="grid grid-cols-2 gap-2">
            {TOPIC_OPTIONS.map(option => (
              <button
                key={option.value}
                type="button"
                onClick={() => toggleTopicFilter(option.value)}
                className={`px-3 py-1 text-xs rounded-full border transition-colors ${topicFilters.includes(option.value)
                  ? 'bg-blue-100 border-blue-300 text-blue-700'
                  : 'bg-gray-100 border-gray-200 text-gray-600 hover:border-gray-300'
                }`}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>

        <div className="space-y-4">
          <div>
            <h5 className="text-xs font-medium text-gray-600 uppercase mb-3">Sentiment</h5>
            <div className="space-y-2">
              {SENTIMENT_OPTIONS.map(option => (
                <label key={option.value} className="flex items-center space-x-2 text-sm text-gray-700">
                  <input
                    type="checkbox"
                    className="h-4 w-4 text-primary-600 border-gray-300 rounded"
                    checked={sentimentFilters.includes(option.value)}
                    onChange={() => toggleSentimentFilter(option.value)}
                  />
                  <span>{option.label}</span>
                </label>
              ))}
            </div>
          </div>

          <div>
            <h5 className="text-xs font-medium text-gray-600 uppercase mb-2">Minimum Priority</h5>
            <div className="flex items-center space-x-3">
              <input
                type="range"
                min={0}
                max={1}
                step={0.05}
                value={minPriorityFilter ?? 0}
                onChange={event => {
                  const value = Number(event.target.value)
                  if (value <= 0) {
                    setMinPriorityFilter(null)
                  } else {
                    setMinPriorityFilter(Number(value.toFixed(2)))
                  }
                }}
                className="w-full"
              />
              <span className="text-sm font-medium text-gray-700 w-12 text-right">
                {minPriorityFilter !== null ? minPriorityFilter.toFixed(2) : 'Off'}
              </span>
            </div>
            <p className="text-xs text-gray-500 mt-1">Filter out low-priority news items below the selected threshold.</p>
          </div>
        </div>
      </div>
    </div>
  )

  const sentimentColors: Record<string, string> = {
    positive: 'bg-green-500',
    neutral: 'bg-gray-400',
    negative: 'bg-red-500',
    mixed: 'bg-purple-500'
  }

  const statusBadgeStyles: Record<ChangeProcessingStatus, string> = {
    success: 'bg-green-100 text-green-700',
    skipped: 'bg-gray-100 text-gray-600',
    error: 'bg-red-100 text-red-600'
  }

  const renderTopicDistributionCard = (companyId: string) => {
    const topics = analysisData?.metrics?.topic_distribution?.[companyId]
    if (!topics || Object.keys(topics).length === 0) return null
    const entries = Object.entries(topics).sort(([, a], [, b]) => Number(b) - Number(a))
    const total = entries.reduce((sum, [, value]) => sum + Number(value), 0)

    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <div className="flex items-center space-x-3 mb-4">
          <div className="p-2 bg-indigo-100 rounded-lg">
            <PieChart className="w-5 h-5 text-indigo-600" />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-gray-900">Topic Distribution</h4>
            <p className="text-xs text-gray-500">Top themes driving conversation</p>
          </div>
        </div>
        <div className="space-y-3">
          {entries.slice(0, 5).map(([topic, count]) => {
            const percentage = total ? Math.round((Number(count) / total) * 100) : 0
            return (
              <div key={topic}>
                <div className="flex justify-between text-xs text-gray-600 mb-1">
                  <span>{formatLabel(topic)}</span>
                  <span className="text-gray-900 font-medium">{Number(count)} ({percentage}%)</span>
                </div>
                <div className="h-2 w-full bg-gray-100 rounded-full">
                  <div
                    className="h-2 bg-indigo-500 rounded-full"
                    style={{ width: `${percentage}%` }}
                  />
                </div>
              </div>
            )
          })}
        </div>
      </div>
    )
  }

  const renderSentimentDistributionCard = (companyId: string) => {
    const sentiments = analysisData?.metrics?.sentiment_distribution?.[companyId]
    if (!sentiments || Object.keys(sentiments).length === 0) return null
    const entries = Object.entries(sentiments)
    const total = entries.reduce((sum, [, value]) => sum + Number(value), 0)

    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <div className="flex items-center space-x-3 mb-4">
          <div className="p-2 bg-rose-100 rounded-lg">
            <Smile className="w-5 h-5 text-rose-600" />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-gray-900">Sentiment Overview</h4>
            <p className="text-xs text-gray-500">Tone of recent coverage</p>
          </div>
        </div>
        <div className="space-y-3">
          {entries.map(([sentiment, count]) => {
            const percentage = total ? Math.round((Number(count) / total) * 100) : 0
            const barColor = sentimentColors[sentiment] || 'bg-gray-400'
            return (
              <div key={sentiment}>
                <div className="flex justify-between text-xs text-gray-600 mb-1">
                  <span>{formatLabel(sentiment)}</span>
                  <span className="text-gray-900 font-medium">{Number(count)} ({percentage}%)</span>
                </div>
                <div className="h-2 w-full bg-gray-100 rounded-full">
                  <div
                    className={`h-2 rounded-full ${barColor}`}
                    style={{ width: `${percentage}%` }}
                  />
                </div>
              </div>
            )
          })}
        </div>
      </div>
    )
  }

  const renderPriorityCard = (companyId: string) => {
    const avgPriority = analysisData?.metrics?.avg_priority?.[companyId]
    if (avgPriority === undefined || avgPriority === null) return null
    const percent = Math.round(Number(avgPriority) * 100)

    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <div className="flex items-center space-x-3 mb-4">
          <div className="p-2 bg-emerald-100 rounded-lg">
            <Gauge className="w-5 h-5 text-emerald-600" />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-gray-900">Average Priority</h4>
            <p className="text-xs text-gray-500">Weighted priority score for selected news</p>
          </div>
        </div>
        <div className="space-y-3">
          <div className="flex items-end justify-between">
            <div>
              <p className="text-xs text-gray-500 uppercase">Priority Score</p>
              <p className="text-2xl font-semibold text-gray-900">{Number(avgPriority).toFixed(2)}</p>
            </div>
            <span className="text-sm font-medium text-emerald-600">{percent}%</span>
          </div>
          <div className="h-2 w-full bg-gray-100 rounded-full overflow-hidden">
            <div className="h-2 bg-emerald-500" style={{ width: `${percent}%` }} />
          </div>
          <p className="text-xs text-gray-500">Higher score indicates more impactful or time-sensitive updates.</p>
        </div>
      </div>
    )
  }

  const renderActiveFiltersSummary = (filters?: {
    topics?: string[]
    sentiments?: string[]
    source_types?: string[]
    min_priority?: number
  }) => {
    if (!filters) return null
    const { topics = [], sentiments = [], source_types = [], min_priority } = filters
    const hasFilters = topics.length || sentiments.length || source_types.length || (min_priority !== undefined && min_priority !== null)
    if (!hasFilters) return null

    return (
      <div className="bg-blue-50 border border-blue-100 rounded-lg p-4 flex items-start space-x-3">
        <Filter className="w-4 h-4 mt-1 text-blue-600" />
        <div className="space-y-2 text-sm text-blue-700">
          <p className="text-xs font-semibold uppercase text-blue-600">Active Filters</p>
          <div className="flex flex-wrap gap-2">
            {source_types.map(value => (
              <span key={`source-${value}`} className="px-2 py-1 text-xs bg-white border border-blue-200 text-blue-700 rounded-full">
                Source: {formatLabel(value)}
              </span>
            ))}
            {topics.map(value => (
              <span key={`topic-${value}`} className="px-2 py-1 text-xs bg-white border border-blue-200 text-blue-700 rounded-full">
                Topic: {formatLabel(value)}
              </span>
            ))}
            {sentiments.map(value => (
              <span key={`sentiment-${value}`} className="px-2 py-1 text-xs bg-white border border-blue-200 text-blue-700 rounded-full">
                Sentiment: {formatLabel(value)}
              </span>
            ))}
            {(min_priority !== undefined && min_priority !== null) && (
              <span className="px-2 py-1 text-xs bg-white border border-blue-200 text-blue-700 rounded-full">
                Min priority: {Number(min_priority).toFixed(2)}
              </span>
            )}
          </div>
        </div>
      </div>
    )
  }

  const loadChangeEvents = useCallback(async (companyId: string) => {
    setChangeEventsLoading(true)
    setChangeEventsError(null)
    try {
      const response = await ApiService.getCompetitorChangeEvents(companyId, { limit: 10 })
      setChangeEvents(response.events)
    } catch (err: any) {
      console.error('Error loading change history:', err)
      setChangeEventsError(err.response?.data?.detail || 'Failed to load change history')
    } finally {
      setChangeEventsLoading(false)
    }
  }, [])

  const handleRecomputeChange = useCallback(async (eventId: string) => {
    setRecomputingEventId(eventId)
    try {
      const updatedEvent = await ApiService.recomputeCompetitorChangeEvent(eventId)
      setChangeEvents(prev =>
        prev.map(event => (event.id === updatedEvent.id ? updatedEvent : event))
      )
      setChangeEventsError(null)
    } catch (err: any) {
      console.error('Error recomputing change event:', err)
      setChangeEventsError(err.response?.data?.detail || 'Unable to recompute diff')
    } finally {
      setRecomputingEventId(null)
    }
  }, [])

  useEffect(() => {
    if (!selectedCompany) {
      setChangeEvents([])
      setChangeEventsError(null)
      return
    }
    loadChangeEvents(selectedCompany.id)
  }, [selectedCompany?.id, loadChangeEvents])

  useEffect(() => {
    setMetricsTab('persistent')
  }, [selectedCompany?.id])

  const renderChangeFieldSummary = (change: Record<string, any>) => {
    if (change.field === 'price') {
      return `${formatPriceDisplay(change.previous ?? null, change.previous_currency)} → ${formatPriceDisplay(change.current ?? null, change.current_currency)}`
    }
    if (change.field === 'billing_cycle') {
      const previous = change.previous ? formatLabel(change.previous) : 'n/a'
      const current = change.current ? formatLabel(change.current) : 'n/a'
      return `${previous} → ${current}`
    }
    if (change.field === 'features') {
      const parts: string[] = []
      if (change.added?.length) {
        const preview = change.added.slice(0, 3).join(', ')
        parts.push(`Added: ${preview}${change.added.length > 3 ? '…' : ''}`)
      }
      if (change.removed?.length) {
        const preview = change.removed.slice(0, 3).join(', ')
        parts.push(`Removed: ${preview}${change.removed.length > 3 ? '…' : ''}`)
      }
      return parts.length ? parts.join(' · ') : 'Feature list updated'
    }
    if (change.change === 'added') {
      return 'Plan added'
    }
    if (change.change === 'removed') {
      return 'Plan removed'
    }
    return JSON.stringify(change)
  }

  const renderChangeEventsSection = () => {
    if (!selectedCompany) return null

    return (
      <div className="bg-white rounded-lg shadow-md border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <div className="flex items-center space-x-2">
              <History className="w-5 h-5 text-blue-600" />
              <h3 className="text-lg font-semibold text-gray-900">Latest Changes</h3>
            </div>
            <p className="text-xs text-gray-500 mt-1">
              Pricing and feature updates detected for {selectedCompany.name}
            </p>
          </div>
          <button
            type="button"
            onClick={() => loadChangeEvents(selectedCompany.id)}
            disabled={changeEventsLoading}
            className="flex items-center text-sm text-blue-600 hover:text-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <RefreshCw className={`w-4 h-4 mr-1 ${changeEventsLoading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>

        {changeEventsError && (
          <div className="mb-3 p-3 rounded-md border border-red-200 bg-red-50 text-xs text-red-700">
            {changeEventsError}
          </div>
        )}

        {changeEventsLoading ? (
          <div className="py-6 text-center">
            <div className="mx-auto h-6 w-6 border-2 border-blue-200 border-t-blue-600 rounded-full animate-spin" />
            <p className="text-sm text-gray-500 mt-3">Loading change history...</p>
          </div>
        ) : changeEvents.length === 0 ? (
          <p className="text-sm text-gray-500">
            No changes detected yet. We will surface pricing and feature updates here as soon as they are captured.
          </p>
        ) : (
          <div className="space-y-4">
            {changeEvents.map(event => (
              <div key={event.id} className="border border-gray-200 rounded-lg p-4">
                <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-3">
                  <div>
                    <div className="flex items-center space-x-2">
                      <span className="text-sm font-semibold text-gray-900">
                        {formatLabel(event.source_type)}
                      </span>
                      <span
                        className={`text-xs font-medium px-2 py-0.5 rounded-full ${statusBadgeStyles[event.processing_status]}`}
                      >
                        {formatLabel(event.processing_status)}
                      </span>
                    </div>
                    <p className="text-sm text-gray-700 mt-2">
                      {event.change_summary}
                    </p>
                  </div>
                  <div className="flex flex-col items-end space-y-2">
                    <div className="flex items-center text-xs text-gray-500">
                      <Clock className="w-3 h-3 mr-1" />
                      {new Date(event.detected_at).toLocaleString()}
                    </div>
                    <button
                      type="button"
                      onClick={() => handleRecomputeChange(event.id)}
                      disabled={recomputingEventId === event.id}
                      className="text-xs text-blue-600 hover:text-blue-700 flex items-center disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <History className={`w-3 h-3 mr-1 ${recomputingEventId === event.id ? 'animate-spin' : ''}`} />
                      Recompute diff
                    </button>
                  </div>
                </div>

                {event.changed_fields.length > 0 && (
                  <div className="mt-3 space-y-2 text-xs text-gray-600">
                    {event.changed_fields.map((change, index) => (
                      <div key={`${event.id}-${index}`} className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1">
                        <span className="font-medium text-gray-700">
                          {change.plan ? `${change.plan} · ${formatLabel(change.field || 'update')}` : formatLabel(change.field || 'update')}
                        </span>
                        <span>{renderChangeFieldSummary(change)}</span>
                      </div>
                    ))}
                  </div>
                )}

                {(event.current_snapshot?.raw_snapshot_url || event.previous_snapshot?.raw_snapshot_url) && (
                  <div className="mt-3 flex flex-wrap gap-3 text-xs text-blue-600">
                    {event.current_snapshot?.raw_snapshot_url && (
                      <a
                        href={event.current_snapshot.raw_snapshot_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="hover:underline"
                      >
                        View current snapshot
                      </a>
                    )}
                    {event.previous_snapshot?.raw_snapshot_url && (
                      <a
                        href={event.previous_snapshot.raw_snapshot_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="hover:underline"
                      >
                        View previous snapshot
                      </a>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    )
  }

  const loadAnalyticsInsights = async (companyId: string) => {
    setAnalyticsLoading(true)
    setAnalyticsError(null)
    setFocusedImpactPoint(null)
    try {
      const [snapshotResult, seriesResult, edgesResult] = await Promise.allSettled([
        ApiService.getLatestAnalyticsSnapshot(companyId),
        ApiService.getAnalyticsSnapshots(companyId, 'daily', 60),
        ApiService.getAnalyticsGraph(companyId, undefined, 25)
      ])

      let resolvedSnapshot: CompanyAnalyticsSnapshot | null = null
      let resolvedSeries: SnapshotSeries | null = null
      let resolvedEdges: KnowledgeGraphEdge[] = []
      let errorMessage: string | null = null

      if (snapshotResult.status === 'fulfilled') {
        resolvedSnapshot = snapshotResult.value
      } else {
        const reason = snapshotResult.reason
        if (axios.isAxiosError(reason) && reason.response?.status === 404) {
          resolvedSnapshot = null
          errorMessage = 'Аналитика ещё не построена. Запустите пересчёт, чтобы получить метрики.'
        } else {
          console.error('Failed to load latest analytics snapshot:', reason)
          errorMessage = reason?.response?.data?.detail || reason?.message || 'Failed to load analytics insights'
        }
      }

      if (seriesResult.status === 'fulfilled') {
        resolvedSeries = seriesResult.value
      } else {
        const reason = seriesResult.reason
        if (!(axios.isAxiosError(reason) && reason.response?.status === 404)) {
          console.error('Failed to load analytics snapshot series:', reason)
          const fallbackMessage = reason?.response?.data?.detail || reason?.message || 'Failed to load analytics insights'
          errorMessage = errorMessage ?? fallbackMessage
        }
      }

      if (edgesResult.status === 'fulfilled') {
        resolvedEdges = edgesResult.value
      } else {
        const reason = edgesResult.reason
        if (!(axios.isAxiosError(reason) && reason.response?.status === 404)) {
          console.error('Failed to load analytics edges:', reason)
          const fallbackMessage = reason?.response?.data?.detail || reason?.message || 'Failed to load analytics insights'
          errorMessage = errorMessage ?? fallbackMessage
        }
      }

      setImpactSnapshot(resolvedSnapshot)
      setImpactSeries(resolvedSeries)
      setAnalyticsEdges(resolvedEdges)
      setFocusedImpactPoint(resolvedSnapshot)
      setAnalyticsError(errorMessage)
    } catch (error: any) {
      console.error('Failed to load analytics insights:', error)
      const message = error?.response?.data?.detail || error?.message || 'Failed to load analytics insights'
      setAnalyticsError(message)
      setImpactSnapshot(null)
      setImpactSeries(null)
      setAnalyticsEdges([])
    } finally {
      setAnalyticsLoading(false)
    }
  }

  const loadReportPresets = async () => {
    setPresetsLoading(true)
    setPresetsError(null)
    try {
      const presets = await ApiService.listReportPresets()
      setReportPresets(presets)
    } catch (error: any) {
      console.error('Failed to load report presets:', error)
      const message = error?.response?.data?.detail || error?.message || 'Failed to load report presets'
      setPresetsError(message)
    } finally {
      setPresetsLoading(false)
    }
  }

  const fetchComparisonData = useCallback(
    async (
      subjects: ComparisonSubjectRequest[],
      overrides: {
        period?: AnalyticsPeriod
        lookback?: number
        range?: { from: string; to: string } | null
      } = {}
    ) => {
      if (!subjects.length) {
        return
      }

      const nextPeriod = overrides.period ?? comparisonPeriod
      const nextLookback = overrides.lookback ?? comparisonLookback
      const range = overrides.range ?? analysisRange

      setComparisonLoading(true)
      setComparisonError(null)

      try {
        const payload = buildComparisonPayload(subjects, nextPeriod, nextLookback, range)
        const response = await ApiService.getAnalyticsComparison(payload)

        setComparisonData(response)
        setComparisonSubjects(subjects)
        setComparisonPeriod(nextPeriod)
        setComparisonLookback(nextLookback)
        if (range) {
          setAnalysisRange(range)
        } else if (payload.date_from && payload.date_to) {
          setAnalysisRange({ from: payload.date_from, to: payload.date_to })
        }

        const subjectKeys = response.subjects.map(
          (subject: ComparisonSubjectSummary) => subject.subject_key
        )
        setAbSelection(prev => ({
          left: prev.left && subjectKeys.includes(prev.left) ? prev.left : subjectKeys[0] || null,
          right:
            prev.right && subjectKeys.includes(prev.right)
              ? prev.right
              : subjectKeys[1] || subjectKeys[0] || null
        }))
      } catch (err: any) {
        console.error('Failed to load comparison data:', err)
        setComparisonError(err?.response?.data?.detail || 'Failed to load comparison data')
      } finally {
        setComparisonLoading(false)
      }
    },
    [
      analysisRange,
      comparisonLookback,
      comparisonPeriod,
      minPriorityFilter,
      sentimentFilters,
      sourceTypeFilters,
      topicFilters
    ]
  )

  const handleComparisonPeriodChange = (period: AnalyticsPeriod) => {
    if (period === comparisonPeriod) return
    setComparisonPeriod(period)
    if (comparisonSubjects.length) {
      fetchComparisonData(comparisonSubjects, { period })
    }
  }

  const handleComparisonLookbackChange = (lookback: number) => {
    if (lookback === comparisonLookback) return
    setComparisonLookback(lookback)
    if (comparisonSubjects.length) {
      fetchComparisonData(comparisonSubjects, { lookback })
    }
  }

  const handleAbSelectionChange = (position: 'left' | 'right', subjectKey: string) => {
    setAbSelection(prev => ({
      ...prev,
      [position]: subjectKey
    }))
  }

  const handleAddPresetToComparison = async (presetId: string) => {
    if (!presetId) return
    const preset = reportPresets.find(item => item.id === presetId)
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
    loadReportPresets()
  }, [])

  useEffect(() => {
    if (impactSnapshot) {
      setFocusedImpactPoint(impactSnapshot)
    }
  }, [impactSnapshot?.id])

  const handleRecomputeAnalytics = async () => {
    if (!selectedCompany) return
    try {
      await ApiService.triggerAnalyticsRecompute(selectedCompany.id, 'daily', 60)
      toast.success('Analytics recompute queued')
    } catch (error: any) {
      console.error('Failed to queue analytics recompute:', error)
      const message = error?.response?.data?.detail || error?.message || 'Failed to queue analytics recompute'
      toast.error(message)
    }
  }

  const handleSyncKnowledgeGraph = async () => {
    if (!selectedCompany || !impactSnapshot) return
    try {
      await ApiService.triggerKnowledgeGraphSync(
        selectedCompany.id,
        impactSnapshot.period_start,
        impactSnapshot.period
      )
      toast.success('Knowledge graph sync queued')
    } catch (error: any) {
      console.error('Failed to sync knowledge graph:', error)
      const message = error?.response?.data?.detail || error?.message || 'Failed to sync knowledge graph'
      toast.error(message)
    }
  }

  const handleCreatePreset = async () => {
    if (!selectedCompany) {
      toast.error('Select a primary company before saving a preset')
      return
    }

    const name = newPresetName.trim()
    if (!name) {
      toast.error('Preset name cannot be empty')
      return
    }

    const companyIds = [selectedCompany.id, ...selectedCompetitors]

    setSavingPreset(true)
    try {
      await ApiService.createReportPreset({
        name,
        companies: companyIds,
        filters: {
          source_types: sourceTypeFilters,
          topics: topicFilters,
          sentiments: sentimentFilters,
          min_priority: minPriorityFilter
        },
        visualization_config: {
          impact_panel: true,
          comparison_chart: true
        }
      })
      toast.success('Report preset saved')
      setNewPresetName('')
      await loadReportPresets()
    } catch (error: any) {
      console.error('Failed to save preset:', error)
      const message = error?.response?.data?.detail || error?.message || 'Failed to save preset'
      toast.error(message)
    } finally {
      setSavingPreset(false)
    }
  }

  const handleApplyPreset = async (preset: ReportPreset) => {
    if (!preset.companies || preset.companies.length === 0) {
      toast.error('Preset does not contain any companies')
      return
    }

    setPresetApplyingId(preset.id)

    try {
      const companies = await ApiService.getCompaniesByIds(preset.companies)
      if (!companies.length) {
        throw new Error('Preset companies could not be loaded')
      }

      const primaryId = preset.companies[0]
      const primaryCompany = companies.find(company => company.id === primaryId) ?? companies[0]

      if (!primaryCompany) {
        throw new Error('Primary company is missing in preset')
      }

      const competitorIds = preset.companies.filter(id => id !== primaryCompany.id)
      if (!competitorIds.length) {
        toast.error('Preset must include at least one competitor')
        setPresetApplyingId(null)
        return
      }

      const presetSourceTypes = Array.isArray(preset.filters?.source_types) ? preset.filters.source_types as string[] : []
      const presetTopics = Array.isArray(preset.filters?.topics) ? preset.filters.topics as string[] : []
      const presetSentiments = Array.isArray(preset.filters?.sentiments) ? preset.filters.sentiments as string[] : []
      const presetMinPriority = typeof preset.filters?.min_priority === 'number' ? preset.filters.min_priority : null

      const competitorCompanies = companies.filter(company => competitorIds.includes(company.id))

      setAnalysisMode('custom')
      setSelectedCompany(primaryCompany)
      setSelectedCompetitors(competitorIds)
      setManuallyAddedCompetitors(competitorCompanies)
      setSuggestedCompetitors(
        competitorCompanies.map(company => ({
          company,
          similarity_score: 0,
          common_categories: [],
          reason: 'Preset'
        }))
      )
      setSourceTypeFilters(presetSourceTypes)
      setTopicFilters(presetTopics)
      setSentimentFilters(presetSentiments)
      setMinPriorityFilter(presetMinPriority)

      await runAnalysis({
        primaryCompany,
        competitorIds,
        filters: {
          source_types: presetSourceTypes,
          topics: presetTopics,
          sentiments: presetSentiments,
          min_priority: presetMinPriority
        }
      })

      toast.success('Preset applied')
    } catch (error: any) {
      console.error('Failed to apply preset:', error)
      const message = error?.response?.data?.detail || error?.message || 'Failed to apply preset'
      toast.error(message)
    } finally {
      setPresetApplyingId(null)
    }
  }

  const renderPersistentMetricsSection = () => {
    if (!analysisData || !selectedCompany) {
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

    const dailyActivityRaw: Record<string, number> = analysisData.metrics?.daily_activity?.[companyId] ?? {}
    const dailyActivity = Object.entries(dailyActivityRaw)
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
          comparisonData.subjects.map(subject => [subject.subject_key, subject])
        )
      : new Map<string, ComparisonSubjectSummary>()
    const seriesForChart: MultiImpactSeriesDescriptor[] = comparisonData
      ? comparisonData.series
          .filter(entry => entry.snapshots.length > 0)
          .map(entry => ({
            subjectKey: entry.subject_key,
            label:
              (subjectSummariesByKey.get(entry.subject_key) as { label?: string } | undefined)?.label ||
              entry.subject_key,
            color: subjectColorMap.get(entry.subject_key) || SUBJECT_COLORS[0],
            points: entry.snapshots
          }))
      : []

    return (
      <>
        {renderActiveFiltersSummary(analysisData.filters)}

        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6 space-y-6">
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div>
              <h3 className="text-lg font-semibold text-gray-900">Comparison dashboard</h3>
              <p className="text-sm text-gray-500">
                Aggregated metrics for selected companies and presets
              </p>
            </div>
            <div className="flex items-center gap-3">
              <label className="flex items-center gap-2 text-sm text-gray-600">
                Period
                <select
                  value={comparisonPeriod}
                  onChange={event => handleComparisonPeriodChange(event.target.value as AnalyticsPeriod)}
                  className="rounded-md border border-gray-300 px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                >
                  <option value="daily">Daily</option>
                  <option value="weekly">Weekly</option>
                  <option value="monthly">Monthly</option>
                </select>
              </label>
              <label className="flex items-center gap-2 text-sm text-gray-600">
                Lookback
                <select
                  value={comparisonLookback}
                  onChange={event => handleComparisonLookbackChange(Number(event.target.value))}
                  className="rounded-md border border-gray-300 px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                >
                  <option value={30}>30 days</option>
                  <option value={60}>60 days</option>
                  <option value={90}>90 days</option>
                </select>
              </label>
            </div>
          </div>

          {comparisonError && (
            <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              {comparisonError}
            </div>
          )}

          {comparisonLoading ? (
            <div className="py-10 text-center text-sm text-gray-500">
              <div className="mx-auto mb-3 h-6 w-6 animate-spin rounded-full border-2 border-blue-200 border-t-blue-600" />
              Loading comparison data…
            </div>
          ) : comparisonData ? (
            <div className="space-y-6">
              {seriesForChart.length > 0 ? (
                <MultiImpactTrendChart series={seriesForChart} />
              ) : (
                <p className="text-sm text-gray-500">
                  Not enough snapshot data yet to render combined trend. Run analysis to build history.
                </p>
              )}

              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200 text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-2 text-left font-semibold text-gray-700">Subject</th>
                      <th className="px-4 py-2 text-left font-semibold text-gray-700">Impact</th>
                      <th className="px-4 py-2 text-left font-semibold text-gray-700">Trend Δ</th>
                      <th className="px-4 py-2 text-left font-semibold text-gray-700">News</th>
                      <th className="px-4 py-2 text-left font-semibold text-gray-700">Activity</th>
                      <th className="px-4 py-2 text-left font-semibold text-gray-700">Priority</th>
                      <th className="px-4 py-2 text-left font-semibold text-gray-700">Innovation</th>
                      <th className="px-4 py-2 text-left font-semibold text-gray-700">Positive</th>
                      <th className="px-4 py-2 text-left font-semibold text-gray-700">Negative</th>
                      <th className="px-4 py-2 text-left font-semibold text-gray-700">Knowledge</th>
                      <th className="px-4 py-2 text-left font-semibold text-gray-700">Changes</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {comparisonData.metrics.map(metric => {
                      const subject = subjectSummariesByKey.get(metric.subject_key)
                      const snapshot = metric.snapshot
                      const knowledgeCount = comparisonData.knowledge_graph?.[metric.subject_key]?.length ?? 0
                      const changeCount = comparisonData.change_log?.[metric.subject_key]?.length ?? 0
                      const trendDelta = metric.trend_delta ?? 0
                      return (
                        <tr key={metric.subject_key} className="hover:bg-gray-50">
                          <td className="whitespace-nowrap px-4 py-2 font-medium text-gray-900">
                            <div className="flex items-center gap-2">
                              <span
                                className="inline-block h-2 w-2 rounded-sm"
                                style={{ backgroundColor: subjectColorMap.get(metric.subject_key) || SUBJECT_COLORS[0] }}
                              />
                              {subject?.label || metric.subject_key}
                            </div>
                          </td>
                          <td className="px-4 py-2">{metric.impact_score.toFixed(2)}</td>
                          <td className="px-4 py-2">
                            {trendDelta >= 0 ? '+' : ''}
                            {trendDelta.toFixed(2)}%
                          </td>
                          <td className="px-4 py-2">{metric.news_volume}</td>
                          <td className="px-4 py-2">{metric.activity_score.toFixed(2)}</td>
                          <td className="px-4 py-2">{metric.avg_priority.toFixed(2)}</td>
                          <td className="px-4 py-2">{metric.innovation_velocity.toFixed(2)}</td>
                          <td className="px-4 py-2">{snapshot?.news_positive ?? 0}</td>
                          <td className="px-4 py-2">{snapshot?.news_negative ?? 0}</td>
                          <td className="px-4 py-2">{knowledgeCount}</td>
                          <td className="px-4 py-2">{changeCount}</td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
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
              {impactDelta !== null ? `${impactDelta >= 0 ? '+' : ''}${impactDelta.toFixed(2)} vs previous` : 'Awaiting history for comparison'}
            </p>
          </div>

          <div className="p-4 rounded-lg border border-emerald-100 bg-emerald-50">
            <div className="flex items-center justify-between">
              <p className="text-xs uppercase font-semibold text-emerald-700">Activity Score</p>
              <Activity className="w-4 h-4 text-emerald-600" />
            </div>
            <p className="text-2xl font-bold text-emerald-900 mt-2">
              {activityScore.toFixed(2)}
            </p>
            <p className="text-xs text-emerald-700 mt-1">
              Benchmarked vs {Math.max(competitorTotal, 0)} competitor{competitorTotal === 1 ? '' : 's'}
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

        <div className="bg-white rounded-lg border border-gray-200 p-5">
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
          <div className="mt-4">
            {trendSnapshots.length > 0 ? (
              <ImpactTrendChart
                snapshots={trendSnapshots}
                onPointHover={snapshot => {
                  if (snapshot) {
                    setFocusedImpactPoint(snapshot)
                    return
                  }
                  if (impactSnapshot) {
                    setFocusedImpactPoint(impactSnapshot)
                  } else {
                    setFocusedImpactPoint(null)
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
          <div className={`p-4 rounded-lg border ${trendPercent >= 0 ? 'border-green-100 bg-green-50' : 'border-rose-100 bg-rose-50'}`}>
            <div className="flex items-center space-x-2">
              <TrendingUp className={`w-4 h-4 ${trendPercent >= 0 ? 'text-green-600' : 'text-rose-600'}`} />
              <span className="text-sm font-semibold text-gray-800">
                {trendPercent >= 0 ? 'Positive trend' : 'Negative trend'}: {trendPercent >= 0 ? '+' : ''}{trendPercent.toFixed(1)}%
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
                      style={{ width: `${maxDailyValue ? Math.max(8, (value / maxDailyValue) * 100) : 8}%` }}
                    />
                  </div>
                  <span className="w-10 text-right text-gray-500">{value}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        <BrandPreview
          company={selectedCompany}
          stats={{
            total_news: newsVolume,
            categories_breakdown: Object.entries(analysisData.metrics.category_distribution?.[companyId] || {}).map(([category, count]) => ({
              category,
              count: count as number
            })),
            activity_score: activityScore,
            avg_priority: avgPriority ?? 0.5
          }}
        />

        <BusinessIntelligence
          company={selectedCompany}
          metrics={analysisData.metrics.category_distribution?.[companyId] || {}}
          activityScore={activityScore}
          competitorCount={suggestedCompetitors.length}
        />

        <InnovationMetrics
          company={selectedCompany}
          metrics={analysisData.metrics.category_distribution?.[companyId] || {}}
          totalNews={newsVolume}
        />

        <TeamInsights
          company={selectedCompany}
          metrics={analysisData.metrics.category_distribution?.[companyId] || {}}
          totalNews={newsVolume}
          activityScore={activityScore}
        />

        <MarketPosition
          company={selectedCompany}
          metrics={{
            news_volume: newsVolume,
            activity_score: activityScore,
            category_distribution: analysisData.metrics.category_distribution?.[companyId] || {}
          }}
          competitors={suggestedCompetitors}
          totalNews={Object.values(analysisData.metrics.news_volume || {}).reduce((sum: number, value: unknown) => sum + Number(value), 0)}
        />

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {renderTopicDistributionCard(companyId)}
          {renderSentimentDistributionCard(companyId)}
          {renderPriorityCard(companyId)}
        </div>

        <div className="bg-white rounded-lg shadow-md border border-gray-200 p-6">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-semibold text-gray-900">
              News Volume Comparison
            </h3>
          </div>
          <div className="space-y-3">
            {analysisData.companies.map((company: Company, index: number) => {
              const volume = analysisData.metrics.news_volume?.[company.id] || 0
              const maxVolume = Math.max(...Object.values(analysisData.metrics.news_volume || {}).map(value => Number(value)), 0)
              const percentage = maxVolume > 0 ? (volume / maxVolume) * 100 : 0
              const colors = ['bg-blue-500', 'bg-green-500', 'bg-purple-500', 'bg-orange-500', 'bg-pink-500']

              return (
                <div key={company.id}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-gray-700">
                      {company.name}
                    </span>
                    <span className="text-sm text-gray-600">{volume} news</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-3">
                    <div
                      className={`h-3 rounded-full ${colors[index % colors.length]}`}
                      style={{ width: `${percentage}%` }}
                    />
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {themesData && (
          <div className="bg-white rounded-lg shadow-md p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              Theme Analysis
            </h3>
            <ThemeAnalysis
              themesData={themesData}
              companies={analysisData.companies}
            />
          </div>
        )}
      </>
    )
  }

  const renderCurrentSignalsSection = () => {
    if (!analysisData || !selectedCompany) {
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
    const trendPercent = typeof impactSnapshot?.trend_delta === 'number' ? impactSnapshot.trend_delta * 100 : null
    const comparisonSubjectsAvailable = comparisonData?.subjects ?? []
    const subjectSummariesByKey = comparisonData
      ? new Map<string, ComparisonSubjectSummary>(
          comparisonData.subjects.map(subject => [subject.subject_key, subject])
        )
      : new Map<string, ComparisonSubjectSummary>()
    const metricsMap = comparisonData
      ? new Map<string, ComparisonMetricSummary>(
          comparisonData.metrics.map(metric => [metric.subject_key, metric])
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
        return comparisonSubjectsAvailable[1]?.subject_key ?? comparisonSubjectsAvailable[0]?.subject_key ?? null
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
              style={{ backgroundColor: subjectColorMap.get(subjectKey) || SUBJECT_COLORS[0] }}
              aria-hidden="true"
            />
          </div>
          <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
            <div>
              <p className="text-xs text-gray-500">Impact Score</p>
              <p className="text-lg font-semibold text-gray-900">
                {metric ? metric.impact_score.toFixed(2) : '—'}
              </p>
              <p className={`text-xs ${trendDelta !== null && trendDelta >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
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
              <p className="text-xs text-gray-500">Activity: {metric?.activity_score?.toFixed(2) ?? '—'}</p>
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
                        {news.category && <span className="rounded bg-blue-50 px-2 py-0.5 text-blue-600">{formatLabel(news.category)}</span>}
                        {news.sentiment && <span className="rounded bg-emerald-50 px-2 py-0.5 text-emerald-600">{formatLabel(news.sentiment)}</span>}
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
                  changeEvents.map(event => (
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
                  onChange={event => handleAbSelectionChange('left', event.target.value)}
                  className="rounded-md border border-gray-300 px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                >
                  {comparisonSubjectsAvailable.map(subject => (
                    <option key={subject.subject_key} value={subject.subject_key}>
                      {subject.label}
                    </option>
                  ))}
                </select>
                <select
                  value={resolvedRight ?? ''}
                  onChange={event => handleAbSelectionChange('right', event.target.value)}
                  className="rounded-md border border-gray-300 px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                >
                  {comparisonSubjectsAvailable.map(subject => (
                    <option key={subject.subject_key} value={subject.subject_key}>
                      {subject.label}
                    </option>
                  ))}
                </select>
                <div className="flex items-center gap-2">
                  <select
                    value={pendingPresetId}
                    onChange={event => setPendingPresetId(event.target.value)}
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
                    onClick={() => handleAddPresetToComparison(pendingPresetId)}
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
          <div className={`p-4 rounded-lg border ${trendPercent !== null && trendPercent < 0 ? 'border-rose-100 bg-rose-50' : 'border-emerald-100 bg-emerald-50'}`}>
            <div className="flex items-center justify-between">
              <p className="text-xs uppercase font-semibold text-gray-700">Trend Direction</p>
              <TrendingUp className={`w-4 h-4 ${trendPercent !== null && trendPercent < 0 ? 'text-rose-600' : 'text-emerald-600'}`} />
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
            <p className="text-2xl font-bold text-orange-900 mt-2">{changeEvents.length}</p>
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

        {renderChangeEventsSection()}
      </div>
    )
  }

  const renderAnalyticsTabs = () => {
    if (!analysisData || !selectedCompany) {
      return null
    }

    const tabs: Array<{ id: 'persistent' | 'signals'; label: string; hint: string }> = [
      {
        id: 'persistent',
        label: 'Persistent Metrics',
        hint: 'KPIs, baselines, historical context'
      },
      {
        id: 'signals',
        label: 'Current Signals',
        hint: 'Alerts, top news, knowledge graph'
      }
    ]

    return (
      <div className="rounded-lg border border-gray-200 shadow-sm overflow-hidden bg-white">
        <div className="flex flex-wrap bg-gray-50 border-b border-gray-200">
          {tabs.map(tab => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setMetricsTab(tab.id)}
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
          {metricsTab === 'persistent' ? renderPersistentMetricsSection() : renderCurrentSignalsSection()}
        </div>
      </div>
    )
  }

  const renderImpactPanel = () => {
    if (!impactSnapshot && !analyticsLoading && !analyticsError) {
      return null
    }

    const recentSnapshots = impactSeries?.snapshots?.slice(-8) ?? []
    const maxImpact = recentSnapshots.length ? Math.max(...recentSnapshots.map(snapshot => snapshot.impact_score)) : 0
    const minImpact = recentSnapshots.length ? Math.min(...recentSnapshots.map(snapshot => snapshot.impact_score)) : 0
    const previousScore = recentSnapshots.length > 1 ? recentSnapshots[recentSnapshots.length - 2].impact_score : null
    const trendDeltaPercent = typeof impactSnapshot?.trend_delta === 'number' ? impactSnapshot.trend_delta * 100 : null
    const absoluteChange = previousScore !== null && impactSnapshot
      ? impactSnapshot.impact_score - previousScore
      : null

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
                Snapshot range {new Date(impactSnapshot.period_start).toLocaleDateString()} — {new Date(impactSnapshot.period_end).toLocaleDateString()}
              </p>
            )}
          </div>
          <div className="flex items-center space-x-2">
            <button
              type="button"
              onClick={handleRecomputeAnalytics}
              className="text-xs px-3 py-1.5 rounded-md border border-blue-200 text-blue-600 hover:bg-blue-50 transition-colors"
            >
              Recompute
            </button>
            <button
              type="button"
              onClick={handleSyncKnowledgeGraph}
              disabled={!impactSnapshot}
              className="text-xs px-3 py-1.5 rounded-md border border-indigo-200 text-indigo-600 hover:bg-indigo-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Sync graph
            </button>
          </div>
        </div>

        {analyticsError && (
          <div className="mb-4 p-3 rounded-md border border-red-200 bg-red-50 text-xs text-red-700">
            {analyticsError}
          </div>
        )}

        {analyticsLoading && !impactSnapshot ? (
          <div className="py-6 text-center text-sm text-gray-500">
            <div className="mx-auto h-6 w-6 border-2 border-blue-200 border-t-blue-600 rounded-full animate-spin mb-3" />
            Loading analytics insights...
          </div>
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
                <p className={`text-3xl font-bold mt-2 ${trendDeltaPercent !== null && trendDeltaPercent >= 0 ? 'text-emerald-700' : 'text-red-600'}`}>
                  {trendDeltaPercent !== null ? `${trendDeltaPercent >= 0 ? '+' : ''}${trendDeltaPercent.toFixed(1)}%` : 'n/a'}
                </p>
                <p className="text-xs text-emerald-700 mt-1">
                  {absoluteChange !== null ? `${absoluteChange >= 0 ? '+' : ''}${absoluteChange.toFixed(2)} points vs previous snapshot` : 'Awaiting history for comparison'}
                </p>
              </div>
              <div className="p-4 rounded-lg bg-purple-50 border border-purple-100">
                <p className="text-xs uppercase text-purple-600 font-semibold">Signals</p>
                <p className="text-sm text-purple-700 mt-2">
                  {impactSnapshot.news_total} news · {impactSnapshot.pricing_changes} pricing · {impactSnapshot.feature_updates} features
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
                      const normalized = maxImpact !== minImpact ? (snapshot.impact_score - minImpact) / (maxImpact - minImpact) : 0.5
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
                    <div key={edge.id} className="flex flex-col sm:flex-row sm:items-center sm:justify-between border-b border-gray-100 pb-2 last:border-b-0 gap-1">
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

  const renderPresetManager = () => (
    <div className="bg-white rounded-lg shadow-md border border-gray-200 p-6">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-4">
        <div>
          <div className="flex items-center space-x-2">
            <Building2 className="w-5 h-5 text-teal-600" />
            <h3 className="text-lg font-semibold text-gray-900">Saved report presets</h3>
          </div>
          <p className="text-xs text-gray-500 mt-1">
            Save frequently used combinations of companies и фильтров for quick access later.
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <input
            type="text"
            value={newPresetName}
            onChange={(event) => setNewPresetName(event.target.value)}
            placeholder="Preset name"
            className="w-48 md:w-56 rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent"
          />
          <button
            type="button"
            onClick={handleCreatePreset}
            disabled={savingPreset}
            className="text-xs px-3 py-2 rounded-md bg-teal-600 text-white hover:bg-teal-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {savingPreset ? 'Saving…' : 'Save preset'}
          </button>
        </div>
      </div>

      {presetsError && (
        <div className="mb-3 p-3 rounded-md border border-red-200 bg-red-50 text-xs text-red-700">
          {presetsError}
        </div>
      )}

      {presetsLoading ? (
        <div className="py-6 text-center text-sm text-gray-500">
          <div className="mx-auto h-6 w-6 border-2 border-teal-200 border-t-teal-600 rounded-full animate-spin mb-3" />
          Loading presets…
        </div>
      ) : reportPresets.length === 0 ? (
        <p className="text-sm text-gray-500">No presets yet. Save the current configuration to reuse it later.</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm text-gray-700">
          {reportPresets.map((preset) => (
            <div key={preset.id} className="border border-gray-200 rounded-lg p-3">
              <div className="flex items-center justify-between">
                <p className="font-semibold text-gray-900">{preset.name}</p>
                {preset.is_favorite && <span className="text-xs text-amber-600 font-medium">Favorite</span>}
              </div>
              <p className="mt-1 text-xs text-gray-500">
                Companies: {preset.companies?.length ?? 0} · Updated {new Date(preset.updated_at).toLocaleDateString()}
              </p>
              <p className="mt-1 text-xs text-gray-400">
                Filters saved · companies: {preset.companies?.length ?? 0}
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => handleApplyPreset(preset)}
                  disabled={presetApplyingId === preset.id}
                  className="text-xs px-3 py-1.5 rounded-md border border-teal-200 text-teal-600 hover:bg-teal-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {presetApplyingId === preset.id ? 'Applying…' : 'Apply preset'}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )

  const handleExport = async (format: 'json' | 'pdf' | 'csv') => {
    if (!analysisData || !selectedCompany) return

    try {
      const fallbackSubjects: ComparisonSubjectRequest[] = (analysisData.companies || []).map((company: Company) => ({
        subject_type: 'company',
        reference_id: company.id,
        label: company.name
      }))
      const subjects = comparisonSubjects.length ? comparisonSubjects : fallbackSubjects

      if (!subjects.length) {
        toast.error('No comparison subjects available for export')
        return
      }

      const range = analysisRange ?? {
        from: new Date(Date.now() - comparisonLookback * 24 * 60 * 60 * 1000).toISOString(),
        to: new Date().toISOString()
      }

      const payload: AnalyticsExportRequestPayload = {
        ...buildComparisonPayload(subjects, comparisonPeriod, comparisonLookback, range),
        export_format: format,
        include: {
          include_notifications: true,
          include_presets: true
        }
      }

      const exportResponse = await ApiService.buildAnalyticsExport(payload)
      await ApiService.exportAnalysis(exportResponse, format)
      toast.success(`Exported analysis as ${format.toUpperCase()}`)
    } catch (err: any) {
      console.error('Export failed:', err)
      toast.error(err.response?.data?.detail || 'Export failed. Please try again.')
    }
  }

  // Главное меню выбора режима анализа
  const renderModeSelection = () => (
    <div className="max-w-4xl mx-auto">
      <div className="text-center mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">
          Choose Analysis Type
        </h2>
        <p className="text-gray-600">
          Select the type of competitor analysis you want to perform
        </p>
      </div>
      
      <div className="grid md:grid-cols-2 gap-6">
        {/* Анализ компании */}
        <div 
          onClick={() => {
            setAnalysisMode('company')
            // Сбрасываем состояние при смене режима
            setSelectedCompany(null)
            setAnalysisData(null)
            setThemesData(null)
            setError(null)
            clearFilters()
          }}
          className="bg-white rounded-lg shadow-md p-6 cursor-pointer hover:shadow-lg transition-shadow border-2 border-transparent hover:border-blue-200"
        >
          <div className="flex items-center mb-4">
            <Building2 className="w-8 h-8 text-blue-600 mr-3" />
            <h3 className="text-xl font-semibold text-gray-900">
              Company Analysis
            </h3>
          </div>
          <p className="text-gray-600 mb-4">
            Quick analysis of a specific company with AI-suggested competitors. 
            Perfect for getting immediate insights about a company and its competitive landscape.
          </p>
          <ul className="text-sm text-gray-500 space-y-1">
            <li>• Select target company</li>
            <li>• AI-powered competitor suggestions</li>
            <li>• Instant analysis results</li>
            <li>• Export capabilities</li>
          </ul>
        </div>

        {/* Кастомный анализ */}
        <div 
          onClick={() => {
            setAnalysisMode('custom')
            // Сбрасываем состояние при смене режима
            setSelectedCompany(null)
            setAnalysisData(null)
            setThemesData(null)
            setError(null)
            setStep('select')
            setSelectedCompetitors([])
            setSuggestedCompetitors([])
            setManuallyAddedCompetitors([])
            clearFilters()
          }}
          className="bg-white rounded-lg shadow-md p-6 cursor-pointer hover:shadow-lg transition-shadow border-2 border-transparent hover:border-green-200"
        >
          <div className="flex items-center mb-4">
            <Users className="w-8 h-8 text-green-600 mr-3" />
            <h3 className="text-xl font-semibold text-gray-900">
              Custom Analysis
            </h3>
          </div>
          <p className="text-gray-600 mb-4">
            Advanced step-by-step analysis with full control over competitor selection. 
            Ideal for detailed research and comprehensive competitive intelligence.
          </p>
          <ul className="text-sm text-gray-500 space-y-1">
            <li>• Step-by-step process</li>
            <li>• Manual competitor selection</li>
            <li>• Detailed theme analysis</li>
            <li>• Advanced export options</li>
          </ul>
        </div>
      </div>
    </div>
  )

  // Режим анализа компании
  const renderCompanyAnalysis = () => (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">
            Company Analysis
          </h2>
          <p className="text-gray-600 mt-1">
            Quick analysis with AI-suggested competitors
          </p>
        </div>
        <button
          onClick={() => {
            setAnalysisMode(null)
            // Сбрасываем все состояние при возврате в меню
            setSelectedCompany(null)
            setAnalysisData(null)
            setThemesData(null)
            setError(null)
            setStep('select')
            setSelectedCompetitors([])
            setSuggestedCompetitors([])
            setManuallyAddedCompetitors([])
            clearFilters()
          }}
          className="text-gray-600 hover:text-gray-800 flex items-center"
        >
          <ArrowLeft className="w-4 h-4 mr-1" />
          Back to Menu
        </button>
      </div>

      {/* Выбор компании */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Select Company to Analyze
        </h3>
        <CompanySelector
          onSelect={setSelectedCompany}
          selectedCompany={selectedCompany}
        />

        <div className="mt-6">
          {renderFilterControls()}
        </div>
        
        {selectedCompany && (
          <div className="mt-6">
            <button
              onClick={runCompanyAnalysis}
              disabled={loading}
              className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
            >
              {loading ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  Analyzing...
                </>
              ) : (
                <>
                  <BarChart3 className="w-4 h-4 mr-2" />
                  Analyze Company
                </>
              )}
            </button>
          </div>
        )}
      </div>

      {/* Результаты анализа компании */}
      {analysisData && selectedCompany && (
        <div className="space-y-6">
          {/* Analysis Header with Export */}
          <div className="bg-white rounded-lg shadow-md p-6">
            <div className="flex justify-between items-center mb-4">
              <div>
                <h2 className="text-2xl font-bold text-gray-900">{selectedCompany.name}</h2>
                <p className="text-gray-600">Competitor Analysis Report</p>
              </div>
              <ExportMenu onExport={handleExport} />
            </div>
          </div>

          {renderActiveFiltersSummary(analysisData.filters)}

          {/* Brand Preview */}
          <BrandPreview
            company={selectedCompany}
            stats={{
              total_news: analysisData.metrics.news_volume[selectedCompany.id] || 0,
              categories_breakdown: Object.entries(analysisData.metrics.category_distribution[selectedCompany.id] || {}).map(([category, count]) => ({
                category,
                count: count as number
              })),
              activity_score: analysisData.metrics.activity_score[selectedCompany.id] || 0,
              avg_priority: analysisData.metrics.avg_priority?.[selectedCompany.id] ?? 0.5
            }}
          />

          {/* Business Intelligence */}
          <BusinessIntelligence
            company={selectedCompany}
            metrics={analysisData.metrics.category_distribution[selectedCompany.id] || {}}
            activityScore={analysisData.metrics.activity_score[selectedCompany.id] || 0}
            competitorCount={suggestedCompetitors.length}
          />

          {/* Innovation & Technology */}
          <InnovationMetrics
            company={selectedCompany}
            metrics={analysisData.metrics.category_distribution[selectedCompany.id] || {}}
            totalNews={analysisData.metrics.news_volume[selectedCompany.id] || 0}
          />

          {/* Team & Culture */}
          <TeamInsights
            company={selectedCompany}
            metrics={analysisData.metrics.category_distribution[selectedCompany.id] || {}}
            totalNews={analysisData.metrics.news_volume[selectedCompany.id] || 0}
            activityScore={analysisData.metrics.activity_score[selectedCompany.id] || 0}
          />

          {/* Market Position */}
          <MarketPosition
            company={selectedCompany}
            metrics={{
              news_volume: analysisData.metrics.news_volume[selectedCompany.id] || 0,
              activity_score: analysisData.metrics.activity_score[selectedCompany.id] || 0,
              category_distribution: analysisData.metrics.category_distribution[selectedCompany.id] || {}
            }}
            competitors={suggestedCompetitors}
            totalNews={Object.values(analysisData.metrics.news_volume).reduce((sum: number, v: unknown) => sum + Number(v), 0)}
          />

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {renderTopicDistributionCard(selectedCompany.id)}
            {renderSentimentDistributionCard(selectedCompany.id)}
            {renderPriorityCard(selectedCompany.id)}
          </div>

          {renderChangeEventsSection()}
          
          {/* News Volume Comparison */}
          <div className="bg-white rounded-lg shadow-md p-6">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold text-gray-900">
                News Volume Comparison
              </h3>
            </div>
            <div className="space-y-3">
              {analysisData.companies.map((company: Company, index: number) => {
                const volume = analysisData.metrics.news_volume[company.id] || 0
                const maxVolume = Math.max(...Object.values(analysisData.metrics.news_volume).map(v => Number(v)))
                const percentage = maxVolume > 0 ? (volume / maxVolume) * 100 : 0
                const colors = ['bg-blue-500', 'bg-green-500', 'bg-purple-500', 'bg-orange-500', 'bg-pink-500']
                
                return (
                  <div key={company.id}>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium text-gray-700">
                        {company.name}
                      </span>
                      <span className="text-sm text-gray-600">{volume} news</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-3">
                      <div
                        className={`h-3 rounded-full ${colors[index % colors.length]}`}
                        style={{ width: `${percentage}%` }}
                      />
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  )

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
          onClick={() => {
            setAnalysisMode(null)
            // Сбрасываем все состояние при возврате в меню
            setSelectedCompany(null)
            setAnalysisData(null)
            setThemesData(null)
            setError(null)
            setStep('select')
            setSelectedCompetitors([])
            setSuggestedCompetitors([])
            setManuallyAddedCompetitors([])
            clearFilters()
          }}
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

  // Функция для быстрого анализа компании
  const runCompanyAnalysis = async () => {
    if (!selectedCompany) return
    
    setError(null)
    
    try {
      const suggestionsResponse = await ApiService.suggestCompetitors(selectedCompany.id, {
        limit: 5,
        days: 30
      })
      
      const competitorIds = suggestionsResponse.suggestions.slice(0, 3).map(s => s.company.id)
      if (!competitorIds.length) {
        toast.error('Not enough competitor data to run analysis yet')
        return
      }

      setSelectedCompetitors(competitorIds)
      setManuallyAddedCompetitors(suggestionsResponse.suggestions.map(s => s.company))

      await runAnalysis({
        primaryCompany: selectedCompany,
        competitorIds,
        filters: {
          source_types: sourceTypeFilters,
          topics: topicFilters,
          sentiments: sentimentFilters,
          min_priority: minPriorityFilter
        }
      })
    } catch (err: any) {
      console.error('Error running company analysis:', err)
      setError(err.response?.data?.detail || err.message || 'Failed to run analysis')
    }
  }
  
  // Шаг 1: Выбор основной компании
  const renderCompanySelection = () => (
    <div className="max-w-2xl mx-auto">
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">
          Select Your Company
        </h2>
        <p className="text-gray-600 mb-6">
          Choose the company you want to analyze and find competitors for.
        </p>
        
        <CompanySelector
          onSelect={setSelectedCompany}
          selectedCompany={selectedCompany}
        />
        
        <div className="mt-6 flex justify-end">
          <button
            onClick={() => {
              if (selectedCompany) {
                loadCompetitorSuggestions()
                setStep('suggest')
              }
            }}
            disabled={!selectedCompany}
            className="bg-primary-600 text-white px-6 py-3 rounded-lg hover:bg-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
          >
            Continue
            <ArrowRight className="w-5 h-5 ml-2" />
          </button>
        </div>
      </div>
    </div>
  )
  
  // Шаг 2: Подбор конкурентов
  const renderCompetitorSuggestion = () => (
    <div className="max-w-4xl mx-auto">
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">
              Choose Competitors
            </h2>
            <p className="text-gray-600 mt-1">
              AI has suggested competitors based on similarity analysis
            </p>
          </div>
          <button
            onClick={() => setStep('select')}
            className="text-gray-600 hover:text-gray-800 flex items-center"
          >
            <ArrowLeft className="w-4 h-4 mr-1" />
            Back
          </button>
        </div>
        
        {error && (
          <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-lg border border-red-200 text-sm">
            {error}
          </div>
        )}
        
        <CompetitorSuggestions
          suggestions={[
            ...suggestedCompetitors,
            ...manuallyAddedCompetitors.map(company => ({
              company,
              similarity_score: 0, // Ручные добавления не имеют similarity score
              common_categories: [],
              reason: 'Manually added competitor'
            }))
          ]}
          selectedCompetitors={selectedCompetitors}
          onToggleCompetitor={toggleCompetitor}
          onAddManual={(company: Company) => {
            setManuallyAddedCompetitors(prev => [...prev, company])
            // Автоматически добавляем в selectedCompetitors
            if (!selectedCompetitors.includes(company.id)) {
              setSelectedCompetitors(prev => [...prev, company.id])
            }
          }}
        />

        <div className="mt-6">
          {renderFilterControls()}
        </div>
        
        <div className="mt-6 flex justify-between">
          <button
            onClick={() => setStep('select')}
            className="text-gray-600 hover:text-gray-800 flex items-center"
          >
            <ArrowLeft className="w-4 h-4 mr-1" />
            Back
          </button>
          <button
            onClick={() => {
              if (selectedCompetitors.length > 0) {
                runAnalysis()
              }
            }}
            disabled={selectedCompetitors.length === 0}
            className="bg-primary-600 text-white px-6 py-3 rounded-lg hover:bg-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
          >
            Analyze
            <ArrowRight className="w-5 h-5 ml-2" />
          </button>
        </div>
      </div>
    </div>
  )
  
  // Шаг 3: Анализ
  const renderAnalysis = () => (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">
            Analysis Results
          </h2>
          <p className="text-gray-600 mt-1">
            Comprehensive analysis of {selectedCompany?.name} and its competitors
          </p>
        </div>
        <div className="flex space-x-3">
          <button
            onClick={() => setStep('suggest')}
            className="text-gray-600 hover:text-gray-800 flex items-center"
          >
            <ArrowLeft className="w-4 h-4 mr-1" />
            Back
          </button>
          <ExportMenu onExport={handleExport} />
        </div>
      </div>
      
      {loading && (
        <div className="text-center py-8">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Analyzing competitors...</p>
        </div>
      )}
      
      {analysisData && (
        <div className="space-y-6">
          {renderImpactPanel()}
          {renderPresetManager()}
          {renderAnalyticsTabs()}
        </div>
      )}
    </div>
  )
  
  const loadCompetitorSuggestions = async () => {
    if (!selectedCompany) return
    
    setLoading(true)
    setError(null)
    
    try {
      const response = await ApiService.suggestCompetitors(selectedCompany.id, {
        limit: 5,
        days: 30
      })
      setSuggestedCompetitors(response.suggestions)
    } catch (err: any) {
      console.error('Error loading suggestions:', err)
      setError(err.response?.data?.detail || 'Failed to load competitor suggestions')
    } finally {
      setLoading(false)
    }
  }
  
  const toggleCompetitor = (companyId: string) => {
    setSelectedCompetitors(prev => 
      prev.includes(companyId)
        ? prev.filter(id => id !== companyId)
        : [...prev, companyId]
    )
  }
  
  const runAnalysis = async (
    override?: {
      primaryCompany: Company
      competitorIds: string[]
      filters?: {
        source_types?: string[]
        topics?: string[]
        sentiments?: string[]
        min_priority?: number | null
      }
    }
  ) => {
    const primaryCompany = override?.primaryCompany ?? selectedCompany
    const competitorIds = override?.competitorIds ?? selectedCompetitors

    if (!primaryCompany || !primaryCompany.id || !Array.isArray(competitorIds) || competitorIds.length === 0) {
      setError('Select a primary company and at least one competitor before running analysis.')
      return
    }
    
    setImpactSnapshot(null)
    setImpactSeries(null)
    setAnalyticsEdges([])
    setAnalyticsError(null)
    setAnalysisData(null)
    setThemesData(null)
    setComparisonData(null)
    setComparisonError(null)
    setComparisonSubjects([])
    setAbSelection({ left: null, right: null })
    setStep('analyze')
    
    setLoading(true)
    setError(null)
    
    try {
      const allCompanyIds = [primaryCompany.id, ...competitorIds].map(id => String(id))
      const dateFrom = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString()
      const dateTo = new Date().toISOString()
      setAnalysisRange({ from: dateFrom, to: dateTo })
      
      const comparisonPayload = applyFiltersToPayload({
        company_ids: allCompanyIds,
        date_from: dateFrom,
        date_to: dateTo
      }, {
        sourceTypes: override?.filters?.source_types ?? sourceTypeFilters,
        topics: override?.filters?.topics ?? topicFilters,
        sentiments: override?.filters?.sentiments ?? sentimentFilters,
        minPriority: override?.filters?.min_priority ?? minPriorityFilter
      })

      const response = await ApiService.compareCompanies(comparisonPayload)
      setAnalysisData(response)
      
      const themesResponse = await ApiService.analyzeThemes(allCompanyIds, {
        date_from: dateFrom,
        date_to: dateTo
      })
      setThemesData(themesResponse)

      const subjects: ComparisonSubjectRequest[] = response.companies.map((company: Company) => ({
        subject_type: 'company',
        reference_id: company.id,
        label: company.name
      }))
      await fetchComparisonData(subjects, {
        period: comparisonPeriod,
        lookback: comparisonLookback,
        range: { from: dateFrom, to: dateTo }
      })
      
      await loadAnalyticsInsights(primaryCompany.id)
      await loadReportPresets()
      setStep('analyze')
    } catch (err: any) {
      console.error('Error running analysis:', err)
      console.error('Error details:', err.response?.data)
      setError(err.response?.data?.detail || 'Failed to run analysis')
    } finally {
      setLoading(false)
    }
  }
  
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
        {!analysisMode && renderModeSelection()}
        {analysisMode === 'company' && renderCompanyAnalysis()}
        {analysisMode === 'custom' && renderCustomAnalysis()}
      </div>
    </div>
  )
}