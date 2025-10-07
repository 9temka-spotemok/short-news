import api from '@/services/api'
import { formatDistance } from 'date-fns'
import { ru } from 'date-fns/locale'
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
  const [news, setNews] = useState<NewsItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [total, setTotal] = useState(0)

  const categories = [
    { value: '', label: 'Все категории' },
    { value: 'product_update', label: 'Обновления продуктов' },
    { value: 'pricing_change', label: 'Изменения цен' },
    { value: 'strategic_announcement', label: 'Стратегические анонсы' },
    { value: 'technical_update', label: 'Технические обновления' },
    { value: 'funding_news', label: 'Новости о финансировании' },
  ]

  const categoryLabels: Record<string, string> = {
    'product_update': 'Обновления продуктов',
    'pricing_change': 'Изменения цен',
    'strategic_announcement': 'Стратегические анонсы',
    'technical_update': 'Технические обновления',
    'funding_news': 'Новости о финансировании',
    'research_paper': 'Исследования',
    'community_event': 'События',
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
      setError('Не удалось загрузить новости. Попробуйте обновить страницу.')
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
          Новости ИИ-индустрии
        </h1>
        <p className="text-gray-600">
          Актуальные новости из мира искусственного интеллекта и машинного обучения
        </p>
        {total > 0 && (
          <p className="text-sm text-gray-500 mt-2">
            Найдено новостей: {total}
          </p>
        )}
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-8">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder="Поиск новостей..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="input pl-10"
            />
          </div>

          {/* Category Filter */}
          <div className="relative">
            <Filter className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
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

          {/* Date Filter */}
          <div className="relative">
            <Calendar className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
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
          <p className="mt-4 text-gray-600">Загрузка новостей...</p>
        </div>
      )}

      {/* Empty State */}
      {!loading && !error && news.length === 0 && (
        <div className="text-center py-12">
          <p className="text-gray-600 text-lg">Новостей пока нет</p>
          <p className="text-gray-500 text-sm mt-2">Попробуйте изменить фильтры или вернитесь позже</p>
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
                      {item.summary || 'Нет описания'}
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
                        Читать далее →
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
              Обновить новости
            </button>
          </div>
        </>
      )}
    </div>
  )
}
