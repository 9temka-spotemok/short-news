import CompanyMultiSelect from '@/components/CompanyMultiSelect'
import TrackedCompaniesManager from '@/components/TrackedCompaniesManager'
import { useNewsAnalytics } from '@/hooks/useNews'
import api, { ApiService } from '@/services/api'
import { useAuthStore } from '@/store/authStore'
import { useQuery } from '@tanstack/react-query'
import { formatDistance } from 'date-fns'
import { enUS } from 'date-fns/locale'
import { Bell, Calendar, Filter, Search, TrendingUp } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
 

interface NewsItem {
  id: string
  title: string
  summary: string
  source_url: string
  source_type: string
  category: string
  published_at: string
  created_at: string
  company?: {
    id: string
    name: string
    website?: string
  }
}

interface DashboardStats {
  todayNews: number
  totalNews: number
  categoriesBreakdown: { category: string; technicalCategory?: string; count: number; percentage: number }[]
}

interface DigestData {
  date_from: string
  date_to: string
  news_count: number
  categories?: Record<string, NewsItem[]>
  statistics?: {
    total_news: number
    by_category: Record<string, number>
    by_source: Record<string, number>
    avg_priority: number
  }
  format: string
}

export default function DashboardPage() {
  const { isAuthenticated, user, accessToken } = useAuthStore()
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState('overview')
  const [recentNews, setRecentNews] = useState<NewsItem[]>([])
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [selectedCategory, setSelectedCategory] = useState('')
  const [selectedCompanies, setSelectedCompanies] = useState<string[]>([])
  const [selectedDate, setSelectedDate] = useState('')
  const [availableCategories, setAvailableCategories] = useState<{ value: string; description: string }[]>([])
  const [showAllCategories, setShowAllCategories] = useState(false)
  const [showAllCompanies, setShowAllCompanies] = useState(false)
  const [showTrackedOnly, setShowTrackedOnly] = useState(false) // Переключатель: все новости (false) / только отслеживаемые компании (true)
  // Notifications are handled globally in NotificationCenter
  
  // Digest state
  const [digest, setDigest] = useState<DigestData | null>(null)
  const [digestLoading, setDigestLoading] = useState(false)
  const [digestError, setDigestError] = useState<string | null>(null)
  
  // Use news analytics for comprehensive statistics
  const { stats: allStats, categoryTrends } = useNewsAnalytics()
  
  // Debug authentication state
  useEffect(() => {
    console.log('DashboardPage auth state:', {
      isAuthenticated,
      user: user?.email,
      hasToken: !!accessToken,
      tokenPreview: accessToken ? accessToken.substring(0, 50) + '...' : 'None'
    })
  }, [isAuthenticated, user, accessToken])

  const tabs = [
    { id: 'overview', label: 'Overview' },
    // { id: 'news', label: 'News' },
    { id: 'digest', label: 'Digests' },
    // { id: 'analytics', label: 'Analytics' },
  ]

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

  // Create reverse mapping from display names to technical names
  const categoryTechnicalNames: Record<string, string> = Object.fromEntries(
    Object.entries(categoryLabels).map(([tech, display]) => [display, tech])
  )

  // Load categories/source types metadata
  const { data: categoriesData } = useQuery({
    queryKey: ['news-categories'],
    queryFn: ApiService.getNewsCategories,
    staleTime: 1000 * 60 * 60,
  })

  // Load user preferences for personalization
  const { data: userPreferences } = useQuery({
    queryKey: ['user-preferences'],
    queryFn: ApiService.getUserPreferences,
    staleTime: 1000 * 60 * 5, // 5 minutes
  })

  useEffect(() => {
    fetchDashboardData()
  }, [userPreferences?.subscribed_companies, showTrackedOnly])

  // Listen for global refresh event from NotificationCenter
  useEffect(() => {
    const handler = () => {
      fetchDashboardData()
    }
    window.addEventListener('app:refresh-news', handler as EventListener)
    return () => window.removeEventListener('app:refresh-news', handler as EventListener)
  }, [])
  
  // Recompute available categories based on recentNews usage
  useEffect(() => {
    if (!categoriesData) return
    const used = new Set(recentNews.map((n) => n.category).filter(Boolean))
    const all = categoriesData.categories
    const filtered = all.filter((c: any) => used.has(c.value))
    setAvailableCategories(showAllCategories ? all : filtered)
  }, [categoriesData, recentNews, showAllCategories])

  // Уведомления перенесены в глобальный NotificationCenter

  // Refetch when filters change on news tab
  useEffect(() => {
    if (activeTab === 'news') {
      fetchFilteredNews()
    }
  }, [selectedCategory, selectedCompanies, activeTab])

  const fetchDashboardData = async () => {
    try {
      setLoading(true)
      
      // Build query parameters for news
      const params: any = { limit: 20 }
      
      // Apply company filter only if user wants to see tracked companies AND has them
      if (showTrackedOnly && userPreferences?.subscribed_companies?.length) {
        params.companies = userPreferences.subscribed_companies.join(',')
      }
      
      // Fetch news
      const newsResponse = await api.get('/news/', { params })
      setRecentNews(newsResponse.data.items)
      
      // Calculate stats from loaded news (for today's news count)
      const items = newsResponse.data.items
      const todayNews = items.filter((item: NewsItem) => {
        const published = new Date(item.published_at || item.created_at)
        const today = new Date()
        return published.toDateString() === today.toDateString()
      }).length
      
      // Use stats based on current mode
      let categoriesBreakdown
      let totalNews
      
      if (showTrackedOnly) {
        // Build stats from loaded news (for tracked companies)
        const categoryCount: Record<string, number> = {}
        items.forEach((item: NewsItem) => {
          const cat = item.category || 'other'
          categoryCount[cat] = (categoryCount[cat] || 0) + 1
        })
        
        const total = newsResponse.data.total
        categoriesBreakdown = Object.entries(categoryCount)
          .map(([category, count]) => ({
            category: categoryLabels[category] || category,
            technicalCategory: category, // Keep original technical name
            count,
            percentage: total > 0 ? Math.round((count / total) * 100) : 0
          }))
          .sort((a, b) => b.count - a.count)
        
        totalNews = total
      } else {
        // Use comprehensive stats from API for all news
        categoriesBreakdown = categoryTrends.map(trend => ({
          category: trend.category,
          technicalCategory: trend.technicalCategory,
          count: trend.count,
          percentage: Math.round(trend.percentage)
        }))
        totalNews = allStats?.total_count || newsResponse.data.total
      }
      
      setStats({
        todayNews,
        totalNews,
        categoriesBreakdown
      })
      
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error)
    } finally {
      setLoading(false)
    }
  }

  const fetchFilteredNews = async () => {
    try {
      setLoading(true)
      
      const params: any = { limit: 20 }
      if (selectedCategory) {
        params.category = selectedCategory
      }
      if (selectedCompanies.length > 0) {
        params.companies = selectedCompanies.join(',')
      }
      
      const response = await api.get('/news/', { params })
      setRecentNews(response.data.items)
      
    } catch (error) {
      console.error('Failed to fetch filtered news:', error)
    } finally {
      setLoading(false)
    }
  }

  const fetchDigest = async (type: 'daily' | 'weekly' | 'custom') => {
    try {
      setDigestLoading(true)
      setDigestError(null)
      
      console.log('Fetching digest:', type)
      
      let endpoint = ''
      switch (type) {
        case 'daily':
          endpoint = '/digest/daily'
          break
        case 'weekly':
          endpoint = '/digest/weekly'
          break
        case 'custom':
          // Default to last 7 days for custom
          const dateFrom = new Date()
          dateFrom.setDate(dateFrom.getDate() - 7)
          endpoint = `/digest/custom?date_from=${dateFrom.toISOString().split('T')[0]}&date_to=${new Date().toISOString().split('T')[0]}`
          break
      }
      
      console.log('Making request to:', endpoint)
      const response = await api.get(endpoint)
      console.log('Digest response:', response.data)
      setDigest(response.data)
      
    } catch (error: any) {
      console.error('Failed to fetch digest:', error)
      console.error('Error details:', {
        message: error.message,
        status: error.response?.status,
        statusText: error.response?.statusText,
        data: error.response?.data
      })
      setDigestError(error.response?.data?.detail || error.response?.data?.message || 'Failed to load digest')
    } finally {
      setDigestLoading(false)
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
  
  const filteredNews = selectedDate
    ? recentNews.filter((item) => {
        const itemDate = new Date(item.published_at || item.created_at)
        const filterDate = new Date(selectedDate)
        return itemDate.toDateString() === filterDate.toDateString()
      })
    : recentNews

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 mb-2">Dashboard</h1>
              <div className="flex items-center space-x-4">
                {userPreferences?.subscribed_companies?.length ? (
                  <p className="text-gray-600">
                    {showTrackedOnly ? `Personalized for ${userPreferences.subscribed_companies.length} tracked companies` : 'Showing all news'}
                  </p>
                ) : (
                  <p className="text-gray-600">
                    Showing all news • <span className="text-primary-600">Add companies to personalize</span>
                  </p>
                )}
                
                {/* Toggle Switch */}
                {userPreferences?.subscribed_companies?.length && (
                  <div className="flex items-center space-x-2">
                    <span className="text-sm text-gray-600">All News</span>
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
          </div>
        </div>

        {/* Tabs */}
        <div className="border-b border-gray-200 mb-8">
          <nav className="-mb-px flex space-x-8">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`py-2 px-1 border-b-2 font-medium text-sm ${
                  activeTab === tab.id
                    ? 'border-primary-500 text-primary-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        {/* Tab Content */}
        {activeTab === 'overview' && (
          <div className="space-y-8">
            {/* Stats Cards */}
            {loading ? (
              <div className="text-center py-12">
                <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
                <p className="mt-4 text-gray-600">Loading statistics...</p>
              </div>
            ) : (
              <>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  <div className="card p-6">
                    <div className="flex items-center">
                      <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
                        <Bell className="h-6 w-6 text-green-600" />
                      </div>
                      <div className="ml-4">
                        <p className="text-sm font-medium text-gray-600">News Today</p>
                        <p className="text-2xl font-bold text-gray-900">{stats?.todayNews || 0}</p>
                      </div>
                    </div>
                  </div>

                  <div className="card p-6">
                    <div className="flex items-center">
                      <div className="w-12 h-12 bg-yellow-100 rounded-lg flex items-center justify-center">
                        <Calendar className="h-6 w-6 text-yellow-600" />
                      </div>
                      <div className="ml-4">
                        <p className="text-sm font-medium text-gray-600">Total News</p>
                        <p className="text-2xl font-bold text-gray-900">{stats?.totalNews || 0}</p>
                      </div>
                    </div>
                  </div>

                  <div className="card p-6">
                    <div className="flex items-center">
                      <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
                        <Filter className="h-6 w-6 text-purple-600" />
                      </div>
                      <div className="ml-4">
                        <p className="text-sm font-medium text-gray-600">Categories</p>
                        <p className="text-2xl font-bold text-gray-900">{stats?.categoriesBreakdown.length || 0}</p>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Tracked Companies Manager */}
                <TrackedCompaniesManager />

                {/* Recent News and Categories */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                  {/* Recent News */}
                  <div className="card p-6">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-lg font-semibold text-gray-900">
                        Recent News
                        {/* {userPreferences?.subscribed_companies?.length && showTrackedOnly && (
                          <span className="ml-2 text-sm font-normal text-primary-600">
                            (from tracked companies)
                          </span>
                        )} */}
                      </h3>
                    </div>
                    <div className="space-y-4">
                      {recentNews.slice(0, 5).map((item) => (
                        <div key={item.id} className="flex items-start space-x-3">
                          <div className="w-2 h-2 bg-primary-600 rounded-full mt-2"></div>
                          <div className="flex-1">
                            <a
                              href={item.source_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-sm text-gray-900 hover:text-primary-600 line-clamp-2"
                            >
                              {item.title}
                            </a>
                            <div className="flex items-center space-x-2 mt-1">
                              <p className="text-xs text-gray-500">
                                {formatDate(item.published_at || item.created_at)}
                              </p>
                              {item.company && (
                                <>
                                  <span className="text-xs text-gray-400">•</span>
                                  <span className="text-xs bg-gray-100 text-gray-700 px-2 py-0.5 rounded-full">
                                    {item.company.name}
                                  </span>
                                </>
                              )}
                            </div>
                          </div>
                        </div>
                      ))}
                      {recentNews.length === 0 && (
                        <p className="text-sm text-gray-500">No news yet</p>
                      )}
                    </div>
                  </div>

                  {/* Top Categories */}
                  <div className="card p-6">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-lg font-semibold text-gray-900 flex items-center">
                        <TrendingUp className="h-5 w-5 mr-2 text-green-600" />
                        Top Categories
                        {/* {userPreferences?.subscribed_companies?.length && showTrackedOnly && (
                          <span className="ml-2 text-sm font-normal text-primary-600">
                            (from tracked companies)
                          </span>
                        )} */}
                        {!showTrackedOnly && (
                          <span className="ml-2 text-sm font-normal text-gray-600">
                            (all news)
                          </span>
                        )}
                      </h3>
                    </div>
                    <div className="space-y-3">
                      {stats?.categoriesBreakdown.map((category, index) => {
                        // Get technical name for navigation - prefer technicalCategory if available
                        const technicalName = category.technicalCategory || categoryTechnicalNames[category.category] || category.category
                        return (
                        <button
                          key={category.category}
                          onClick={() => {
                            const params = new URLSearchParams()
                            if (showTrackedOnly && userPreferences?.subscribed_companies?.length) {
                              params.set('tracked', 'true')
                            }
                            const queryString = params.toString()
                            navigate(`/category/${technicalName}${queryString ? `?${queryString}` : ''}`)
                          }}
                          className="w-full flex items-center justify-between hover:bg-gray-50 p-2 rounded-lg transition-colors cursor-pointer group"
                        >
                          <div className="flex items-center">
                            <span className="text-sm font-medium text-gray-500 w-6">
                              #{index + 1}
                            </span>
                            <span className="text-sm font-medium text-gray-900 ml-2 group-hover:text-primary-600">
                              {category.category}
                            </span>
                          </div>
                          <div className="flex items-center space-x-2">
                            <span className="text-sm text-gray-500">
                              {category.count}
                            </span>
                            <span className="text-xs text-gray-400">
                              ({category.percentage}%)
                            </span>
                          </div>
                        </button>
                        )
                      })}
                      {(!stats || stats.categoriesBreakdown.length === 0) && (
                        <p className="text-sm text-gray-500">No data yet</p>
                      )}
                    </div>
                  </div>
                </div>
              </>
            )}
          </div>
        )}

        {activeTab === 'news' && (
          <div className="space-y-6">
            {/* News Filters */}
            <div className="card p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900">News Filters</h3>
                <a href="/news" className="btn btn-outline btn-sm">
                  <Search className="h-4 w-4 mr-2" />
                  Advanced Search
                </a>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <select 
                  className="input"
                  value={selectedCategory}
                  onChange={(e) => setSelectedCategory(e.target.value)}
                >
                  <option value="">Все категории</option>
                  {availableCategories.map((cat) => (
                    <option key={cat.value} value={cat.value}>
                      {categoryLabels[cat.value] || cat.description || cat.value}
                    </option>
                  ))}
                </select>
                <CompanyMultiSelect
                  selectedCompanies={selectedCompanies}
                  onSelectionChange={setSelectedCompanies}
                  placeholder="Выберите компании..."
                  availableCompanyIds={showAllCompanies ? undefined : Array.from(new Set(recentNews.map((n) => n.company?.id).filter((id): id is string => Boolean(id))))}
                />
                <input 
                  type="date" 
                  className="input"
                  value={selectedDate}
                  onChange={(e) => setSelectedDate(e.target.value)}
                />
              </div>
              <div className="flex items-center gap-3 mt-2">
                <label className="text-xs text-gray-600 inline-flex items-center gap-1">
                  <input
                    type="checkbox"
                    className="mr-1"
                    checked={showAllCategories}
                    onChange={(e) => setShowAllCategories(e.target.checked)}
                  />
                  Показать все категории
                </label>
                <label className="text-xs text-gray-600 inline-flex items-center gap-1">
                  <input
                    type="checkbox"
                    className="mr-1"
                    checked={showAllCompanies}
                    onChange={(e) => setShowAllCompanies(e.target.checked)}
                  />
                  Показать все компании
                </label>
              </div>
              {(selectedCategory || selectedCompanies.length > 0 || selectedDate) && (
                <div className="mt-4 flex items-center justify-between">
                  <p className="text-sm text-gray-600">
                    {selectedCategory && `Category: ${categoryLabels[selectedCategory] || selectedCategory}`}
                    {selectedCategory && (selectedCompanies.length > 0 || selectedDate) && ' • '}
                    {selectedCompanies.length > 0 && `Companies: ${selectedCompanies.length}`}
                    {selectedCompanies.length > 0 && selectedDate && ' • '}
                    {selectedDate && `Date: ${new Date(selectedDate).toLocaleDateString('en-US')}`}
                  </p>
                  <button
                    onClick={() => {
                      setSelectedCategory('')
                      setSelectedCompanies([])
                      setSelectedDate('')
                    }}
                    className="text-sm text-primary-600 hover:text-primary-700 font-medium"
                  >
                    Reset Filters
                  </button>
                </div>
              )}
            </div>

            {/* News List */}
            {loading ? (
              <div className="text-center py-12">
                <p className="text-gray-600">Loading news...</p>
              </div>
            ) : (
              <div className="space-y-4">
                {filteredNews.slice(0, 10).map((item) => (
                  <div key={item.id} className="card p-6">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center space-x-2 mb-2">
                          <span className={`badge ${
                            item.category === 'product_update' ? 'badge-primary' : 
                            item.category === 'technical_update' ? 'badge-secondary' :
                            'badge-gray'
                          }`}>
                            {categoryLabels[item.category] || item.category}
                          </span>
                          {item.company && (
                            <>
                              <span className="text-sm text-gray-500">•</span>
                              <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full font-medium">
                                {item.company.name}
                              </span>
                            </>
                          )}
                          <span className="text-sm text-gray-500">•</span>
                          <span className="text-sm text-gray-500">
                            {formatDate(item.published_at || item.created_at)}
                          </span>
                        </div>
                        <h4 className="text-lg font-semibold text-gray-900 mb-2 line-clamp-2">
                          {item.title}
                        </h4>
                        <p className="text-gray-600 text-sm mb-3 line-clamp-2">
                          {item.summary || 'No description'}
                        </p>
                        <div className="flex items-center space-x-4">
                          <a
                            href={item.source_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-primary-600 hover:text-primary-700 text-sm font-medium"
                          >
                            Read more →
                          </a>
                          <span className="text-gray-500 text-sm capitalize">
                            {item.source_type}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
                {filteredNews.length === 0 && !loading && (
                  <div className="text-center py-12">
                    <p className="text-gray-600">No news found</p>
                    <button
                      onClick={() => {
                        setSelectedCategory('')
                        setSelectedDate('')
                      }}
                      className="mt-4 text-sm text-primary-600 hover:text-primary-700 font-medium"
                    >
                      Reset Filters
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {activeTab === 'digest' && (
          <div className="space-y-6">
            {/* Settings Link */}
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <Bell className="w-5 h-5 text-blue-600" />
                  <p className="text-sm text-blue-900">
                    Configure digest settings for automatic delivery
                  </p>
                </div>
                <a href="/digest-settings" className="text-sm font-medium text-blue-600 hover:text-blue-700">
                  Go to Settings →
                </a>
              </div>
            </div>

            <div className="card p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">
                Generate Digests
              </h3>
              <p className="text-gray-600 mb-6">
                Create personalized digests based on your preferences
              </p>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <button 
                  onClick={() => fetchDigest('daily')}
                  disabled={digestLoading}
                  className="btn btn-outline btn-md flex flex-col items-center p-4"
                >
                  <span className="font-medium">
                    {digestLoading ? 'Loading...' : 'Daily Digest'}
                  </span>
                </button>
                <button 
                  onClick={() => fetchDigest('weekly')}
                  disabled={digestLoading}
                  className="btn btn-outline btn-md flex flex-col items-center p-4"
                >
                  <span className="font-medium">Weekly Digest</span>
                </button>
                <button 
                  onClick={() => fetchDigest('custom')}
                  disabled={digestLoading}
                  className="btn btn-outline btn-md flex flex-col items-center p-4"
                >
                  <span className="font-medium">Custom Period</span>
                </button>
              </div>
            </div>

            {/* Error Message */}
            {digestError && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                <p className="text-sm text-red-800">{digestError}</p>
              </div>
            )}

            {/* Digest Results */}
            <div className="card p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900">
                  Digest Results
                </h3>
                {digest && (
                  <span className="text-sm text-gray-500">
                    {digest.news_count} news items • {digest.format}
                  </span>
                )}
              </div>

              {digestLoading && (
                <div className="text-center py-8">
                  <div className="inline-block w-8 h-8 border-4 border-primary-600 border-t-transparent rounded-full animate-spin"></div>
                  <p className="text-gray-600 mt-4">Generating digest...</p>
                </div>
              )}

              {!digestLoading && !digest && !digestError && (
                <div className="text-center py-8">
                  <p className="text-gray-600">Click a button above to generate a digest</p>
                  <p className="text-sm text-gray-500 mt-2">
                    Digests are personalized based on your preferences
                  </p>
                </div>
              )}

              {!digestLoading && digest && (
                <div className="space-y-6">
                  {/* Period Information */}
                  <div className="bg-gray-50 rounded-lg p-4 mb-6">
                    <div className="flex items-center justify-between">
                      <div>
                        <h4 className="font-medium text-gray-900">Digest Period</h4>
                        <p className="text-sm text-gray-600">
                          {new Date(digest.date_from).toLocaleDateString('en-US', {
                            year: 'numeric',
                            month: 'long',
                            day: 'numeric'
                          })} - {new Date(digest.date_to).toLocaleDateString('en-US', {
                            year: 'numeric',
                            month: 'long',
                            day: 'numeric'
                          })}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="text-sm font-medium text-gray-900">{digest.news_count} news items</p>
                        <p className="text-xs text-gray-500 capitalize">{digest.format} format</p>
                      </div>
                    </div>
                  </div>

                  {digest.categories && Object.entries(digest.categories).map(([category, items]) => (
                    <div key={category}>
                      <h4 className="font-semibold text-gray-900 mb-3 flex items-center">
                        <span className="px-2 py-1 text-sm rounded bg-primary-100 text-primary-700 mr-2">
                          {categoryLabels[category] || category}
                        </span>
                        <span className="text-sm text-gray-500">({items.length})</span>
                      </h4>
                      <div className="space-y-4">
                        {items.map((item: any) => (
                          <div key={item.id} className="border-b border-gray-100 pb-4 last:border-0">
                            <div className="flex items-start justify-between">
                              <div className="flex-1">
                                <a 
                                  href={item.source_url} 
                                  target="_blank" 
                                  rel="noopener noreferrer"
                                  className="text-base font-medium text-gray-900 hover:text-primary-600"
                                >
                                  {item.title}
                                </a>
                                {item.summary && <p className="text-sm text-gray-600 mt-1">{item.summary}</p>}
                                <div className="flex items-center space-x-3 mt-2">
                                  {item.company && (
                                    <span className="px-2 py-1 text-xs rounded-full bg-blue-100 text-blue-700">
                                      {item.company.name}
                                    </span>
                                  )}
                                  <span className="text-xs text-gray-500">
                                    {formatDate(item.published_at)}
                                  </span>
                                </div>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                  {(!digest.categories || Object.keys(digest.categories).length === 0) && (
                    <p className="text-center text-gray-500 py-4">
                      No news items found for this period
                    </p>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
