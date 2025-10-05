import { Bell, Calendar, Filter, Search, TrendingUp } from 'lucide-react'
import { useState } from 'react'

export default function DashboardPage() {
  const [activeTab, setActiveTab] = useState('overview')

  const tabs = [
    { id: 'overview', label: 'Обзор' },
    { id: 'news', label: 'Новости' },
    { id: 'digest', label: 'Дайджесты' },
    { id: 'analytics', label: 'Аналитика' },
  ]

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
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <div className="card p-6">
                <div className="flex items-center">
                  <div className="w-12 h-12 bg-primary-100 rounded-lg flex items-center justify-center">
                    <TrendingUp className="h-6 w-6 text-primary-600" />
                  </div>
                  <div className="ml-4">
                    <p className="text-sm font-medium text-gray-600">Отслеживаемых компаний</p>
                    <p className="text-2xl font-bold text-gray-900">50+</p>
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
                    <p className="text-2xl font-bold text-gray-900">127</p>
                  </div>
                </div>
              </div>

              <div className="card p-6">
                <div className="flex items-center">
                  <div className="w-12 h-12 bg-yellow-100 rounded-lg flex items-center justify-center">
                    <Calendar className="h-6 w-6 text-yellow-600" />
                  </div>
                  <div className="ml-4">
                    <p className="text-sm font-medium text-gray-600">Дайджестов создано</p>
                    <p className="text-2xl font-bold text-gray-900">23</p>
                  </div>
                </div>
              </div>

              <div className="card p-6">
                <div className="flex items-center">
                  <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
                    <Filter className="h-6 w-6 text-purple-600" />
                  </div>
                  <div className="ml-4">
                    <p className="text-sm font-medium text-gray-600">Активных фильтров</p>
                    <p className="text-2xl font-bold text-gray-900">8</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Recent News */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              <div className="card p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">
                  Последние новости
                </h3>
                <div className="space-y-4">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="flex items-start space-x-3">
                      <div className="w-2 h-2 bg-primary-600 rounded-full mt-2"></div>
                      <div className="flex-1">
                        <p className="text-sm text-gray-900">
                          OpenAI анонсирует новые возможности для GPT-4
                        </p>
                        <p className="text-xs text-gray-500 mt-1">2 часа назад</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="card p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">
                  Популярные категории
                </h3>
                <div className="space-y-3">
                  {[
                    { name: 'Product Updates', count: 45, percentage: 35 },
                    { name: 'Technical Updates', count: 32, percentage: 25 },
                    { name: 'Strategic Announcements', count: 28, percentage: 22 },
                    { name: 'Funding News', count: 18, percentage: 14 },
                  ].map((category) => (
                    <div key={category.name} className="flex items-center justify-between">
                      <span className="text-sm text-gray-700">{category.name}</span>
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
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'news' && (
          <div className="space-y-6">
            {/* News Filters */}
            <div className="card p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900">Фильтры новостей</h3>
                <button className="btn btn-outline btn-sm">
                  <Search className="h-4 w-4 mr-2" />
                  Поиск
                </button>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <select className="input">
                  <option>Все категории</option>
                  <option>Product Updates</option>
                  <option>Technical Updates</option>
                </select>
                <select className="input">
                  <option>Все компании</option>
                  <option>OpenAI</option>
                  <option>Anthropic</option>
                  <option>Google</option>
                </select>
                <input type="date" className="input" />
              </div>
            </div>

            {/* News List */}
            <div className="space-y-4">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="card p-6">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-2 mb-2">
                        <span className="badge badge-primary">Product Update</span>
                        <span className="text-sm text-gray-500">OpenAI</span>
                        <span className="text-sm text-gray-500">•</span>
                        <span className="text-sm text-gray-500">2 часа назад</span>
                      </div>
                      <h4 className="text-lg font-semibold text-gray-900 mb-2">
                        OpenAI анонсирует GPT-5 с улучшенными возможностями
                      </h4>
                      <p className="text-gray-600 text-sm mb-3">
                        Компания OpenAI представила новую версию своей языковой модели 
                        с значительными улучшениями в области понимания контекста...
                      </p>
                      <div className="flex items-center space-x-4">
                        <button className="text-primary-600 hover:text-primary-700 text-sm font-medium">
                          Читать далее
                        </button>
                        <button className="text-gray-500 hover:text-gray-700 text-sm">
                          Добавить в избранное
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
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
              <div className="space-y-4">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                    <div>
                      <h4 className="font-medium text-gray-900">Ежедневный дайджест</h4>
                      <p className="text-sm text-gray-600">5 октября 2025 • 23 новости</p>
                    </div>
                    <button className="btn btn-outline btn-sm">
                      Просмотреть
                    </button>
                  </div>
                ))}
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
                Анализ вашей активности и трендов в ИИ-индустрии
              </p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="p-4 bg-gray-50 rounded-lg">
                  <h4 className="font-medium text-gray-900 mb-2">Активность за месяц</h4>
                  <p className="text-2xl font-bold text-primary-600">1,247</p>
                  <p className="text-sm text-gray-600">просмотренных новостей</p>
                </div>
                <div className="p-4 bg-gray-50 rounded-lg">
                  <h4 className="font-medium text-gray-900 mb-2">Избранные новости</h4>
                  <p className="text-2xl font-bold text-green-600">89</p>
                  <p className="text-sm text-gray-600">добавлено в избранное</p>
                </div>
              </div>
            </div>

            <div className="card p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">
                Тренды по категориям
              </h3>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-700">Product Updates</span>
                  <div className="flex items-center space-x-2">
                    <div className="w-32 h-2 bg-gray-200 rounded-full">
                      <div className="w-3/4 h-2 bg-primary-600 rounded-full"></div>
                    </div>
                    <span className="text-xs text-gray-500">75%</span>
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-700">Technical Updates</span>
                  <div className="flex items-center space-x-2">
                    <div className="w-32 h-2 bg-gray-200 rounded-full">
                      <div className="w-1/2 h-2 bg-green-600 rounded-full"></div>
                    </div>
                    <span className="text-xs text-gray-500">50%</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
