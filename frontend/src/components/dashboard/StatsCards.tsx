import { Bell, Calendar, Filter, TrendingUp, TrendingDown } from 'lucide-react'
import { Link } from 'react-router-dom'

interface CategoryBreakdown {
  category: string
  technicalCategory?: string
  count: number
  percentage: number
}

interface StatsCardsProps {
  todayNews: number
  totalNews: number
  categoriesCount: number
  categoriesBreakdown?: CategoryBreakdown[]
  loading?: boolean
  showLinkToAnalytics?: boolean
}

export default function StatsCards({
  todayNews,
  totalNews,
  categoriesCount,
  categoriesBreakdown,
  loading = false,
  showLinkToAnalytics = true
}: StatsCardsProps) {
  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {[1, 2, 3].map((i) => (
          <div key={i} className="card p-6 animate-pulse">
            <div className="flex items-center">
              <div className="w-12 h-12 bg-gray-200 rounded-lg"></div>
              <div className="ml-4 flex-1">
                <div className="h-4 bg-gray-200 rounded w-24 mb-2"></div>
                <div className="h-8 bg-gray-200 rounded w-16"></div>
              </div>
            </div>
          </div>
        ))}
      </div>
    )
  }

  // Calculate trend (mock for now - можно улучшить с реальными данными)
  const getTrend = (current: number, previous?: number) => {
    if (!previous) return null
    const diff = current - previous
    const percent = previous > 0 ? Math.round((diff / previous) * 100) : 0
    return { diff, percent, isPositive: diff >= 0 }
  }

  const todayTrend = getTrend(todayNews) // Можно добавить предыдущее значение

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {/* News Today Card */}
      <div className="card p-6 hover:shadow-lg transition-shadow group">
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center group-hover:bg-green-200 transition-colors">
              <Bell className="h-6 w-6 text-green-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">News Today</p>
              <div className="flex items-baseline gap-2">
                <p className="text-2xl font-bold text-gray-900">{todayNews}</p>
                {todayTrend && (
                  <span className={`text-xs font-medium flex items-center gap-1 ${
                    todayTrend.isPositive ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {todayTrend.isPositive ? (
                      <TrendingUp className="h-3 w-3" />
                    ) : (
                      <TrendingDown className="h-3 w-3" />
                    )}
                    {Math.abs(todayTrend.percent)}%
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Total News Card */}
      <div className="card p-6 hover:shadow-lg transition-shadow group">
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <div className="w-12 h-12 bg-yellow-100 rounded-lg flex items-center justify-center group-hover:bg-yellow-200 transition-colors">
              <Calendar className="h-6 w-6 text-yellow-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Total News</p>
              <p className="text-2xl font-bold text-gray-900">{totalNews.toLocaleString()}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Categories Card */}
      <div className="card p-6 hover:shadow-lg transition-shadow group">
        <div className="flex items-center justify-between">
          <div className="flex items-center flex-1">
            <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center group-hover:bg-purple-200 transition-colors">
              <Filter className="h-6 w-6 text-purple-600" />
            </div>
            <div className="ml-4 flex-1">
              <p className="text-sm font-medium text-gray-600">Categories</p>
              <div className="flex items-center justify-between">
                <p className="text-2xl font-bold text-gray-900">{categoriesCount}</p>
                {showLinkToAnalytics && (
                  <Link
                    to="/news-analytics"
                    className="text-xs text-primary-600 hover:text-primary-700 font-medium"
                  >
                    View Details →
                  </Link>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}


