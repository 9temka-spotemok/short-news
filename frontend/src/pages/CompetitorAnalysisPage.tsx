import { ArrowLeft, ArrowRight, BarChart3, Building2, Clock, Download, Filter, Gauge, History, PieChart, RefreshCw, Smile, Users } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import BrandPreview from '../components/BrandPreview'
import { BusinessIntelligence } from '../components/BusinessIntelligence'
import CompanySelector from '../components/CompanySelector'
import CompetitorSuggestions from '../components/CompetitorSuggestions'
import { ExportMenu } from '../components/ExportMenu'
import { InnovationMetrics } from '../components/InnovationMetrics'
import { MarketPosition } from '../components/MarketPosition'
import ProgressSteps from '../components/ProgressSteps'
import { TeamInsights } from '../components/TeamInsights'
import ThemeAnalysis from '../components/ThemeAnalysis'
import { ApiService } from '../services/api'
import { ChangeProcessingStatus, Company, CompetitorChangeEvent } from '../types'

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

  // Очищаем данные анализа при смене компании в режиме Company Analysis
  useEffect(() => {
    if (analysisMode === 'company' && selectedCompany) {
      setAnalysisData(null)
      setThemesData(null)
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

  const applyFiltersToPayload = <T extends Record<string, unknown>>(payload: T): FilteredPayload<T> => {
    const nextPayload: FilteredPayload<T> = { ...payload }
    if (sourceTypeFilters.length) {
      nextPayload.source_types = sourceTypeFilters
    }
    if (topicFilters.length) {
      nextPayload.topics = topicFilters
    }
    if (sentimentFilters.length) {
      nextPayload.sentiments = sentimentFilters
    }
    if (minPriorityFilter !== null) {
      nextPayload.min_priority = Number(minPriorityFilter.toFixed(2))
    }
    return nextPayload
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

  const handleExport = async (format: 'json' | 'pdf' | 'csv') => {
    if (!analysisData || !selectedCompany) return
    
    try {
      // Собираем все данные для экспорта
      const exportData = {
        // Основные данные анализа
        ...analysisData,
        
        // Дополнительные данные для полного отчета
        report: {
          company: selectedCompany,
          analysisDate: new Date().toISOString(),
          analysisMode: analysisMode,
          
          // Business Intelligence данные
          businessIntelligence: {
            metrics: analysisData.metrics.category_distribution[selectedCompany.id] || {},
            activityScore: analysisData.metrics.activity_score[selectedCompany.id] || 0,
            competitorCount: suggestedCompetitors.length,
            totalActivity: Object.values(analysisData.metrics.category_distribution[selectedCompany.id] || {}).reduce((sum: number, v: unknown) => sum + Number(v), 0)
          },
          
          // Innovation & Technology данные
          innovationTechnology: {
            metrics: analysisData.metrics.category_distribution[selectedCompany.id] || {},
            totalNews: analysisData.metrics.news_volume[selectedCompany.id] || 0,
            technicalActivity: Object.entries(analysisData.metrics.category_distribution[selectedCompany.id] || {})
              .filter(([key]) => ['technical_update', 'api_update', 'research_paper', 'model_release', 'performance_improvement', 'security_update'].includes(key))
              .reduce((sum, [, count]) => sum + Number(count), 0)
          },
          
          // Team & Culture данные
          teamCulture: {
            metrics: analysisData.metrics.category_distribution[selectedCompany.id] || {},
            totalNews: analysisData.metrics.news_volume[selectedCompany.id] || 0,
            activityScore: analysisData.metrics.activity_score[selectedCompany.id] || 0,
            teamActivity: Object.entries(analysisData.metrics.category_distribution[selectedCompany.id] || {})
              .filter(([key]) => ['community_event', 'strategic_announcement', 'research_paper'].includes(key))
              .reduce((sum, [, count]) => sum + Number(count), 0)
          },
          
          // Market Position данные
          marketPosition: {
            company: selectedCompany,
            metrics: {
              news_volume: analysisData.metrics.news_volume[selectedCompany.id] || 0,
              activity_score: analysisData.metrics.activity_score[selectedCompany.id] || 0,
              category_distribution: analysisData.metrics.category_distribution[selectedCompany.id] || {}
            },
            competitors: suggestedCompetitors,
            totalNews: Object.values(analysisData.metrics.news_volume).reduce((sum: number, v: unknown) => sum + Number(v), 0)
          },
          
          // News Volume Comparison данные
          newsVolumeComparison: {
            companies: analysisData.companies,
            metrics: analysisData.metrics.news_volume,
            dateFrom: analysisData.date_from,
            dateTo: analysisData.date_to
          }
        }
      }
      
      await ApiService.exportAnalysis(exportData, format)
    } catch (err) {
      console.error('Export failed:', err)
      setError('Export failed. Please try again.')
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
    
    setLoading(true)
    setError(null)
    
    try {
      // Получаем предложения конкурентов
      const suggestionsResponse = await ApiService.suggestCompetitors(selectedCompany.id, {
        limit: 5,
        days: 30
      })
      
      // Берем первых 3 конкурентов для анализа
      const competitorIds = suggestionsResponse.suggestions.slice(0, 3).map(s => s.company.id)
      const allCompanyIds = [selectedCompany.id, ...competitorIds]
      
      // Выполняем анализ
      const dateFrom = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString()
      const dateTo = new Date().toISOString()
      
      const payload = applyFiltersToPayload({
        company_ids: allCompanyIds,
        date_from: dateFrom,
        date_to: dateTo
      })

      const response = await ApiService.compareCompanies(payload)
      
      setAnalysisData(response)
      
    } catch (err: any) {
      console.error('Error running company analysis:', err)
      setError(err.response?.data?.detail || 'Failed to run analysis')
    } finally {
      setLoading(false)
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
                setStep('analyze')
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
          <button
            onClick={exportResults}
            className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition-colors flex items-center"
          >
            <Download className="w-4 h-4 mr-2" />
            Export
          </button>
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
          {/* Brand Preview */}
          <BrandPreview
            company={selectedCompany!}
            stats={{
              total_news: analysisData.metrics.news_volume[selectedCompany!.id] || 0,
              categories_breakdown: Object.entries(analysisData.metrics.category_distribution[selectedCompany!.id] || {}).map(([category, count]) => ({
                category,
                count: count as number
              })),
              activity_score: analysisData.metrics.activity_score[selectedCompany!.id] || 0,
              avg_priority: analysisData.metrics.avg_priority?.[selectedCompany!.id] ?? 0.5
            }}
          />

          {renderActiveFiltersSummary(analysisData.filters)}

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {renderTopicDistributionCard(selectedCompany!.id)}
            {renderSentimentDistributionCard(selectedCompany!.id)}
            {renderPriorityCard(selectedCompany!.id)}
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
          
          {/* Theme Analysis */}
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
  
  const runAnalysis = async () => {
    if (!selectedCompany || selectedCompetitors.length === 0) return
    
    setLoading(true)
    setError(null)
    
    try {
      // Валидация данных
      if (!selectedCompany || !selectedCompany.id) {
        throw new Error('Selected company is invalid')
      }
      
      if (!Array.isArray(selectedCompetitors)) {
        throw new Error('Selected competitors is not an array')
      }
      
      // Проверяем что все ID являются строками
      const allCompanyIds = [selectedCompany.id, ...selectedCompetitors].map(id => String(id))
      
      // Исправить формат дат - добавить время
      const dateFrom = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString()
      const dateTo = new Date().toISOString()
      
      console.log('Sending request with:', {
        company_ids: allCompanyIds,
        date_from: dateFrom,
        date_to: dateTo
      })
      
      console.log('Selected company:', selectedCompany)
      console.log('Selected competitors:', selectedCompetitors)
      console.log('All company IDs:', allCompanyIds)
      console.log('Request object:', {
        company_ids: allCompanyIds,
        date_from: dateFrom,
        date_to: dateTo
      })
      
      const comparisonPayload = applyFiltersToPayload({
        company_ids: allCompanyIds,
        date_from: dateFrom,
        date_to: dateTo
      })

      const response = await ApiService.compareCompanies(comparisonPayload)
      
      setAnalysisData(response)
      
      // Get themes data
      const themesResponse = await ApiService.analyzeThemes(allCompanyIds, {
        date_from: dateFrom,
        date_to: dateTo
      })
      
      setThemesData(themesResponse)
      
    } catch (err: any) {
      console.error('Error running analysis:', err)
      console.error('Error details:', err.response?.data)
      setError(err.response?.data?.detail || 'Failed to run analysis')
    } finally {
      setLoading(false)
    }
  }
  
  const exportResults = () => {
    if (!analysisData) return
    
    const exportData = {
      company: selectedCompany,
      competitors: analysisData.companies.filter((c: Company) => c.id !== selectedCompany?.id),
      analysis: analysisData,
      themes: themesData,
      generated_at: new Date().toISOString()
    }
    
    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `competitor-analysis-${selectedCompany?.name}-${new Date().toISOString().split('T')[0]}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
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