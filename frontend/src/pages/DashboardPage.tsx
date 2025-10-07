import api from '@/services/api'
import { formatDistance } from 'date-fns'
import { ru } from 'date-fns/locale'
import { Bell, Calendar, Filter, Search, TrendingUp } from 'lucide-react'
import { useEffect, useState } from 'react'

interface NewsItem {
  id: string
  title: string
  summary: string
  source_url: string
  source_type: string
  category: string
  published_at: string
  created_at: string
}

interface DashboardStats {
  totalCompanies: number
  todayNews: number
  totalNews: number
  categoriesBreakdown: { category: string; count: number; percentage: number }[]
}

export default function DashboardPage() {
  const [activeTab, setActiveTab] = useState('overview')
  const [recentNews, setRecentNews] = useState<NewsItem[]>([])
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [selectedCategory, setSelectedCategory] = useState('')
  const [selectedCompany, setSelectedCompany] = useState('')
  const [selectedDate, setSelectedDate] = useState('')

  const tabs = [
    { id: 'overview', label: 'Обзор' },
    { id: 'news', label: 'Новости' },
    { id: 'digest', label: 'Дайджесты' },
    { id: 'analytics', label: 'Аналитика' },
  ]

  const categoryLabels: Record<string, string> = {
    'product_update': 'Обновления продуктов',
    'technical_update': 'Технические обновления',
    'strategic_announcement': 'Стратегические анонсы',
    'funding_news': 'Новости о финансировании',
    'pricing_change': 'Изменения цен',
    'research_paper': 'Исследования',
    'community_event': 'События',
  }

  useEffect(() => {
    fetchDashboardData()
  }, [])
  
  // Refetch when filters change on news tab
  useEffect(() => {
    if (activeTab === 'news') {
      fetchFilteredNews()
    }
  }, [selectedCategory, selectedCompany, activeTab])

  const fetchDashboardData = async () => {
    try {
      setLoading(true)
      
      // Fetch recent news
      const newsResponse = await api.get('/news/', { params: { limit: 20 } })
      setRecentNews(newsResponse.data.items)
      
      // Calculate stats
      const total = newsResponse.data.total
      const items = newsResponse.data.items
      
      // Count by category
      const categoryCount: Record<string, number> = {}
      items.forEach((item: NewsItem) => {
        const cat = item.category || 'other'
        categoryCount[cat] = (categoryCount[cat] || 0) + 1
      })
      
      const categoriesBreakdown = Object.entries(categoryCount)
        .map(([category, count]) => ({
          category: categoryLabels[category] || category,
          count,
          percentage: total > 0 ? Math.round((count / total) * 100) : 0
        }))
        .sort((a, b) => b.count - a.count)
      
      setStats({
        totalCompanies: 10, // Известно из seed
        todayNews: items.filter((item: NewsItem) => {
          const published = new Date(item.published_at || item.created_at)
          const today = new Date()
          return published.toDateString() === today.toDateString()
        }).length,
        totalNews: total,
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
      if (selectedCompany) {
        params.company = selectedCompany
      }
      
      const response = await api.get('/news/', { params })
      setRecentNews(response.data.items)
      
    } catch (error) {
      console.error('Failed to fetch filtered news:', error)
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (dateString: string) => {
    try {
      const date = new Date(dateString)
      return formatDistance(date, new Date(), { addSuffix: true, locale: ru })
    } catch {
      return 'Недавно'
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
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Панель управления
          </h1>
          <p className="text-gray-600">
            Добро пожаловать в AI Competitor Insight Hub
          </p>
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
                <p className="mt-4 text-gray-600">Загрузка статистики...</p>
              </div>
            ) : (
              <>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                  <div className="card p-6">
                    <div className="flex items-center">
                      <div className="w-12 h-12 bg-primary-100 rounded-lg flex items-center justify-center">
                        <TrendingUp className="h-6 w-6 text-primary-600" />
                      </div>
                      <div className="ml-4">
                        <p className="text-sm font-medium text-gray-600">Отслеживаемых компаний</p>
                        <p className="text-2xl font-bold text-gray-900">{stats?.totalCompanies || 0}</p>
                      </div>
                    </div>
                  </div>

                  <div className="card p-6">
                    <div className="flex items-center">
                      <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
                        <Bell className="h-6 w-6 text-green-600" />
                      </div>
                      <div className="ml-4">
                        <p className="text-sm font-medium text-gray-600">Новостей сегодня</p>
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
                        <p className="text-sm font-medium text-gray-600">Всего новостей</p>
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
                        <p className="text-sm font-medium text-gray-600">Категорий</p>
                        <p className="text-2xl font-bold text-gray-900">{stats?.categoriesBreakdown.length || 0}</p>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Recent News and Categories */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                  {/* Recent News */}
                  <div className="card p-6">
                    <h3 className="text-lg font-semibold text-gray-900 mb-4">
                      Последние новости
                    </h3>
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
                            <p className="text-xs text-gray-500 mt-1">
                              {formatDate(item.published_at || item.created_at)}
                            </p>
                          </div>
                        </div>
                      ))}
                      {recentNews.length === 0 && (
                        <p className="text-sm text-gray-500">Новостей пока нет</p>
                      )}
                    </div>
                  </div>

                  {/* Popular Categories */}
                  <div className="card p-6">
                    <h3 className="text-lg font-semibold text-gray-900 mb-4">
                      Популярные категории
                    </h3>
                    <div className="space-y-3">
                      {stats?.categoriesBreakdown.slice(0, 4).map((category) => (
                        <div key={category.category} className="flex items-center justify-between">
                          <span className="text-sm text-gray-700">{category.category}</span>
                          <div className="flex items-center space-x-2">
                            <div className="w-16 h-2 bg-gray-200 rounded-full">
                              <div
                                className="h-2 bg-primary-600 rounded-full"
                                style={{ width: `${category.percentage}%` }}
                              ></div>
                            </div>
                            <span className="text-xs text-gray-500">{category.count}</span>
                          </div>
                        </div>
                      ))}
                      {(!stats || stats.categoriesBreakdown.length === 0) && (
                        <p className="text-sm text-gray-500">Данных пока нет</p>
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
                <h3 className="text-lg font-semibold text-gray-900">Фильтры новостей</h3>
                <a href="/news" className="btn btn-outline btn-sm">
                  <Search className="h-4 w-4 mr-2" />
                  Расширенный поиск
                </a>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <select 
                  className="input"
                  value={selectedCategory}
                  onChange={(e) => setSelectedCategory(e.target.value)}
                >
                  <option value="">Все категории</option>
                  <option value="product_update">Обновления продуктов</option>
                  <option value="technical_update">Технические обновления</option>
                  <option value="strategic_announcement">Стратегические анонсы</option>
                  <option value="funding_news">Новости о финансировании</option>
                  <option value="pricing_change">Изменения цен</option>
                </select>
                <select 
                  className="input"
                  value={selectedCompany}
                  onChange={(e) => setSelectedCompany(e.target.value)}
                  disabled
                >
                  <option value="">Все компании</option>
                  <option value="openai">OpenAI</option>
                  <option value="anthropic">Anthropic</option>
                  <option value="google">Google</option>
                  <option value="meta">Meta</option>
                </select>
                <input 
                  type="date" 
                  className="input"
                  value={selectedDate}
                  onChange={(e) => setSelectedDate(e.target.value)}
                />
              </div>
              {(selectedCategory || selectedDate) && (
                <div className="mt-4 flex items-center justify-between">
                  <p className="text-sm text-gray-600">
                    {selectedCategory && `Категория: ${categoryLabels[selectedCategory] || selectedCategory}`}
                    {selectedCategory && selectedDate && ' • '}
                    {selectedDate && `Дата: ${new Date(selectedDate).toLocaleDateString('ru-RU')}`}
                  </p>
                  <button
                    onClick={() => {
                      setSelectedCategory('')
                      setSelectedCompany('')
                      setSelectedDate('')
                    }}
                    className="text-sm text-primary-600 hover:text-primary-700 font-medium"
                  >
                    Сбросить фильтры
                  </button>
                </div>
              )}
            </div>

            {/* News List */}
            {loading ? (
              <div className="text-center py-12">
                <p className="text-gray-600">Загрузка новостей...</p>
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
                          <span className="text-sm text-gray-500">•</span>
                          <span className="text-sm text-gray-500">
                            {formatDate(item.published_at || item.created_at)}
                          </span>
                        </div>
                        <h4 className="text-lg font-semibold text-gray-900 mb-2 line-clamp-2">
                          {item.title}
                        </h4>
                        <p className="text-gray-600 text-sm mb-3 line-clamp-2">
                          {item.summary || 'Нет описания'}
                        </p>
                        <div className="flex items-center space-x-4">
                          <a
                            href={item.source_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-primary-600 hover:text-primary-700 text-sm font-medium"
                          >
                            Читать далее →
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
                    <p className="text-gray-600">Новостей не найдено</p>
                    <button
                      onClick={() => {
                        setSelectedCategory('')
                        setSelectedDate('')
                      }}
                      className="mt-4 text-sm text-primary-600 hover:text-primary-700 font-medium"
                    >
                      Сбросить фильтры
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {activeTab === 'digest' && (
          <div className="space-y-6">
            <div className="card p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">
                Генерация дайджестов
              </h3>
              <p className="text-gray-600 mb-6">
                Создавайте персонализированные дайджесты на основе ваших предпочтений
              </p>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <button className="btn btn-primary btn-md">
                  Ежедневный дайджест
                </button>
                <button className="btn btn-outline btn-md">
                  Еженедельный дайджест
                </button>
                <button className="btn btn-outline btn-md">
                  Кастомный дайджест
                </button>
              </div>
            </div>

            <div className="card p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">
                Последние дайджесты
              </h3>
              <div className="text-center py-8">
                <p className="text-gray-600">Дайджесты будут доступны после реализации email системы</p>
                <p className="text-sm text-gray-500 mt-2">
                  Всего новостей для дайджеста: {stats?.totalNews || 0}
                </p>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'analytics' && (
          <div className="space-y-6">
            <div className="card p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">
                Аналитика и тренды
              </h3>
              <p className="text-gray-600 mb-6">
                Анализ активности и трендов в ИИ-индустрии
              </p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="p-4 bg-gray-50 rounded-lg">
                  <h4 className="font-medium text-gray-900 mb-2">Всего новостей</h4>
                  <p className="text-2xl font-bold text-primary-600">{stats?.totalNews || 0}</p>
                  <p className="text-sm text-gray-600">в базе данных</p>
                </div>
                <div className="p-4 bg-gray-50 rounded-lg">
                  <h4 className="font-medium text-gray-900 mb-2">Новостей сегодня</h4>
                  <p className="text-2xl font-bold text-green-600">{stats?.todayNews || 0}</p>
                  <p className="text-sm text-gray-600">опубликовано сегодня</p>
                </div>
              </div>
            </div>

            {/* Category Trends */}
            <div className="card p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">
                Распределение по категориям
              </h3>
              <div className="space-y-4">
                {stats?.categoriesBreakdown.map((category) => (
                  <div key={category.category} className="flex items-center justify-between">
                    <span className="text-sm text-gray-700">{category.category}</span>
                    <div className="flex items-center space-x-2">
                      <div className="w-32 h-2 bg-gray-200 rounded-full">
                        <div
                          className="h-2 bg-primary-600 rounded-full transition-all"
                          style={{ width: `${category.percentage}%` }}
                        ></div>
                      </div>
                      <span className="text-xs text-gray-500 w-12 text-right">
                        {category.count} ({category.percentage}%)
                      </span>
                    </div>
                  </div>
                ))}
                {(!stats || stats.categoriesBreakdown.length === 0) && (
                  <p className="text-sm text-gray-500 text-center py-4">Данных пока нет</p>
                )}
              </div>
            </div>

            {/* Recent Activity */}
            <div className="card p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">
                Последняя активность
              </h3>
              <div className="space-y-3">
                {recentNews.slice(0, 8).map((item) => (
                  <div key={item.id} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-gray-900 truncate">{item.title}</p>
                      <p className="text-xs text-gray-500 mt-1">
                        {formatDate(item.published_at || item.created_at)}
                      </p>
                    </div>
                    <span className="ml-4 px-2 py-1 text-xs rounded-full bg-gray-100 text-gray-600 capitalize">
                      {item.source_type}
                    </span>
                  </div>
                ))}
                {recentNews.length === 0 && (
                  <p className="text-sm text-gray-500 text-center py-4">Активности пока нет</p>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
