import { Briefcase, FileText, Globe, History, Layout, RefreshCw, Search, ShoppingBag, Tag } from 'lucide-react'
import { useMemo, useState } from 'react'

import { ErrorBanner } from '@/components/ErrorBanner'
import { LoadingOverlay } from '@/components/LoadingOverlay'

import type {
  ChangeProcessingStatus,
  Company,
  CompetitorChangeEvent
} from '@/types'

import { formatLabel, formatPriceDisplay } from '../utils/formatters'

type ChangeEventsSectionProps = {
  company: Company | null
  events: CompetitorChangeEvent[]
  loading: boolean
  error?: string | null
  onRefresh: () => void
  onRecompute: (eventId: string) => void
  recomputingEventId: string | null
  hasMore?: boolean
  onLoadMore?: () => void
  loadingMore?: boolean
}

const statusBadgeStyles: Record<ChangeProcessingStatus, string> = {
  success: 'bg-green-100 text-green-700',
  skipped: 'bg-gray-100 text-gray-600',
  error: 'bg-red-100 text-red-600'
}

// Change type detection and icons
type ChangeType = 
  | 'website_structure' 
  | 'marketing_banner' 
  | 'marketing_landing' 
  | 'marketing_product' 
  | 'marketing_jobs' 
  | 'seo_meta' 
  | 'seo_structure'
  | 'pricing'
  | 'other'

const getChangeType = (event: CompetitorChangeEvent): ChangeType => {
  // Check raw_diff for change type
  if (event.raw_diff?.type) {
    const type = event.raw_diff.type as string
    if (type.includes('navigation') || type.includes('structure')) return 'website_structure'
    if (type.includes('banner')) return 'marketing_banner'
    if (type.includes('landing')) return 'marketing_landing'
    if (type.includes('product')) return 'marketing_product'
    if (type.includes('job') || type.includes('career')) return 'marketing_jobs'
    if (type.includes('seo') || type.includes('meta')) return 'seo_meta'
    if (type.includes('sitemap') || type.includes('robots')) return 'seo_structure'
  }
  
  // Check source_type
  if (event.source_type === 'press_release') return 'other'
  
  // Check changed_fields for pricing
  if (event.changed_fields?.some(f => f.field === 'price' || f.field === 'pricing')) {
    return 'pricing'
  }
  
  // Default based on source_type
  if (['facebook', 'instagram', 'linkedin', 'youtube', 'tiktok', 'twitter'].includes(event.source_type)) {
    return 'other'
  }
  
  return 'other'
}

const changeTypeIcons: Record<ChangeType, typeof Globe> = {
  website_structure: Layout,
  marketing_banner: Tag,
  marketing_landing: FileText,
  marketing_product: ShoppingBag,
  marketing_jobs: Briefcase,
  seo_meta: Search,
  seo_structure: Search,
  pricing: ShoppingBag,
  other: Globe
}

const changeTypeLabels: Record<ChangeType, string> = {
  website_structure: 'Website Structure',
  marketing_banner: 'Marketing Banner',
  marketing_landing: 'Landing Page',
  marketing_product: 'Product',
  marketing_jobs: 'Job Postings',
  seo_meta: 'SEO Meta',
  seo_structure: 'SEO Structure',
  pricing: 'Pricing',
  other: 'Other'
}

