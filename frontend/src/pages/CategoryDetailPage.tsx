import { ApiService } from '@/services/api'
import type { NewsItem, SourceType } from '@/types'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, BarChart3, Calendar, ExternalLink, Filter } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'

interface CategoryStatistics {
  top_companies: Array<{ name: string; count: number }>
  source_distribution: Record<string, number>
  total_in_category: number
}

interface CategoryData {
  category: string
  category_description: string
  items: NewsItem[]
  total: number
  limit: number
  offset: number
  has_more: boolean
  statistics: CategoryStatistics
  filters: {
    company_id?: string
    source_type?: string
  }
}

export default function CategoryDetailPage() {
  const { categoryName } = useParams<{ categoryName: string }>()
  const navigate = useNavigate()
  
  // Check if we came from tracked-only mode
  const urlParams = new URLSearchParams(window.location.search)
  const isTrackedMode = urlParams.get('tracked') === 'true'
  
  const [categoryData, setCategoryData] = useState<CategoryData | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
//   const [setSelectedCompanyId] = useState<string>('')
  const [selectedCompanyId] = useState<string>('')
  const [selectedSourceType, setSelectedSourceType] = useState<SourceType | ''>('')
  const [currentPage, setCurrentPage] = useState(0)
  const [showTrackedOnly, setShowTrackedOnly] = useState(isTrackedMode)
  
  const limit = 20

  // Load user preferences for tracked companies
  const { data: userPreferences } = useQuery({
    queryKey: ['user-preferences'],
    queryFn: ApiService.getUserPreferences,
    staleTime: 1000 * 60 * 5, // 5 minutes
  })

  const loadCategoryData = async () => {
    if (!categoryName) return
    
    setIsLoading(true)
    setError(null)
    
    try {
      const filters: any = {
        company_id: selectedCompanyId || undefined,
        source_type: selectedSourceType || undefined,
        limit,
        offset: currentPage * limit
      }
      
      // Если пользователь отслеживает компании и включен режим "tracked only", добавить их в фильтр
      if (showTrackedOnly && userPreferences?.subscribed_companies?.length) {
        filters.company_ids = userPreferences.subscribed_companies.join(',')
      }
      
      const data = await ApiService.getNewsByCategory(categoryName, filters)
      setCategoryData(data)
    } catch (err) {
      setError('Failed to load category data')
      console.error('Error loading category data:', err)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadCategoryData()
  }, [categoryName, selectedCompanyId, selectedSourceType, currentPage, showTrackedOnly, userPreferences?.subscribed_companies])

  const handleFilterChange = () => {
    setCurrentPage(0) // Reset to first page when filters change
  }

//   const handleCompanyFilterChange = (companyId: string) => {
//     setSelectedCompanyId(companyId)
//     handleFilterChange()
//   }

  const handleSourceTypeFilterChange = (sourceType: SourceType | '') => {
    setSelectedSourceType(sourceType)
    handleFilterChange()
  }

  const handlePageChange = (newPage: number) => {
    setCurrentPage(newPage)
  }

  if (isLoading && !categoryData) {
    return (
      <div className="text-center py-12">
        <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
        <p className="mt-4 text-gray-600">Loading category data...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div>
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-6">
          {error}
        </div>
        <button
          onClick={() => navigate('/dashboard')}
          className="btn btn-primary"
        >
          Back to Dashboard
        </button>
      </div>
    )
  }

  if (!categoryData) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-600 text-lg">Category not found</p>
        <button
          onClick={() => navigate('/dashboard')}
          className="btn btn-primary mt-4"
        >
          Back to Dashboard
        </button>
      </div>
    )
  }

  const { category, category_description, items, total, statistics, has_more } = categoryData

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center mb-4">
          <button
            onClick={() => navigate('/dashboard')}
            className="flex items-center text-primary-600 hover:text-primary-700 mr-4"
          >
            <ArrowLeft className="h-5 w-5 mr-2" />
            Back to Dashboard
          </button>
        </div>
        
        <div className="flex justify-between items-start">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2 capitalize">
              {category.replace(/_/g, ' ')}
            </h1>
            <p className="text-gray-600">
              {category_description}
            </p>
            <p className="text-sm text-gray-500 mt-2">
              {total} news items in this category
              {showTrackedOnly && userPreferences?.subscribed_companies?.length && (
                <span className="ml-2 text-primary-600">
                  (from {userPreferences.subscribed_companies.length} tracked companies)
                </span>
              )}
            </p>
          </div>
          
          {/* Tracked Companies Toggle */}
          {userPreferences?.subscribed_companies?.length && (
            <div className="flex items-center space-x-2">
              <span className="text-sm text-gray-600">All Companies</span>
              <button
                onClick={() => setShowTrackedOnly(!showTrackedOnly)}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  showTrackedOnly ? 'bg-primary-600' : 'bg-gray-200'
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    showTrackedOnly ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
              <span className="text-sm text-gray-600">Tracked Only</span>
            </div>
          )}
        </div>
      </div>

      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        {/* Total Count */}
        <div className="card p-6 border border-gray-200">
          <div className="flex items-center">
            <div className="w-12 h-12 bg-primary-100 rounded-lg flex items-center justify-center">
              <BarChart3 className="h-6 w-6 text-primary-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Total News</p>
              <p className="text-2xl font-bold text-gray-900">{total}</p>
            </div>
          </div>
        </div>

        {/* Selected Companies */}
        {/* <div className="card p-6 border border-gray-200">
          <div className="flex items-center mb-3">
            <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center mr-3">
              <Building2 className="h-5 w-5 text-blue-600" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900">Selected Companies</h3>
          </div>
          <div className="space-y-2">
            {statistics.top_companies && statistics.top_companies.length > 0 ? (
              statistics.top_companies.slice(0, 3).map((company) => (
                <div key={company.name} className="flex justify-between items-center">
                  <span className="text-sm text-gray-900 truncate">{company.name}</span>
                  <span className="text-sm text-gray-500">{company.count}</span>
                </div>
              ))
            ) : (
              <p className="text-sm text-gray-500">No companies data</p>
            )}
          </div>
        </div> */}

        {/* Source Distribution */}
        {/* <div className="card p-6 border border-gray-200">
          <div className="flex items-center mb-3">
            <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center mr-3">
              <TrendingUp className="h-5 w-5 text-green-600" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900">Top Sources</h3>
          </div>
          <div className="space-y-2">
            {statistics.source_distribution && Object.keys(statistics.source_distribution).length > 0 ? (
              Object.entries(statistics.source_distribution)
                .sort(([,a], [,b]) => b - a)
                .slice(0, 3)
                .map(([source, count]) => (
                  <div key={source} className="flex justify-between items-center">
                    <span className="text-sm text-gray-900 capitalize">{source}</span>
                    <span className="text-sm text-gray-500">{count}</span>
                  </div>
                ))
            ) : (
              <p className="text-sm text-gray-500">No sources data</p>
            )}
          </div>
        </div> */}
      </div>

      {/* Filters */}
      <div className="card p-6 mb-8 border border-gray-200">
        <div className="flex items-center mb-4">
          <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center mr-3">
            <Filter className="h-5 w-5 text-purple-600" />
          </div>
          <h3 className="text-lg font-semibold text-gray-900">Filters</h3>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Company Filter */}
          {/* <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Filter by Company
            </label>
            <select
              value={selectedCompanyId}
              onChange={(e) => handleCompanyFilterChange(e.target.value)}
              className="input w-full"
            >
              <option value="">All Companies</option>
              {statistics.top_companies && statistics.top_companies.map((company) => (
                <option key={company.name} value={company.name}>
                  {company.name} ({company.count})
                </option>
              ))}
            </select>
          </div> */}

          {/* Source Type Filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Filter by Source Type
            </label>
            <select
              value={selectedSourceType}
              onChange={(e) => handleSourceTypeFilterChange(e.target.value as SourceType | '')}
              className="input w-full"
            >
              <option value="">All Sources</option>
              {statistics.source_distribution && Object.entries(statistics.source_distribution).map(([source, count]) => (
                <option key={source} value={source}>
                  {source.charAt(0).toUpperCase() + source.slice(1)} ({count})
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* News Items */}
      <div className="card p-6 border border-gray-200">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-semibold text-gray-900">News Items</h3>
          {isLoading && (
            <div className="inline-block animate-spin rounded-full h-5 w-5 border-b-2 border-primary-600"></div>
          )}
        </div>

        {items.length > 0 ? (
          <div className="space-y-4">
            {items.map((item) => (
              <div key={item.id} className="border-b border-gray-200 pb-4 last:border-b-0">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <h4 className="text-lg font-medium text-gray-900 mb-2 line-clamp-2">
                      {item.title}
                    </h4>
                    {item.summary && (
                      <p className="text-gray-600 mb-3 line-clamp-2">
                        {item.summary}
                      </p>
                    )}
                    <div className="flex items-center space-x-4 text-sm text-gray-500">
                      <div className="flex items-center">
                        <Calendar className="h-4 w-4 mr-1" />
                        {new Date(item.published_at).toLocaleDateString()}
                      </div>
                      <span className="capitalize">{item.source_type}</span>
                      {item.company && (
                        <span>{item.company.name}</span>
                      )}
                      {item.priority_level !== 'Low' && (
                        <span className={`px-2 py-1 rounded-full text-xs ${
                          item.priority_level === 'High' 
                            ? 'bg-red-100 text-red-800' 
                            : 'bg-yellow-100 text-yellow-800'
                        }`}>
                          {item.priority_level} Priority
                        </span>
                      )}
                    </div>
                  </div>
                  <a
                    href={item.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="ml-4 flex items-center text-primary-600 hover:text-primary-700 text-sm font-medium"
                  >
                    <ExternalLink className="h-4 w-4 mr-1" />
                    Read
                  </a>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8">
            <p className="text-gray-600">No news items found for the selected filters</p>
          </div>
        )}

        {/* Pagination */}
        {total > limit && (
          <div className="mt-8 flex justify-center">
            <div className="flex space-x-2">
              <button
                onClick={() => handlePageChange(currentPage - 1)}
                disabled={currentPage === 0}
                className="btn btn-outline btn-sm disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Previous
              </button>
              
              <span className="flex items-center px-4 py-2 text-sm text-gray-700">
                Page {currentPage + 1} of {Math.ceil(total / limit)}
              </span>
              
              <button
                onClick={() => handlePageChange(currentPage + 1)}
                disabled={!has_more}
                className="btn btn-outline btn-sm disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
