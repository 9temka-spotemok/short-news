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
  const [selectedDate, setSelectedDate] = useState('')
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
    queryKey: ['news', selectedCategory, selectedSourceType, selectedCompanies, searchQuery, minPriority, selectedDate, currentPage],
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
  }, [selectedCategory, selectedSourceType, selectedCompanies, searchQuery, minPriority, selectedDate])

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
        return null
    }
  }

  const resetFilters = () => {
    setSearchQuery('')
    setSelectedCategory('')
    setSelectedSourceType('')
    setSelectedCompanies([])
    setMinPriority(undefined)
    setSelectedDate('')
    setCurrentPage(0)
  }

  const hasActiveFilters = searchQuery || selectedCategory || selectedSourceType || selectedCompanies.length > 0 || minPriority !== undefined || selectedDate

  // Filter news by date on client side
  const filteredNews = selectedDate && newsData
    ? newsData.items.filter((item) => {
        const itemDate = new Date(item.published_at)
        const filterDate = new Date(selectedDate)
        return itemDate.toDateString() === filterDate.toDateString()
      })
    : newsData?.items || []

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 sm:py-6 lg:py-8">
      {/* Header */}
      <div className="mb-6 sm:mb-8">
        <div className="flex flex-col lg:flex-row lg:justify-between lg:items-start gap-4 lg:gap-6">
          <div className="flex-1">
            <h1 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-gray-900 mb-2">
              AI Industry News
            </h1>
            {newsData && (
              <p className="text-xs sm:text-sm text-gray-500 mt-2">
                {selectedDate 
                  ? `${filteredNews.length} news items found for ${new Date(selectedDate).toLocaleDateString('en-US')}`
                  : `${newsData.total} news items found${newsData.has_more ? ` (showing ${newsData.items.length} of ${newsData.total})` : ''}`
                }
              </p>
            )}
          </div>
          
          {/* Stats Cards */}
          {stats && (
            <div className="grid grid-cols-3 gap-2 sm:gap-4 lg:flex lg:space-x-4">
              <div className="bg-blue-50 rounded-lg p-2 sm:p-4 text-center">
                <div className="text-lg sm:text-xl lg:text-2xl font-bold text-blue-600">{stats.total_count}</div>
                <div className="text-xs sm:text-sm text-blue-600">Total News</div>
              </div>
              <div className="bg-green-50 rounded-lg p-2 sm:p-4 text-center">
                <div className="text-lg sm:text-xl lg:text-2xl font-bold text-green-600">{stats.recent_count}</div>
                <div className="text-xs sm:text-sm text-green-600">Recent (24h)</div>
              </div>
              <div className="bg-red-50 rounded-lg p-2 sm:p-4 text-center">
                <div className="text-lg sm:text-xl lg:text-2xl font-bold text-red-600">{stats.high_priority_count}</div>
                <div className="text-xs sm:text-sm text-red-600">High Priority</div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Filters - Full functionality for authenticated users */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 sm:p-6 mb-6 sm:mb-8">
        <div className="flex items-center justify-between mb-4 sm:mb-6">
          <h3 className="text-base sm:text-lg font-semibold text-gray-900">Search & Filters</h3>
        </div>
        
        {/* Search Bar - Full Width */}
        <div className="mb-4 sm:mb-6">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search news by title, summary, or keywords..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="input pl-10 w-full text-sm sm:text-base"
            />
          </div>
        </div>

        {/* Filter Groups */}
        <div className="space-y-4 sm:space-y-6">
          {/* Content Filters */}
          <div>
            <h4 className="text-xs sm:text-sm font-medium text-gray-700 mb-2 sm:mb-3">Content Filters</h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
              {/* Category Filter */}
              <div className="relative">
                <Filter className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none z-10" />
                <select
                  value={selectedCategory}
                  onChange={(e) => setSelectedCategory(e.target.value as NewsCategory | '')}
                  className="input pl-10 appearance-none w-full text-sm sm:text-base"
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
                  className="input pl-10 appearance-none w-full text-sm sm:text-base"
                >
                  <option value="">All Sources</option>
                  {sourceTypes.map((sourceType) => (
                    <option key={sourceType.value} value={sourceType.value}>
                      {sourceType.description}
                    </option>
                  ))}
                </select>
              </div>

              {/* Company Filter */}
              <div className="sm:col-span-2 lg:col-span-1">
                <CompanyMultiSelect
                  selectedCompanies={selectedCompanies}
                  onSelectionChange={setSelectedCompanies}
                  placeholder="Select companies..."
                />
              </div>
            </div>
          </div>

          {/* Advanced Filters */}
          <div className="relative z-0">
            <h4 className="text-xs sm:text-sm font-medium text-gray-700 mb-2 sm:mb-3">Advanced Filters</h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
              {/* Priority Filter */}
              <div className="relative z-0">
                <Star className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none z-10" />
                <select
                  value={minPriority || ''}
                  onChange={(e) => setMinPriority(e.target.value ? Number(e.target.value) : undefined)}
                  className="input pl-10 appearance-none w-full text-sm sm:text-base"
                >
                  <option value="">All Priorities</option>
                  <option value="0.8">High Priority (0.8+)</option>
                  <option value="0.6">Medium+ Priority (0.6+)</option>
                  <option value="0.4">Low+ Priority (0.4+)</option>
                </select>
              </div>

              {/* Date Filter */}
              <div className="relative z-0">
                <Clock className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none z-10" />
                <input
                  type="date"
                  value={selectedDate}
                  onChange={(e) => setSelectedDate(e.target.value)}
                  className="input pl-10 w-full text-sm sm:text-base cursor-pointer"
                />
              </div>
            </div>
          </div>
        </div>

        {/* Active Filters Display */}
        {hasActiveFilters && (
          <div className="mt-4 pt-3 border-t border-gray-200">
            <div className="flex items-center gap-2">
              <span className="text-xs sm:text-sm font-medium text-gray-700">Active filters:</span>
              <div className="flex flex-wrap gap-1 sm:gap-2">
                {searchQuery && (
                  <span className="inline-flex items-center px-2 py-1 rounded-xl text-xs font-medium bg-blue-100 text-blue-800">
                    Search: "{searchQuery.length > 20 ? searchQuery.substring(0, 20) + '...' : searchQuery}"
                  </span>
                )}
                {selectedCategory && (
                  <span className="inline-flex items-center px-2 py-1 rounded-xl text-xs font-medium bg-green-100 text-green-800">
                    {categories.find(c => c.value === selectedCategory)?.description || selectedCategory}
                  </span>
                )}
                {selectedSourceType && (
                  <span className="inline-flex items-center px-2 py-1 rounded-xl text-xs font-medium bg-purple-100 text-purple-800">
                    {sourceTypes.find(s => s.value === selectedSourceType)?.description || selectedSourceType}
                  </span>
                )}
                {selectedCompanies.length > 0 && (
                  <span className="inline-flex items-center px-2 py-1 rounded-xl text-xs font-medium bg-orange-100 text-orange-800">
                    {selectedCompanies.length} companies
                  </span>
                )}
                {minPriority !== undefined && (
                  <span className="inline-flex items-center px-2 py-1 rounded-xl text-xs font-medium bg-red-100 text-red-800">
                    Priority {minPriority}+
                  </span>
                )}
                {selectedDate && (
                  <span className="inline-flex items-center px-2 py-1 rounded-xl text-xs font-medium bg-gray-100 text-gray-800">
                    {new Date(selectedDate).toLocaleDateString('en-US')}
                  </span>
                )}
              </div>
            </div>
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between m-2  gap-3 sm:gap-0">
              {hasActiveFilters && (
                <button
                  onClick={resetFilters}
                  className="btn btn-outline btn-sm w-full sm:w-auto"
                >
                  Reset All
                </button>
              )}
            </div>
          </div>
        )}
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
      {!isLoading && !error && filteredNews.length === 0 && (
        <div className="text-center py-12">
          <p className="text-gray-600 text-lg">No news found</p>
          <p className="text-gray-500 text-sm mt-2">Try changing filters or come back later</p>
          {hasActiveFilters && (
            <button
              onClick={resetFilters}
              className="mt-4 text-sm text-primary-600 hover:text-primary-700 font-medium"
            >
              Reset Filters
            </button>
          )}
        </div>
      )}

      {/* News Grid */}
      {!isLoading && filteredNews.length > 0 && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredNews.map((item) => {
              const badge = getCategoryBadge(item.category)
              
              return (
                <div key={item.id} className="card p-4 sm:p-6 hover:shadow-md transition-shadow flex flex-col h-full">
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-4 gap-3 sm:gap-4">
                    <div className="flex items-center space-x-3">
                      <span className={`badge ${badge.colorClass} text-xs`}>
                        {badge.label}
                      </span>
                      {getPriorityIcon(item.priority_level)}
                    </div>
                    <div className="flex items-center space-x-3 text-xs sm:text-sm text-gray-500">
                      {item.is_recent && (
                        <span className="bg-green-100 text-green-800 px-2 py-1 rounded-xl text-xs font-medium">
                          Recent
                        </span>
                      )}
                      <div className="flex items-center space-x-2">
                        <Clock className="h-3 w-3 text-gray-400" />
                        <span className="whitespace-nowrap">{formatDate(item.published_at)}</span>
                      </div>
                    </div>
                  </div>
                  
                  <h3 className="text-base sm:text-lg font-semibold text-gray-900 mb-4 line-clamp-2">
                    {item.title}
                  </h3>
                  
                  <p className="text-gray-600 text-xs sm:text-sm mb-4 line-clamp-3">
                    {item.summary || 'No description available'}
                  </p>
                  
                  {item.keywords && item.keywords.length > 0 && (
                    <div className="flex flex-wrap gap-2 mb-4">
                      {item.keywords.slice(0, 3).map((keyword, index) => (
                        <span
                          key={index}
                          className="bg-gray-100 text-gray-700 px-2 py-1 rounded-lg text-xs font-medium"
                        >
                          {keyword.keyword}
                        </span>
                      ))}
                    </div>
                  )}
                  
                  <div className="flex items-center justify-between mt-auto pt-2 border-t border-gray-100">
                    <span className="text-xs sm:text-sm text-gray-500 capitalize">
                      {item.source_type || 'Blog'}
                    </span>
                    <a
                      href={item.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary-600 hover:text-primary-700 text-xs sm:text-sm font-medium"
                    >
                      Read more →
                    </a>
                  </div>
                </div>
              )
            })}
          </div>

          {/* Pagination */}
          {newsData && newsData.has_more && !selectedDate && (
            <div className="flex justify-center mt-6 sm:mt-8">
              <button
                onClick={() => setCurrentPage(prev => prev + 1)}
                className="btn btn-outline btn-sm sm:btn-md w-full sm:w-auto"
                disabled={isLoading}
              >
                Load More News
              </button>
            </div>
          )}
          
          {/* Refresh Button */}
          <div className="text-center mt-3 sm:mt-4">
            <button
              onClick={() => refetch()}
              className="btn btn-ghost btn-xs sm:btn-sm"
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
