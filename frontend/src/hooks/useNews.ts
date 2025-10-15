import { ApiService } from '@/services/api'
import type {
    NewsFilter,
    NewsItem,
    SearchRequest
} from '@/types'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useCallback, useState } from 'react'

// Hook for fetching news with filters
export function useNews(filters: NewsFilter = {}) {
  return useQuery({
    queryKey: ['news', filters],
    queryFn: () => ApiService.getNews(filters),
    staleTime: 1000 * 60 * 2, // 2 minutes
    enabled: true,
  })
}

// Hook for fetching a single news item
export function useNewsItem(id: string) {
  return useQuery({
    queryKey: ['news-item', id],
    queryFn: () => ApiService.getNewsItem(id),
    enabled: !!id,
    staleTime: 1000 * 60 * 5, // 5 minutes
  })
}

// Hook for searching news
export function useNewsSearch(searchParams: SearchRequest) {
  return useQuery({
    queryKey: ['news-search', searchParams],
    queryFn: () => ApiService.searchNews(searchParams),
    enabled: !!searchParams.query?.trim(),
    staleTime: 1000 * 60 * 2, // 2 minutes
  })
}

// Hook for news statistics
export function useNewsStats() {
  return useQuery({
    queryKey: ['news-stats'],
    queryFn: ApiService.getNewsStats,
    staleTime: 1000 * 60 * 5, // 5 minutes
  })
}

// Hook for news categories and source types
export function useNewsCategories() {
  return useQuery({
    queryKey: ['news-categories'],
    queryFn: ApiService.getNewsCategories,
    staleTime: 1000 * 60 * 60, // 1 hour
  })
}

// Hook for marking news as read
export function useMarkNewsRead() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (newsId: string) => ApiService.markNewsRead(newsId),
    onSuccess: (_, newsId) => {
      // Update the news item in cache to reflect it's been read
      queryClient.setQueryData(['news-item', newsId], (oldData: NewsItem | undefined) => {
        if (oldData) {
          return {
            ...oldData,
            // Add read status if the API returns it
            activities: [
              ...(oldData.activities || []),
              {
                id: `temp-${Date.now()}`,
                user_id: 'current-user', // This should come from auth context
                news_id: newsId,
                action: 'marked_read',
                created_at: new Date().toISOString(),
              }
            ]
          }
        }
        return oldData
      })
      
      // Invalidate news list to refresh any read status indicators
      queryClient.invalidateQueries({ queryKey: ['news'] })
    },
    onError: (error) => {
      console.error('Failed to mark news as read:', error)
    }
  })
}

// Hook for favoriting news
export function useFavoriteNews() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (newsId: string) => ApiService.favoriteNews(newsId),
    onSuccess: (_, newsId) => {
      // Update the news item in cache to reflect it's been favorited
      queryClient.setQueryData(['news-item', newsId], (oldData: NewsItem | undefined) => {
        if (oldData) {
          return {
            ...oldData,
            activities: [
              ...(oldData.activities || []),
              {
                id: `temp-${Date.now()}`,
                user_id: 'current-user', // This should come from auth context
                news_id: newsId,
                action: 'favorited',
                created_at: new Date().toISOString(),
              }
            ]
          }
        }
        return oldData
      })
      
      // Invalidate news list to refresh any favorite status indicators
      queryClient.invalidateQueries({ queryKey: ['news'] })
    },
    onError: (error) => {
      console.error('Failed to favorite news:', error)
    }
  })
}

