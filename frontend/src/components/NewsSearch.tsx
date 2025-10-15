import { ApiService } from '@/services/api'
import type {
    NewsCategory,
    NewsCategoryInfo,
    NewsSearchResponse,
    SearchRequest,
    SourceType,
    SourceTypeInfo
} from '@/types'
import { useQuery } from '@tanstack/react-query'
import { Clock, FileText, Filter, Search, Star, X } from 'lucide-react'
import { useEffect, useState } from 'react'

interface NewsSearchProps {
  onResults?: (results: NewsSearchResponse) => void
  onLoading?: (loading: boolean) => void
  className?: string
}

export default function NewsSearch({ 
  onResults, 
  onLoading, 
  className = '' 
}: NewsSearchProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCategory, setSelectedCategory] = useState<NewsCategory | ''>('')
  const [selectedSourceType, setSelectedSourceType] = useState<SourceType | ''>('')
  const [selectedCompanyId, setSelectedCompanyId] = useState<string>('')
  const [isExpanded, setIsExpanded] = useState(false)
  const [categories, setCategories] = useState<NewsCategoryInfo[]>([])
  const [sourceTypes, setSourceTypes] = useState<SourceTypeInfo[]>([])

  // Fetch categories and source types
  const { data: categoriesData } = useQuery({
    queryKey: ['news-categories'],
    queryFn: ApiService.getNewsCategories,
    staleTime: 1000 * 60 * 60, // 1 hour
  })

  // Search query
  const {
    data: searchResults,
    isLoading,
    error,
    refetch
  } = useQuery({
    queryKey: ['news-search', searchQuery, selectedCategory, selectedSourceType, selectedCompanyId],
    queryFn: () => {
      if (!searchQuery.trim()) return null
      
      const searchParams: SearchRequest = {
        query: searchQuery,
        category: selectedCategory || undefined,
        source_type: selectedSourceType || undefined,
        company_id: selectedCompanyId || undefined,
        limit: 20,
        offset: 0
      }
      return ApiService.searchNews(searchParams)
    },
    enabled: !!searchQuery.trim(),
    staleTime: 1000 * 60 * 2, // 2 minutes
  })

  useEffect(() => {
    if (categoriesData) {
      setCategories(categoriesData.categories)
      setSourceTypes(categoriesData.source_types)
    }
  }, [categoriesData])

  useEffect(() => {
    if (onLoading) {
      onLoading(isLoading)
    }
  }, [isLoading, onLoading])

  useEffect(() => {
    if (onResults && searchResults) {
      onResults(searchResults)
    }
  }, [searchResults, onResults])

  const handleSearch = () => {
    if (searchQuery.trim()) {
      refetch()
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch()
    }
  }

  const clearFilters = () => {
    setSelectedCategory('')
    setSelectedSourceType('')
    setSelectedCompanyId('')
    setSearchQuery('')
  }

  const hasFilters = selectedCategory || selectedSourceType || selectedCompanyId

  return (
    <div className={`bg-white rounded-lg shadow-sm border border-gray-200 p-6 ${className}`}>
      {/* Main Search */}
      <div className="flex space-x-4">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search news articles, companies, or keywords..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyPress={handleKeyPress}
            className="input pl-10 w-full"
          />
        </div>
        
        <button
          onClick={handleSearch}
          disabled={!searchQuery.trim() || isLoading}
          className="btn btn-primary"
        >
          {isLoading ? 'Searching...' : 'Search'}
        </button>
        
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className={`btn btn-outline ${hasFilters ? 'btn-warning' : ''}`}
        >
          <Filter className="h-4 w-4 mr-2" />
          Filters
          {hasFilters && (
            <span className="ml-2 bg-warning-500 text-white rounded-full px-2 py-1 text-xs">
              {[selectedCategory, selectedSourceType, selectedCompanyId].filter(Boolean).length}
            </span>
          )}
        </button>
      </div>

      {/* Advanced Filters */}
      {isExpanded && (
        <div className="mt-6 pt-6 border-t border-gray-200">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Category Filter */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Category
              </label>
              <select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value as NewsCategory | '')}
                className="input w-full"
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
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Source Type
              </label>
              <select
                value={selectedSourceType}
                onChange={(e) => setSelectedSourceType(e.target.value as SourceType | '')}
                className="input w-full"
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
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Company
              </label>
              <input
                type="text"
                placeholder="Company name or ID..."
                value={selectedCompanyId}
                onChange={(e) => setSelectedCompanyId(e.target.value)}
                className="input w-full"
              />
            </div>
          </div>

          {/* Filter Actions */}
          <div className="flex justify-between items-center mt-4">
            <div className="text-sm text-gray-500">
              {hasFilters && (
                <span>Filters applied: {[selectedCategory, selectedSourceType, selectedCompanyId].filter(Boolean).join(', ')}</span>
              )}
            </div>
            
            <div className="flex space-x-2">
              {hasFilters && (
                <button
                  onClick={clearFilters}
                  className="btn btn-ghost btn-sm text-red-600 hover:bg-red-50"
                >
                  <X className="h-4 w-4 mr-1" />
                  Clear Filters
                </button>
              )}
              
              <button
                onClick={handleSearch}
                disabled={!searchQuery.trim() || isLoading}
                className="btn btn-primary btn-sm"
              >
                Search with Filters
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Search Results Summary */}
      {searchResults && (
        <div className="mt-6 pt-6 border-t border-gray-200">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">
              Search Results
            </h3>
            <div className="text-sm text-gray-500">
              {searchResults.total} results found
              {searchResults.has_more && ' (showing first 20)'}
            </div>
          </div>

          {/* Quick Stats */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-blue-50 rounded-lg p-3">
              <div className="flex items-center">
                <FileText className="h-4 w-4 text-blue-600 mr-2" />
                <span className="text-sm font-medium text-blue-600">
                  {searchResults.total} Articles
                </span>
              </div>
            </div>
            
            <div className="bg-green-50 rounded-lg p-3">
              <div className="flex items-center">
                <Clock className="h-4 w-4 text-green-600 mr-2" />
                <span className="text-sm font-medium text-green-600">
                  Recent: {searchResults.items.filter(item => item.is_recent).length}
                </span>
              </div>
            </div>
            
            <div className="bg-red-50 rounded-lg p-3">
              <div className="flex items-center">
                <Star className="h-4 w-4 text-red-600 mr-2" />
                <span className="text-sm font-medium text-red-600">
                  High Priority: {searchResults.items.filter(item => item.priority_level === 'High').length}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="mt-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          Failed to search news. Please try again.
        </div>
      )}
    </div>
  )
}
