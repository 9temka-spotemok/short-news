import MonitoringSourcesCard from '@/components/monitoring/MonitoringSourcesCard'
import { ApiService } from '@/services/api'
import type { Report } from '@/types'
import { useQuery } from '@tanstack/react-query'
import { formatDistance } from 'date-fns'
import { enUS } from 'date-fns/locale'
import { ChevronDown, ChevronUp, Edit, ExternalLink, Github, Globe, RefreshCw, Trash2, Twitter, UserPlus } from 'lucide-react'
import { useMemo } from 'react'

interface ReportCardProps {
  report: Report
  isExpanded: boolean
  activeTab: 'news' | 'sources' | 'pricing' | 'competitors' | 'monitoring'
  onExpand: () => void
  onTabChange: (tab: 'news' | 'sources' | 'pricing' | 'competitors' | 'monitoring') => void
  reportData?: Report // Полные данные (только для status='ready')
  onRetry?: () => void // Функция для повторного создания отчёта
  onLoadCompetitors?: () => Promise<void> // Функция для загрузки конкурентов
  onEdit?: () => void // Функция для редактирования отчёта
  onDelete?: () => void // Функция для удаления отчёта
  onAddCompetitorsToTracked?: () => void // Функция для добавления конкурентов в Tracked Companies
}

// Category labels
const categoryLabels: Record<string, string> = {
  'product_update': 'Product Updates',
  'technical_update': 'Technical Updates',
  'strategic_announcement': 'Strategic Announcements',
  'funding_news': 'Funding News',
  'pricing_change': 'Pricing Changes',
  'research_paper': 'Research Papers',
  'community_event': 'Community Events',
  'partnership': 'Partnerships',
  'acquisition': 'Acquisitions',
  'integration': 'Integrations',
  'security_update': 'Security Updates',
  'api_update': 'API Updates',
  'model_release': 'Model Releases',
  'performance_improvement': 'Performance Improvements',
  'feature_deprecation': 'Feature Deprecations',
}

const formatDate = (dateString: string) => {
  try {
    const date = new Date(dateString)
    return formatDistance(date, new Date(), { addSuffix: true, locale: enUS })
  } catch {
    return 'Recently'
  }
}