// Hook for paginated news with state management
export function usePaginatedNews(initialFilters: NewsFilter = {}) {
  const [filters, setFilters] = useState<NewsFilter>(initialFilters)
  const [currentPage, setCurrentPage] = useState(0)
  const limit = 20

  const query = useQuery({
    queryKey: ['news', filters, currentPage],
    queryFn: () => ApiService.getNews({
      ...filters,
      limit,
      offset: currentPage * limit,
    }),
    staleTime: 1000 * 60 * 2,
  })

  const updateFilters = useCallback((newFilters: Partial<NewsFilter>) => {
    setFilters(prev => ({ ...prev, ...newFilters }))
    setCurrentPage(0) // Reset to first page when filters change
  }, [])

  const nextPage = useCallback(() => {
    if (query.data?.has_more) {
      setCurrentPage(prev => prev + 1)
    }
  }, [query.data?.has_more])

  const prevPage = useCallback(() => {
    if (currentPage > 0) {
      setCurrentPage(prev => prev - 1)
    }
  }, [currentPage])

  const resetFilters = useCallback(() => {
    setFilters(initialFilters)
    setCurrentPage(0)
  }, [initialFilters])

  return {
    ...query,
    filters,
    currentPage,
    updateFilters,
    nextPage,
    prevPage,
    resetFilters,
    hasNextPage: query.data?.has_more || false,
    hasPrevPage: currentPage > 0,
    totalPages: query.data ? Math.ceil(query.data.total / limit) : 0,
  }
}

// Hook for news search with state management
export function useNewsSearchState() {
  const [searchParams, setSearchParams] = useState<SearchRequest>({
    query: '',
    limit: 20,
    offset: 0,
  })

  const query = useNewsSearch(searchParams)

  const search = useCallback((query: string, additionalParams?: Partial<SearchRequest>) => {
    setSearchParams(prev => ({
      ...prev,
      query,
      offset: 0, // Reset offset when searching
      ...additionalParams,
    }))
  }, [])

  const updateSearchParams = useCallback((params: Partial<SearchRequest>) => {
    setSearchParams(prev => ({ ...prev, ...params }))
  }, [])

  const clearSearch = useCallback(() => {
    setSearchParams({
      query: '',
      limit: 20,
      offset: 0,
    })
  }, [])

  const loadMore = useCallback(() => {
    if (query.data?.has_more) {
      setSearchParams(prev => ({
        ...prev,
        offset: (prev.offset || 0) + (prev.limit || 20),
      }))
    }
  }, [query.data?.has_more])

  return {
    ...query,
    searchParams,
    search,
    updateSearchParams,
    clearSearch,
    loadMore,
    hasMore: query.data?.has_more || false,
  }
}

// Hook for news analytics and insights
export function useNewsAnalytics() {
  const statsQuery = useNewsStats()
  const categoriesQuery = useNewsCategories()

  const getCategoryTrends = useCallback(() => {
    if (!statsQuery.data || !categoriesQuery.data) return []
    
    return Object.entries(statsQuery.data.category_counts)
      .map(([category, count]) => {
        const categoryInfo = categoriesQuery.data.categories.find(c => c.value === category)
        return {
          category: categoryInfo?.description || category,
          count,
          percentage: (count / statsQuery.data.total_count) * 100,
        }
      })
      .sort((a, b) => b.count - a.count)
  }, [statsQuery.data, categoriesQuery.data])

  const getSourceTrends = useCallback(() => {
    if (!statsQuery.data || !categoriesQuery.data) return []
    
    return Object.entries(statsQuery.data.source_type_counts)
      .map(([sourceType, count]) => {
        const sourceInfo = categoriesQuery.data.source_types.find(s => s.value === sourceType)
        return {
          sourceType: sourceInfo?.description || sourceType,
          count,
          percentage: (count / statsQuery.data.total_count) * 100,
        }
      })
      .sort((a, b) => b.count - a.count)
  }, [statsQuery.data, categoriesQuery.data])

  return {
    stats: statsQuery.data,
    categories: categoriesQuery.data,
    isLoading: statsQuery.isLoading || categoriesQuery.isLoading,
    error: statsQuery.error || categoriesQuery.error,
    categoryTrends: getCategoryTrends(),
    sourceTrends: getSourceTrends(),
    refetch: () => {
      statsQuery.refetch()
      categoriesQuery.refetch()
    }
  }
}
