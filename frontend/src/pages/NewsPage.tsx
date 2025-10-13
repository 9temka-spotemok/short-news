import CompanyMultiSelect from '@/components/CompanyMultiSelect'
import api from '@/services/api'
import { formatDistance } from 'date-fns'
import { enUS } from 'date-fns/locale'
import { Calendar, Filter, Search } from 'lucide-react'
import { useEffect, useState } from 'react'

interface NewsItem {
  id: string
  title: string
  summary: string
  source_url: string
  source_type: string
  category: string
  priority_score: number
  published_at: string
  created_at: string
}

interface NewsResponse {
  items: NewsItem[]
  total: number
  limit: number
  offset: number
}

export default function NewsPage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCategory, setSelectedCategory] = useState('')
  const [selectedCompanies, setSelectedCompanies] = useState<string[]>([])
  const [news, setNews] = useState<NewsItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [total, setTotal] = useState(0)

  const categories = [
    { value: '', label: 'All Categories' },
    { value: 'product_update', label: 'Product Updates' },
    { value: 'pricing_change', label: 'Pricing Changes' },
    { value: 'strategic_announcement', label: 'Strategic Announcements' },
    { value: 'technical_update', label: 'Technical Updates' },
    { value: 'funding_news', label: 'Funding News' },
    { value: 'research_paper', label: 'Research Papers' },
    { value: 'community_event', label: 'Community Events' },
    { value: 'partnership', label: 'Partnerships' },
    { value: 'acquisition', label: 'Acquisitions' },
    { value: 'integration', label: 'Integrations' },
    { value: 'security_update', label: 'Security Updates' },
    { value: 'api_update', label: 'API Updates' },
    { value: 'model_release', label: 'Model Releases' },
    { value: 'performance_improvement', label: 'Performance Improvements' },
    { value: 'feature_deprecation', label: 'Feature Deprecations' },
  ]

  const categoryLabels: Record<string, string> = {
    'product_update': 'Product Updates',
    'pricing_change': 'Pricing Changes',
    'strategic_announcement': 'Strategic Announcements',
    'technical_update': 'Technical Updates',
    'funding_news': 'Funding News',
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

  // Fetch news from API
  useEffect(() => {
    fetchNews()
  }, [selectedCategory])

  const fetchNews = async () => {
    try {
      setLoading(true)
      setError(null)
      
      const params: any = { limit: 20 }
      if (selectedCategory) {
        params.category = selectedCategory
      }
      
      const response = await api.get<NewsResponse>('/news/', { params })
      setNews(response.data.items)
      setTotal(response.data.total)
      
    } catch (err: any) {
      console.error('Failed to fetch news:', err)
      setError('Failed to load news. Please try refreshing the page.')
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (dateString: string) => {
    try {
      const date = new Date(dateString)
      return formatDistance(date, new Date(), { addSuffix: true, locale: enUS })
    } catch {
      return 'Recently'
    }
  }

  const getCategoryBadge = (category: string) => {
    const label = categoryLabels[category.toLowerCase()] || category
    const colorClass = category === 'product_update' ? 'badge-primary' : 'badge-secondary'
    return { label, colorClass }
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          AI Industry News
        </h1>
        <p className="text-gray-600">
          Latest news from the world of artificial intelligence and machine learning
        </p>
        {total > 0 && (
          <p className="text-sm text-gray-500 mt-2">
            News found: {total}
          </p>
        )}
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-8">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search news..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="input pl-10"
            />
          </div>

          {/* Category Filter */}
          <div className="relative">
            <Filter className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none z-10" />
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="input pl-10 appearance-none"
            >
              {categories.map((category) => (
                <option key={category.value} value={category.value}>
                  {category.label}
                </option>
              ))}
            </select>
          </div>

          {/* Company Filter */}
          <CompanyMultiSelect
            selectedCompanies={selectedCompanies}
            onSelectionChange={setSelectedCompanies}
            placeholder="Select companies..."
          />

          {/* Date Filter */}
          <div className="relative">
            <Calendar className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none z-10" />
            <input
              type="date"
              className="input pl-10"
            />
          </div>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-6">
          {error}
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
          <p className="mt-4 text-gray-600">Loading news...</p>
        </div>
      )}

      {/* Empty State */}
      {!loading && !error && news.length === 0 && (
        <div className="text-center py-12">
          <p className="text-gray-600 text-lg">No news yet</p>
          <p className="text-gray-500 text-sm mt-2">Try changing filters or come back later</p>
        </div>
      )}

      {/* News Grid */}
      {!loading && news.length > 0 && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {news
              .filter((item) =>
                searchQuery === '' ||
                item.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
                (item.summary && item.summary.toLowerCase().includes(searchQuery.toLowerCase()))
              )
              .map((item) => {
                const badge = getCategoryBadge(item.category || 'technical_update')
                
                return (
                  <div key={item.id} className="card p-6 hover:shadow-md transition-shadow">
                    <div className="flex items-center justify-between mb-3">
                      <span className={`badge ${badge.colorClass}`}>
                        {badge.label}
                      </span>
                      <span className="text-sm text-gray-500">
                        {formatDate(item.published_at || item.created_at)}
                      </span>
                    </div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-2 line-clamp-2">
                      {item.title}
                    </h3>
                    <p className="text-gray-600 text-sm mb-4 line-clamp-3">
                      {item.summary || 'No description'}
                    </p>
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

          {/* Load More Button */}
          <div className="text-center mt-8">
            <button
              onClick={fetchNews}
              className="btn btn-outline btn-md"
            >
              Refresh News
            </button>
          </div>
        </>
      )}
    </div>
  )
}