export default function ReportCard({
  report,
  isExpanded,
  activeTab,
  onExpand,
  onTabChange,
  reportData,
  onRetry,
  onLoadCompetitors,
  onEdit,
  onDelete,
  onAddCompetitorsToTracked,
}: ReportCardProps) {
  const company = reportData?.company || report.company
  const status = report.status

  // Добавить логику для формирования sources с Twitter
  const sourcesWithTwitter = useMemo(() => {
    const sources = reportData?.sources || []
    
    // Если есть twitter_handle и его еще нет в sources, добавить
    if (company?.twitter_handle) {
      const twitterUrl = `https://twitter.com/${company.twitter_handle}`
      const hasTwitterInSources = sources.some(
        (source) => source.url === twitterUrl || source.url.includes('twitter.com')
      )
      
      if (!hasTwitterInSources) {
        return [
          ...sources,
          {
            url: twitterUrl,
            type: 'twitter',
            count: 0
          }
        ]
      }
    }
    
    return sources
  }, [reportData?.sources, company?.twitter_handle])

  // Status badge colors
  const getStatusBadgeClass = (status: string) => {
    switch (status) {
      case 'ready':
        return 'bg-green-100 text-green-700 border-green-200'
      case 'processing':
        return 'bg-blue-100 text-blue-700 border-blue-200'
      case 'error':
        return 'bg-red-100 text-red-700 border-red-200'
      default:
        return 'bg-gray-100 text-gray-700 border-gray-200'
    }
  }

  return (
    <div className="card p-6 hover:shadow-lg transition-shadow">
      <div className="flex items-start gap-4">
        {/* Logo */}
        <div className="flex-shrink-0">
          {company?.logo_url ? (
            <img
              src={company.logo_url}
              alt={company.name || report.query}
              className="w-16 h-16 rounded-lg object-cover"
              onError={(e) => {
                e.currentTarget.style.display = 'none'
              }}
            />
          ) : (
            <div className="w-16 h-16 rounded-lg bg-gray-200 flex items-center justify-center">
              <Globe className="h-8 w-8 text-gray-400" />
            </div>
          )}
        </div>

        {/* Report Info */}
        <div className="flex-1 min-w-0">
          {/* Header - always visible */}
          <div className="flex items-start justify-between gap-4 mb-2">
            <div className="flex-1 min-w-0">
              <h3 className="text-lg font-semibold text-gray-900">
                {company?.name || report.query}
              </h3>
              <div className="flex items-center gap-2 mt-1">
                <span className={`inline-block text-xs px-2 py-1 rounded-full border ${getStatusBadgeClass(status)}`}>
                  {status === 'processing' ? 'Processing...' : status === 'ready' ? 'Ready' : 'Error'}
                </span>
                {company?.category && (
                  <span className="inline-block text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded-full">
                    {company.category}
                  </span>
                )}
              </div>
            </div>
            <div className="flex items-center gap-2">
              <p className="text-xs text-gray-500 whitespace-nowrap">
                Created {formatDate(report.created_at)}
              </p>
              {/* Action Buttons */}
              <div className="flex items-center gap-1">
                {onEdit && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      onEdit()
                    }}
                    className="flex-shrink-0 p-1.5 hover:bg-gray-100 rounded transition-colors text-gray-500 hover:text-primary-600"
                    aria-label="Edit report"
                    title="Edit report"
                  >
                    <Edit className="h-4 w-4" />
                  </button>
                )}
                {onDelete && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      onDelete()
                    }}
                    className="flex-shrink-0 p-1.5 hover:bg-red-50 rounded transition-colors text-gray-500 hover:text-red-600"
                    aria-label="Delete report"
                    title="Delete report"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                )}
                {/* Expand/Collapse Button */}
                <button
                  onClick={onExpand}
                  className="flex-shrink-0 p-1 hover:bg-gray-100 rounded transition-colors"
                  aria-label={isExpanded ? 'Collapse' : 'Expand'}
                >
                  {isExpanded ? (
                    <ChevronUp className="h-5 w-5 text-gray-500" />
                  ) : (
                    <ChevronDown className="h-5 w-5 text-gray-500" />
                  )}
                </button>
              </div>
            </div>
          </div>

          {/* Expanded content */}
          {isExpanded && (
            <div className="mt-4 space-y-4">
              {/* Processing state */}
              {status === 'processing' && (
                <div className="flex items-center gap-2 py-4">
                  <div className="w-4 h-4 border-2 border-primary-600 border-t-transparent rounded-full animate-spin"></div>
                  <span className="text-sm text-gray-500">Preparing report...</span>
                </div>
              )}

              {/* Error state */}
              {status === 'error' && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                  <p className="text-sm text-red-800 font-medium mb-1">Error generating report</p>
                  <p className="text-sm text-red-600 mb-3">{report.error_message || 'Unknown error occurred'}</p>
                  {onRetry && (
                    <button
                      onClick={onRetry}
                      className="btn btn-outline btn-sm flex items-center gap-2 text-red-700 border-red-300 hover:bg-red-100"
                    >
                      <RefreshCw className="h-4 w-4" />
                      Retry Report
                    </button>
                  )}
                </div>
              )}

              {/* Ready state */}
              {status === 'ready' && reportData && (
                <>
                  {/* Описание компании - выделенный блок */}
                  {company?.description && (
                    <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-lg p-4">
                      <p className="text-sm text-gray-700 leading-relaxed">{company.description}</p>
                    </div>
                  )}

                  {/* Категории новостей - всегда видимы */}
                  {reportData.categories && reportData.categories.length > 0 && (
                    <div>
                      <p className="text-xs font-medium text-gray-700 mb-2">Категории новостей:</p>
                      <div className="flex flex-wrap gap-2">
                        {reportData.categories.map((cat) => (
                          <span
                            key={cat.technicalCategory}
                            className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-primary-100 text-primary-700 border border-primary-200"
                          >
                            {cat.category}
                            <span className="ml-1.5 px-1.5 py-0.5 bg-primary-200 rounded-full text-primary-800">
                              {cat.count}
                            </span>
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Табы */}
                  <div className="border-t border-gray-200 pt-4">
                    <div className="flex space-x-1 border-b border-gray-200 mb-4">
                      {['news', 'sources', 'pricing', 'competitors', 'monitoring'].map((tab) => (
                        <button
                          key={tab}
                          onClick={() => onTabChange(tab as 'news' | 'sources' | 'pricing' | 'competitors' | 'monitoring')}
                          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                            activeTab === tab
                              ? 'border-primary-500 text-primary-600'
                              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                          }`}
                        >
                          {tab === 'news' && 'News'}
                          {tab === 'sources' && 'Sources'}
                          {tab === 'pricing' && 'Pricing'}
                          {tab === 'competitors' && 'Competitors'}
                          {tab === 'monitoring' && 'Monitoring'}
                        </button>
                      ))}
                    </div>

                    {/* Tab Content */}
                    {activeTab === 'news' && (
                      <div className="space-y-3">
                        {reportData.news && reportData.news.length > 0 ? (
                          reportData.news.map((news) => (
                            <div key={news.id} className="border-l-2 border-primary-200 pl-3 py-1">
                              <a
                                href={news.source_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-sm text-gray-900 hover:text-primary-600 font-medium block"
                              >
                                {news.title}
                              </a>
                              <div className="flex items-center gap-2 mt-1">
                                <span className="text-xs text-gray-500">
                                  {formatDate(news.published_at || news.created_at || '')}
                                </span>
                                {news.category && (
                                  <>
                                    <span className="text-xs text-gray-400">•</span>
                                    <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">
                                      {categoryLabels[news.category] || news.category}
                                    </span>
                                  </>
                                )}
                              </div>
                            </div>
                          ))
                        ) : (
                          <p className="text-sm text-gray-500 py-4">Новости не найдены</p>
                        )}
                      </div>
                    )}

                    {activeTab === 'sources' && (
                      <div>
                        {sourcesWithTwitter && sourcesWithTwitter.length > 0 ? (
                          <div className="space-y-2">
                            {sourcesWithTwitter.map((source, idx) => (
                              <div key={idx} className="flex items-start justify-between gap-2 p-2 bg-gray-50 rounded text-sm">
                                <div className="flex-1 min-w-0">
                                  <a
                                    href={source.url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-primary-600 hover:text-primary-700 break-all inline-flex items-center gap-1"
                                  >
                                    {source.url}
                                    <ExternalLink className="h-3 w-3" />
                                  </a>
                                  <span className="text-xs text-gray-500 ml-2 capitalize inline-flex items-center gap-1">
                                    {source.type === 'twitter' && <Twitter className="h-3 w-3" />}
                                    ({source.type})
                                  </span>
                                </div>
                                <span className="text-xs text-gray-500 whitespace-nowrap">
                                  {source.count} новостей
                                </span>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <p className="text-xs text-gray-500 py-4">Источники не найдены</p>
                        )}
                      </div>
                    )}

                    {activeTab === 'pricing' && (
                      <div className="space-y-4">
                        {reportData.pricing?.description && 
                         (reportData.pricing.description.toLowerCase().includes('pricing') || 
                          reportData.pricing.description.toLowerCase().includes('price') ||
                          reportData.pricing.description.toLowerCase().includes('$')) && (
                          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                            <h4 className="text-sm font-semibold text-gray-900 mb-2">Информация о ценообразовании:</h4>
                            <p className="text-sm text-gray-700 leading-relaxed">
                              {reportData.pricing.description}
                            </p>
                          </div>
                        )}

                        {reportData.pricing?.news && reportData.pricing.news.length > 0 ? (
                          <div>
                            <h4 className="text-sm font-semibold text-gray-900 mb-3">Последние изменения цен:</h4>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                              {reportData.pricing.news.map((news) => (
                                <div key={news.id} className="bg-gradient-to-br from-blue-50 to-indigo-50 border border-blue-200 rounded-lg p-4">
                                  <a
                                    href={news.source_url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-sm text-gray-900 hover:text-primary-600 font-semibold block mb-2"
                                  >
                                    {news.title}
                                  </a>
                                  {news.summary && (
                                    <p className="text-xs text-gray-600 mb-2 line-clamp-2">{news.summary}</p>
                                  )}
                                  <div className="text-xs text-gray-500">
                                    {formatDate(news.published_at || news.created_at || '')}
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        ) : (
                          !reportData.pricing?.description && (
                            <div className="text-center py-8 bg-gray-50 rounded-lg border border-gray-200">
                              <p className="text-sm text-gray-500">
                                Информация о ценообразовании пока недоступна
                              </p>
                            </div>
                          )
                        )}
                      </div>
                    )}

                    {activeTab === 'competitors' && (
                      <div>
                        {!reportData.competitors && onLoadCompetitors ? (
                          <div className="text-center py-8">
                            <button
                              onClick={async () => {
                                await onLoadCompetitors()
                              }}
                              className="btn btn-primary"
                            >
                              Load Competitors
                            </button>
                            <p className="text-xs text-gray-500 mt-2">
                              This may take a few seconds
                            </p>
                          </div>
                        ) : reportData.competitors && reportData.competitors.length > 0 ? (
                          <div className="space-y-3">
                            {/* Add to Tracked Button */}
                            {onAddCompetitorsToTracked && (
                              <div className="mb-3 flex justify-end">
                                <button
                                  onClick={onAddCompetitorsToTracked}
                                  className="btn btn-primary btn-sm flex items-center gap-2"
                                >
                                  <UserPlus className="h-4 w-4" />
                                  Add to Tracked Companies
                                </button>
                              </div>
                            )}
                            {reportData.competitors.map((competitor, idx) => (
                              <div key={idx} className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
                                <div className="flex items-start gap-3">
                                  {/* Logo */}
                                  <div className="flex-shrink-0">
                                    {competitor.company.logo_url ? (
                                      <img
                                        src={competitor.company.logo_url}
                                        alt={competitor.company.name}
                                        className="w-12 h-12 rounded-lg object-cover"
                                        onError={(e) => {
                                          e.currentTarget.style.display = 'none'
                                        }}
                                      />
                                    ) : (
                                      <div className="w-12 h-12 rounded-lg bg-gray-200 flex items-center justify-center">
                                        <Globe className="h-6 w-6 text-gray-400" />
                                      </div>
                                    )}
                                  </div>

                                  {/* Company Info */}
                                  <div className="flex-1 min-w-0">
                                    <div className="flex items-start justify-between gap-2 mb-1">
                                      <div className="flex-1 min-w-0">
                                        <h4 className="text-sm font-semibold text-gray-900">
                                          {competitor.company.name}
                                        </h4>
                                        {competitor.company.website && (
                                          <a
                                            href={competitor.company.website}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="text-xs text-primary-600 hover:text-primary-700 break-all inline-flex items-center gap-1 mt-1"
                                          >
                                            {competitor.company.website}
                                            <ExternalLink className="h-3 w-3" />
                                          </a>
                                        )}
                                      </div>
                                      <div className="flex-shrink-0 text-right">
                                        <span className="text-xs font-medium text-primary-600">
                                          {Math.round(competitor.similarity_score * 100)}% match
                                        </span>
                                      </div>
                                    </div>

                                    {/* Common Categories */}
                                    {competitor.common_categories && competitor.common_categories.length > 0 && (
                                      <div className="flex flex-wrap gap-1 mt-2">
                                        {competitor.common_categories.slice(0, 3).map((cat, catIdx) => (
                                          <span
                                            key={catIdx}
                                            className="inline-block text-xs bg-gray-100 text-gray-700 px-2 py-0.5 rounded-full"
                                          >
                                            {cat}
                                          </span>
                                        ))}
                                        {competitor.common_categories.length > 3 && (
                                          <span className="text-xs text-gray-500">
                                            +{competitor.common_categories.length - 3} more
                                          </span>
                                        )}
                                      </div>
                                    )}

                                    {/* Reason */}
                                    {competitor.reason && (
                                      <p className="text-xs text-gray-600 mt-2 italic">
                                        {competitor.reason}
                                      </p>
                                    )}
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div className="text-center py-8 bg-gray-50 rounded-lg border border-gray-200">
                            <p className="text-sm text-gray-500">
                              Конкуренты не найдены
                            </p>
                            <p className="text-xs text-gray-400 mt-1">
                              Недостаточно данных для анализа конкурентов
                            </p>
                          </div>
                        )}
                      </div>
                    )}

                    {activeTab === 'monitoring' && company?.id && (
                      <MonitoringTabContent companyId={company.id} />
                    )}
                  </div>

                  {/* Website и Social Links - внизу */}
                  {(company?.website || company?.twitter_handle || company?.github_org) && (
                    <div className="pt-4 border-t border-gray-200 space-y-2">
                      {company.website && (
                        <div>
                          <p className="text-xs font-medium text-gray-700 mb-1">Website:</p>
                          <a
                            href={company.website}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-sm text-primary-600 hover:text-primary-700 break-all inline-flex items-center gap-1"
                          >
                            {company.website}
                            <ExternalLink className="h-3 w-3" />
                          </a>
                        </div>
                      )}

                      {(company.twitter_handle || company.github_org) && (
                        <div className="flex flex-wrap items-center gap-3">
                          {company.twitter_handle && (
                            <a
                              href={`https://twitter.com/${company.twitter_handle}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center space-x-1 text-sm text-blue-600 hover:text-blue-700"
                            >
                              <Twitter className="h-4 w-4" />
                              <span>Twitter</span>
                              <ExternalLink className="h-3 w-3" />
                            </a>
                          )}
                          {company.github_org && (
                            <a
                              href={`https://github.com/${company.github_org}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center space-x-1 text-sm text-gray-600 hover:text-gray-700"
                            >
                              <Github className="h-4 w-4" />
                              <span>GitHub</span>
                              <ExternalLink className="h-3 w-3" />
                            </a>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// Monitoring Tab Content Component
function MonitoringTabContent({ companyId }: { companyId: string }) {
  const { data: monitoringMatrix, isLoading, error } = useQuery({
    queryKey: ['monitoring-matrix', companyId],
    queryFn: () => ApiService.getMonitoringMatrix(companyId),
    enabled: !!companyId,
    staleTime: 1000 * 60 * 5, // 5 minutes
  })

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/4 mb-4"></div>
          <div className="h-32 bg-gray-200 rounded"></div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-sm text-red-800">
          Failed to load monitoring data. Please try again later.
        </p>
      </div>
    )
  }

  if (!monitoringMatrix) {
    return (
      <div className="text-center py-8">
        <p className="text-sm text-gray-500">
          No monitoring data available for this company yet.
        </p>
        <p className="text-xs text-gray-400 mt-2">
          Monitoring will be set up automatically when you add this company.
        </p>
      </div>
    )
  }

  return (
    <div>
      <MonitoringSourcesCard matrix={monitoringMatrix as any} />
    </div>
  )
}

