import { Calendar, Filter, Search } from 'lucide-react'
import { useState } from 'react'

export default function NewsPage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCategory, setSelectedCategory] = useState('')

  const categories = [
    { value: '', label: 'Все категории' },
    { value: 'product_update', label: 'Обновления продуктов' },
    { value: 'pricing_change', label: 'Изменения цен' },
    { value: 'strategic_announcement', label: 'Стратегические анонсы' },
    { value: 'technical_update', label: 'Технические обновления' },
    { value: 'funding_news', label: 'Новости о финансировании' },
  ]

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

      {/* News Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {/* Sample News Card */}
        <div className="card p-6 hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between mb-3">
            <span className="badge badge-primary">Product Update</span>
            <span className="text-sm text-gray-500">2 часа назад</span>
          </div>
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            OpenAI анонсирует GPT-5
          </h3>
          <p className="text-gray-600 text-sm mb-4">
            Компания OpenAI представила новую версию своей языковой модели с улучшенными возможностями...
          </p>
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-500">OpenAI</span>
            <a href="#" className="text-primary-600 hover:text-primary-700 text-sm font-medium">
              Читать далее →
            </a>
          </div>
        </div>

        {/* More sample cards would go here */}
        {[1, 2, 3, 4, 5, 6].map((i) => (
          <div key={i} className="card p-6 hover:shadow-md transition-shadow">
            <div className="flex items-center justify-between mb-3">
              <span className="badge badge-gray">Loading...</span>
              <span className="text-sm text-gray-500">...</span>
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              Загрузка новостей...
            </h3>
            <p className="text-gray-600 text-sm mb-4">
              Подключение к API для получения актуальных новостей...
            </p>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-500">...</span>
              <span className="text-gray-400 text-sm">...</span>
            </div>
          </div>
        ))}
      </div>

      {/* Load More Button */}
      <div className="text-center mt-8">
        <button className="btn btn-outline btn-md">
          Загрузить еще
        </button>
      </div>
    </div>
  )
}