const renderChangeFieldSummary = (change: Record<string, any>): string => {
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

export const ChangeEventsSection = ({
  company,
  events,
  loading,
  error,
  onRefresh,
  onRecompute,
  recomputingEventId,
  hasMore,
  onLoadMore,
  loadingMore
}: ChangeEventsSectionProps) => {
  const [selectedChangeType, setSelectedChangeType] = useState<ChangeType | 'all'>('all')
  
  if (!company) return null

  // Group events by change type
  const eventsByType = useMemo(() => {
    const grouped: Record<ChangeType, CompetitorChangeEvent[]> = {
      website_structure: [],
      marketing_banner: [],
      marketing_landing: [],
      marketing_product: [],
      marketing_jobs: [],
      seo_meta: [],
      seo_structure: [],
      pricing: [],
      other: []
    }
    
    events.forEach(event => {
      const type = getChangeType(event)
      grouped[type].push(event)
    })
    
    return grouped
  }, [events])

  // Get available change types
  const availableTypes = useMemo(() => {
    return (Object.keys(eventsByType) as ChangeType[]).filter(
      type => eventsByType[type].length > 0
    )
  }, [eventsByType])

  // Filter events based on selected type
  const filteredEvents = useMemo(() => {
    if (selectedChangeType === 'all') return events
    return eventsByType[selectedChangeType] || []
  }, [events, selectedChangeType, eventsByType])

  return (
    <div className="bg-white rounded-lg shadow-md border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <div className="flex items-center space-x-2">
            <History className="w-5 h-5 text-blue-600" />
            <h3 className="text-lg font-semibold text-gray-900">Latest Changes</h3>
          </div>
          <p className="text-xs text-gray-500 mt-1">
            Changes detected for {company.name}
          </p>
        </div>
        <button
          type="button"
          onClick={onRefresh}
          disabled={loading}
          className="flex items-center text-sm text-blue-600 hover:text-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <RefreshCw className={`w-4 h-4 mr-1 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Change Type Filters */}
      {availableTypes.length > 0 && (
        <div className="mb-4 flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => setSelectedChangeType('all')}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
              selectedChangeType === 'all'
                ? 'bg-blue-100 text-blue-700 border border-blue-300'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200 border border-gray-200'
            }`}
          >
            All ({events.length})
          </button>
          {availableTypes.map(type => {
            const Icon = changeTypeIcons[type]
            return (
              <button
                key={type}
                type="button"
                onClick={() => setSelectedChangeType(type)}
                className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors flex items-center gap-1.5 ${
                  selectedChangeType === type
                    ? 'bg-blue-100 text-blue-700 border border-blue-300'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200 border border-gray-200'
                }`}
              >
                <Icon className="w-3 h-3" />
                {changeTypeLabels[type]} ({eventsByType[type].length})
              </button>
            )
          })}
        </div>
      )}

      {error ? (
        <ErrorBanner
          className="mb-3 text-xs"
          compact
          message={error}
          onRetry={onRefresh}
          retryLabel="Try again"
        />
      ) : null}

      {loading ? (
        <LoadingOverlay
          className="py-6"
          label="Loading change history…"
          description="Fetching pricing and product updates"
        />
      ) : filteredEvents.length === 0 ? (
        <p className="text-sm text-gray-500">
          {selectedChangeType === 'all' 
            ? 'No changes detected yet. We will surface changes here as soon as they are captured.'
            : `No ${changeTypeLabels[selectedChangeType as ChangeType]} changes found.`
          }
        </p>
      ) : (
        <>
          <div className="space-y-4">
            {filteredEvents.map(event => {
              const changeType = getChangeType(event);
              const Icon = changeTypeIcons[changeType];
              return (
              <div key={event.id} className="border border-gray-200 rounded-lg p-4">
                <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-3">
                  <div>
                    <div className="flex items-center space-x-2">
                      <Icon className="w-4 h-4 text-gray-500" />
                      <span className="text-sm font-semibold text-gray-900">
                        {changeTypeLabels[changeType]}
                      </span>
                      <span className="text-xs text-gray-500">
                        ({formatLabel(event.source_type)})
                      </span>
                      <span
                        className={`text-xs font-medium px-2 py-0.5 rounded-full ${statusBadgeStyles[event.processing_status]}`}
                      >
                        {formatLabel(event.processing_status)}
                      </span>
                    </div>
                    <p className="text-sm text-gray-700 mt-2">
                      {event.change_summary || 'Change detected'}
                    </p>
                    {event.changed_fields?.length ? (
                      <ul className="mt-3 space-y-1">
                        {event.changed_fields.slice(0, 3).map((change, index) => (
                          <li key={`${event.id}-field-${index}`} className="text-xs text-gray-500">
                            • {renderChangeFieldSummary(change)}
                          </li>
                        ))}
                      </ul>
                    ) : null}
                  </div>
                  <div className="flex flex-col items-start gap-2">
                    <span className="text-xs text-gray-400">
                      {new Date(event.detected_at).toLocaleString()}
                    </span>
                    <button
                      type="button"
                      onClick={() => onRecompute(event.id)}
                      disabled={recomputingEventId === event.id}
                      className="text-xs px-3 py-1.5 rounded-md border border-blue-200 text-blue-700 hover:bg-blue-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {recomputingEventId === event.id ? 'Recomputing…' : 'Recompute diff'}
                    </button>
                  </div>
                </div>
              </div>
              )
            })}
          </div>
          {hasMore && onLoadMore ? (
            <div className="pt-4 text-center">
              <button
                type="button"
                onClick={onLoadMore}
                disabled={loadingMore}
                className="text-sm px-4 py-2 rounded-md border border-blue-200 text-blue-700 hover:bg-blue-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loadingMore ? 'Loading more…' : 'Load more changes'}
              </button>
            </div>
          ) : null}
        </>
      )}
    </div>
  )
}

