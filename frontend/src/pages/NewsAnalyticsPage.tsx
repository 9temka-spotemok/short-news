import NewsStats, { CategoryBreakdown, SourceBreakdown } from '@/components/NewsStats'
import { useNews, useNewsAnalytics } from '@/hooks/useNews'
import type { NewsCategory, SourceType } from '@/types'
import { Activity, BarChart3, Calendar, PieChart, TrendingUp } from 'lucide-react'
import { useState } from 'react'

export default function NewsAnalyticsPage() {
  const [selectedCategory, setSelectedCategory] = useState<NewsCategory | ''>('')
  const [selectedSourceType, setSelectedSourceType] = useState<SourceType | ''>('')
  const [timeRange, setTimeRange] = useState<'7d' | '30d' | '90d'>('30d')

  const {
    stats,
    categories,
    isLoading: analyticsLoading,
    error: analyticsError,
    categoryTrends,
    sourceTrends,
    refetch
  } = useNewsAnalytics()

  // Get recent news for selected filters
  const { data: recentNews, isLoading: newsLoading } = useNews({
    category: selectedCategory || undefined,
    source_type: selectedSourceType || undefined,
    limit: 10,
    offset: 0,
  })

  if (analyticsLoading) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
          <p className="mt-4 text-gray-600">Loading analytics...</p>
        </div>
      </div>
    )
  }

  if (analyticsError) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-6">
          Failed to load analytics. Please try again.
        </div>
        <button
          onClick={() => refetch()}
          className="btn btn-primary"
        >
          Retry
        </button>
      </div>
    )
  }

  if (!stats) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="text-center py-12">
          <p className="text-gray-600 text-lg">No analytics data available</p>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex justify-between items-start">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">
              News Analytics
            </h1>
            <p className="text-gray-600">
              Insights and trends from the AI industry news
            </p>
          </div>
          
          {/* Time Range Selector */}
          {/* <div className="flex space-x-2">
            {(['7d', '30d', '90d'] as const).map((range) => (
              <button
                key={range}
                onClick={() => setTimeRange(range)}
                className={`btn btn-sm ${
                  timeRange === range ? 'btn-primary' : 'btn-outline'
                }`}
              >
                {range === '7d' ? '7 Days' : range === '30d' ? '30 Days' : '90 Days'}
              </button>
            ))}
          </div> */} 
          {/* //TODO исправить временной диапазон */}
        </div>
      </div>

      {/* Main Stats */}
      <NewsStats stats={stats} className="mb-8" />

      {/* Filters */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Category Filter */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
            <PieChart className="h-5 w-5 mr-2 text-primary-600" />
            Filter by Category
          </h3>
          
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value as NewsCategory | '')}
            className="input w-full"
          >
            <option value="">All Categories</option>
            {categories?.categories.map((category) => (
              <option key={category.value} value={category.value}>
                {category.description}
              </option>
            ))}
          </select>
        </div>

        {/* Source Type Filter */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
            <BarChart3 className="h-5 w-5 mr-2 text-primary-600" />
            Filter by Source
          </h3>
          
          <select
            value={selectedSourceType}
            onChange={(e) => setSelectedSourceType(e.target.value as SourceType | '')}
            className="input w-full"
          >
            <option value="">All Sources</option>
            {categories?.source_types.map((sourceType) => (
              <option key={sourceType.value} value={sourceType.value}>
                {sourceType.description}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Analytics Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Category Breakdown */}
        <CategoryBreakdown 
          categoryCounts={stats.category_counts} 
          className="h-full"
        />

        {/* Source Breakdown */}
        <SourceBreakdown 
          sourceTypeCounts={stats.source_type_counts} 
          className="h-full"
        />
      </div>

      {/* Top Trends */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Top Categories */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
            <TrendingUp className="h-5 w-5 mr-2 text-green-600" />
            Top Categories
          </h3>
          
          <div className="space-y-3">
            {categoryTrends.slice(0, 5).map((trend, index) => (
              <div key={trend.category} className="flex items-center justify-between">
                <div className="flex items-center">
                  <span className="text-sm font-medium text-gray-500 w-6">
                    #{index + 1}
                  </span>
                  <span className="text-sm font-medium text-gray-900 ml-2">
                    {trend.category}
                  </span>
                </div>
                <div className="flex items-center space-x-2">
                  <span className="text-sm text-gray-500">
                    {trend.count}
                  </span>
                  <span className="text-xs text-gray-400">
                    ({trend.percentage.toFixed(1)}%)
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Top Sources */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
            <Activity className="h-5 w-5 mr-2 text-blue-600" />
            Top Sources
          </h3>
          
          <div className="space-y-3">
            {sourceTrends.slice(0, 5).map((trend, index) => (
              <div key={trend.sourceType} className="flex items-center justify-between">
                <div className="flex items-center">
                  <span className="text-sm font-medium text-gray-500 w-6">
                    #{index + 1}
                  </span>
                  <span className="text-sm font-medium text-gray-900 ml-2">
                    {trend.sourceType}
                  </span>
                </div>
                <div className="flex items-center space-x-2">
                  <span className="text-sm text-gray-500">
                    {trend.count}
                  </span>
                  <span className="text-xs text-gray-400">
                    ({trend.percentage.toFixed(1)}%)
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Recent News for Selected Filters */}
      {(selectedCategory || selectedSourceType) && (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
            <Calendar className="h-5 w-5 mr-2 text-primary-600" />
            Recent News
            {selectedCategory && (
              <span className="ml-2 badge badge-primary">
                {categories?.categories.find(c => c.value === selectedCategory)?.description}
              </span>
            )}
            {selectedSourceType && (
              <span className="ml-2 badge badge-secondary">
                {categories?.source_types.find(s => s.value === selectedSourceType)?.description}
              </span>
            )}
          </h3>
          
          {newsLoading ? (
            <div className="text-center py-8">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
              <p className="mt-2 text-gray-600">Loading recent news...</p>
            </div>
          ) : recentNews && recentNews.items.length > 0 ? (
            <div className="space-y-3">
              {recentNews.items.map((item) => (
                <div key={item.id} className="flex items-start space-x-3 p-3 bg-gray-50 rounded-lg">
                  <div className="flex-1">
                    <h4 className="text-sm font-medium text-gray-900 line-clamp-2">
                      {item.title}
                    </h4>
                    <div className="flex items-center space-x-4 mt-1 text-xs text-gray-500">
                      <span className="capitalize">{item.source_type}</span>
                      <span>{new Date(item.published_at).toLocaleDateString()}</span>
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
                    className="text-primary-600 hover:text-primary-700 text-sm font-medium"
                  >
                    Read →
                  </a>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <p className="text-gray-600">No recent news found for selected filters</p>
            </div>
          )}
        </div>
      )}

      {/* Refresh Button */}
      <div className="text-center mt-8">
        <button
          onClick={() => refetch()}
          className="btn btn-outline"
        >
          Refresh Analytics
        </button>
      </div>
    </div>
  )
}
