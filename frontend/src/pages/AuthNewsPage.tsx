import CompanyMultiSelect from '@/components/CompanyMultiSelect'
import { ApiService } from '@/services/api'
import type {
    NewsCategory,
    NewsCategoryInfo,
    NewsFilter,
    NewsStats,
    SourceType,
    SourceTypeInfo
} from '@/types'
import { useQuery } from '@tanstack/react-query'
import { formatDistance } from 'date-fns'
import { enUS } from 'date-fns/locale'
import { Clock, Filter, Search, Star, TrendingUp } from 'lucide-react'
import { useEffect, useState } from 'react'

export default function AuthNewsPage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCategory, setSelectedCategory] = useState<NewsCategory | ''>('')
  const [selectedSourceType, setSelectedSourceType] = useState<SourceType | ''>('')
  const [selectedCompanies, setSelectedCompanies] = useState<string[]>([])
  const [minPriority, setMinPriority] = useState<number | undefined>(undefined)
  const [currentPage, setCurrentPage] = useState(0)
  const [categories, setCategories] = useState<NewsCategoryInfo[]>([])
  const [sourceTypes, setSourceTypes] = useState<SourceTypeInfo[]>([])
  const [stats, setStats] = useState<NewsStats | null>(null)

  const limit = 20

  // Fetch categories and source types
  const { data: categoriesData } = useQuery({
    queryKey: ['news-categories'],
    queryFn: ApiService.getNewsCategories,
    staleTime: 1000 * 60 * 60, // 1 hour
  })

  // Fetch news statistics
  const { data: statsData } = useQuery({
    queryKey: ['news-stats'],
    queryFn: ApiService.getNewsStats,
    staleTime: 1000 * 60 * 5, // 5 minutes
  })

  // Fetch news with React Query
  const {
    data: newsData,
    isLoading,
    error,
    refetch
  } = useQuery({
    queryKey: ['news', selectedCategory, selectedSourceType, selectedCompanies, searchQuery, minPriority, currentPage],
    queryFn: () => {
      const filters: NewsFilter = {
        category: selectedCategory || undefined,
        source_type: selectedSourceType || undefined,
        company_ids: selectedCompanies.length > 0 ? selectedCompanies : undefined,
        search_query: searchQuery || undefined,
        min_priority: minPriority,
        limit,
        offset: currentPage * limit,
      }
      return ApiService.getNews(filters)
    },
    staleTime: 1000 * 60 * 2, // 2 minutes
  })

  useEffect(() => {
    if (categoriesData) {
      setCategories(categoriesData.categories)
      setSourceTypes(categoriesData.source_types)
    }
  }, [categoriesData])

  useEffect(() => {
    if (statsData) {
      setStats(statsData)
    }
  }, [statsData])

  // Reset page when filters change
  useEffect(() => {
    setCurrentPage(0)
  }, [selectedCategory, selectedSourceType, selectedCompanies, searchQuery, minPriority])

  const formatDate = (dateString: string) => {
    try {
      const date = new Date(dateString)
      return formatDistance(date, new Date(), { addSuffix: true, locale: enUS })
    } catch {
      return 'Recently'
    }
  }

  const getCategoryBadge = (category: NewsCategory | null) => {
    if (!category) return { label: 'Uncategorized', colorClass: 'badge-secondary' }
    
    const categoryInfo = categories.find(c => c.value === category)
    const label = categoryInfo?.description || category.replace('_', ' ')
    
    const colorClasses: Record<string, string> = {
      'product_update': 'badge-primary',
      'pricing_change': 'badge-warning',
      'strategic_announcement': 'badge-success',
      'technical_update': 'badge-info',
      'funding_news': 'badge-accent',
      'security_update': 'badge-error',
      'research_paper': 'badge-secondary',
      'community_event': 'badge-secondary',
      'partnership': 'badge-secondary',
      'acquisition': 'badge-secondary',
      'integration': 'badge-secondary',
      'api_update': 'badge-secondary',
      'model_release': 'badge-secondary',
      'performance_improvement': 'badge-secondary',
      'feature_deprecation': 'badge-secondary',
    }
    
    const colorClass = colorClasses[category] || 'badge-secondary'
    return { label, colorClass }
  }

  const getPriorityIcon = (priorityLevel: string) => {
    switch (priorityLevel) {
      case 'High':
        return <Star className="h-4 w-4 text-red-500" />
      case 'Medium':
        return <TrendingUp className="h-4 w-4 text-yellow-500" />
      default:
        return <Clock className="h-4 w-4 text-gray-400" />
    }
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex justify-between items-start">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">
              AI Industry News
            </h1>
            <p className="text-gray-600">
              Latest news from the world of artificial intelligence and machine learning
            </p>
            {newsData && (
              <p className="text-sm text-gray-500 mt-2">
                {newsData.total} news items found
                {newsData.has_more && ` (showing ${newsData.items.length} of ${newsData.total})`}
              </p>
            )}
          </div>
          
          {/* Stats Cards */}
          {stats && (
            <div className="flex space-x-4">
              <div className="bg-blue-50 rounded-lg p-4 text-center min-w-[100px]">
                <div className="text-2xl font-bold text-blue-600">{stats.total_count}</div>
                <div className="text-sm text-blue-600">Total News</div>
              </div>
              <div className="bg-green-50 rounded-lg p-4 text-center min-w-[100px]">
                <div className="text-2xl font-bold text-green-600">{stats.recent_count}</div>
                <div className="text-sm text-green-600">Recent (24h)</div>
              </div>
              <div className="bg-red-50 rounded-lg p-4 text-center min-w-[100px]">
                <div className="text-2xl font-bold text-red-600">{stats.high_priority_count}</div>
                <div className="text-sm text-red-600">High Priority</div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Filters - Full functionality for authenticated users */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-8">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search news..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="input pl-10 w-full"
            />
          </div>

          {/* Category Filter */}
          <div className="relative">
            <Filter className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none z-10" />
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value as NewsCategory | '')}
              className="input pl-10 appearance-none w-full"
            >
              <option value="">All Categories</option>
              {categories.map((category) => (
                <option key={category.value} value={category.value}>
                  {category.description}
                </option>
              ))}
            </select>
          </div>

          {/* Source Type Filter */}
          <div className="relative">
            <Filter className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none z-10" />
            <select
              value={selectedSourceType}
              onChange={(e) => setSelectedSourceType(e.target.value as SourceType | '')}
              className="input pl-10 appearance-none w-full"
            >
              <option value="">All Sources</option>
              {sourceTypes.map((sourceType) => (
                <option key={sourceType.value} value={sourceType.value}>
                  {sourceType.description}
                </option>
              ))}
            </select>
          </div>

          {/* Priority Filter - Only for authenticated users */}
          <div className="relative">
            <Star className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none z-10" />
            <select
              value={minPriority || ''}
              onChange={(e) => setMinPriority(e.target.value ? Number(e.target.value) : undefined)}
              className="input pl-10 appearance-none w-full"
            >
              <option value="">All Priorities</option>
              <option value="0.8">High Priority (0.8+)</option>
              <option value="0.6">Medium+ Priority (0.6+)</option>
              <option value="0.4">Low+ Priority (0.4+)</option>
            </select>
          </div>

          {/* Company Filter */}
          <CompanyMultiSelect
            selectedCompanies={selectedCompanies}
            onSelectionChange={setSelectedCompanies}
            placeholder="Select companies..."
          />
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-6">
          Failed to load news. Please try refreshing the page.
        </div>
      )}

      {/* Loading State */}
      {isLoading && (
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
          <p className="mt-4 text-gray-600">Loading news...</p>
        </div>
      )}

      {/* Empty State */}
      {!isLoading && !error && newsData && newsData.items.length === 0 && (
        <div className="text-center py-12">
          <p className="text-gray-600 text-lg">No news found</p>
          <p className="text-gray-500 text-sm mt-2">Try changing filters or come back later</p>
        </div>
      )}

      {/* News Grid */}
      {!isLoading && newsData && newsData.items.length > 0 && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {newsData.items.map((item) => {
              const badge = getCategoryBadge(item.category)
              
              return (
                <div key={item.id} className="card p-6 hover:shadow-md transition-shadow">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center space-x-2">
                      <span className={`badge ${badge.colorClass}`}>
                        {badge.label}
                      </span>
                      {getPriorityIcon(item.priority_level)}
                    </div>
                    <div className="flex items-center space-x-2 text-sm text-gray-500">
                      {item.is_recent && (
                        <span className="bg-green-100 text-green-800 px-2 py-1 rounded-full text-xs">
                          Recent
                        </span>
                      )}
                      <span>{formatDate(item.published_at)}</span>
                    </div>
                  </div>
                  
                  <h3 className="text-lg font-semibold text-gray-900 mb-2 line-clamp-2">
                    {item.title}
                  </h3>
                  
                  <p className="text-gray-600 text-sm mb-4 line-clamp-3">
                    {item.summary || 'No description available'}
                  </p>
                  
                  {item.company && (
                    <div className="flex items-center mb-3">
                      <div className="w-6 h-6 bg-gray-200 rounded-full mr-2"></div>
                      <span className="text-sm text-gray-600">{item.company.name}</span>
                    </div>
                  )}
                  
                  {item.keywords && item.keywords.length > 0 && (
                    <div className="flex flex-wrap gap-1 mb-3">
                      {item.keywords.slice(0, 3).map((keyword, index) => (
                        <span
                          key={index}
                          className="bg-gray-100 text-gray-700 px-2 py-1 rounded text-xs"
                        >
                          {keyword.keyword}
                        </span>
                      ))}
                    </div>
                  )}
                  
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-500 capitalize">
                      {item.source_type || 'Blog'}
                    </span>
                    <a
                      href={item.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary-600 hover:text-primary-700 text-sm font-medium"
                    >
                      Read more →
                    </a>
                  </div>
                </div>
              )
            })}
          </div>

          {/* Pagination */}
          {newsData.has_more && (
            <div className="flex justify-center mt-8">
              <button
                onClick={() => setCurrentPage(prev => prev + 1)}
                className="btn btn-outline btn-md"
                disabled={isLoading}
              >
                Load More News
              </button>
            </div>
          )}
          
          {/* Refresh Button */}
          <div className="text-center mt-4">
            <button
              onClick={() => refetch()}
              className="btn btn-ghost btn-sm"
              disabled={isLoading}
            >
              Refresh News
            </button>
          </div>
        </>
      )}
    </div>
  )
}
