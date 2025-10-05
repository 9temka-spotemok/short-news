import { Bell, Filter, Shield, User } from 'lucide-react'
import { useState } from 'react'

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState('profile')

  const tabs = [
    { id: 'profile', label: 'Профиль', icon: User },
    { id: 'notifications', label: 'Уведомления', icon: Bell },
    { id: 'preferences', label: 'Предпочтения', icon: Filter },
    { id: 'security', label: 'Безопасность', icon: Shield },
  ]

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Настройки
          </h1>
          <p className="text-gray-600">
            Управление профилем и предпочтениями
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          {/* Sidebar */}
          <div className="lg:col-span-1">
            <nav className="space-y-1">
              {tabs.map((tab) => {
                const Icon = tab.icon
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`w-full flex items-center px-3 py-2 text-sm font-medium rounded-md ${
                      activeTab === tab.id
                        ? 'bg-primary-100 text-primary-700'
                        : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                    }`}
                  >
                    <Icon className="mr-3 h-5 w-5" />
                    {tab.label}
                  </button>
                )
              })}
            </nav>
          </div>

          {/* Content */}
          <div className="lg:col-span-3">
            {activeTab === 'profile' && (
              <div className="space-y-6">
                <div className="card p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">
                    Информация профиля
                  </h3>
                  <form className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Имя
                        </label>
                        <input
                          type="text"
                          defaultValue="Иван Иванов"
                          className="input"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Email
                        </label>
                        <input
                          type="email"
                          defaultValue="ivan@example.com"
                          className="input"
                        />
                      </div>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        О себе
                      </label>
                      <textarea
                        rows={3}
                        defaultValue="Исследователь ИИ и машинного обучения"
                        className="input"
                      />
                    </div>
                    <button className="btn btn-primary btn-md">
                      Сохранить изменения
                    </button>
                  </form>
                </div>

                <div className="card p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">
                    Аватар
                  </h3>
                  <div className="flex items-center space-x-4">
                    <div className="w-16 h-16 bg-primary-600 rounded-full flex items-center justify-center">
                      <span className="text-white font-bold text-lg">ИИ</span>
                    </div>
                    <div>
                      <button className="btn btn-outline btn-sm">
                        Изменить аватар
                      </button>
                      <p className="text-sm text-gray-500 mt-1">
                        JPG, PNG или GIF, максимум 2MB
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'notifications' && (
              <div className="space-y-6">
                <div className="card p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">
                    Настройки уведомлений
                  </h3>
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <h4 className="text-sm font-medium text-gray-900">
                          Email уведомления
                        </h4>
                        <p className="text-sm text-gray-500">
                          Получать уведомления на email
                        </p>
                      </div>
                      <input
                        type="checkbox"
                        defaultChecked
                        className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                      />
                    </div>
                    <div className="flex items-center justify-between">
                      <div>
                        <h4 className="text-sm font-medium text-gray-900">
                          Ежедневные дайджесты
                        </h4>
                        <p className="text-sm text-gray-500">
                          Получать ежедневные дайджесты новостей
                        </p>
                      </div>
                      <input
                        type="checkbox"
                        defaultChecked
                        className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                      />
                    </div>
                    <div className="flex items-center justify-between">
                      <div>
                        <h4 className="text-sm font-medium text-gray-900">
                          Критические новости
                        </h4>
                        <p className="text-sm text-gray-500">
                          Мгновенные уведомления о важных новостях
                        </p>
                      </div>
                      <input
                        type="checkbox"
                        defaultChecked
                        className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                      />
                    </div>
                  </div>
                </div>

                <div className="card p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">
                    Частота уведомлений
                  </h3>
                  <div className="space-y-3">
                    {[
                      { value: 'realtime', label: 'В реальном времени' },
                      { value: 'daily', label: 'Ежедневно' },
                      { value: 'weekly', label: 'Еженедельно' },
                      { value: 'never', label: 'Никогда' },
                    ].map((option) => (
                      <label key={option.value} className="flex items-center">
                        <input
                          type="radio"
                          name="frequency"
                          value={option.value}
                          defaultChecked={option.value === 'daily'}
                          className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300"
                        />
                        <span className="ml-2 text-sm text-gray-700">
                          {option.label}
                        </span>
                      </label>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'preferences' && (
              <div className="space-y-6">
                <div className="card p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">
                    Отслеживаемые компании
                  </h3>
                  <div className="space-y-3">
                    {[
                      { name: 'OpenAI', checked: true },
                      { name: 'Anthropic', checked: true },
                      { name: 'Google', checked: false },
                      { name: 'Meta', checked: true },
                      { name: 'Microsoft', checked: false },
                    ].map((company) => (
                      <label key={company.name} className="flex items-center">
                        <input
                          type="checkbox"
                          defaultChecked={company.checked}
                          className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                        />
                        <span className="ml-2 text-sm text-gray-700">
                          {company.name}
                        </span>
                      </label>
                    ))}
                  </div>
                </div>

                <div className="card p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">
                    Интересующие категории
                  </h3>
                  <div className="grid grid-cols-2 gap-3">
                    {[
                      'Product Updates',
                      'Pricing Changes',
                      'Strategic Announcements',
                      'Technical Updates',
                      'Funding News',
                      'Research Papers',
                    ].map((category) => (
                      <label key={category} className="flex items-center">
                        <input
                          type="checkbox"
                          defaultChecked
                          className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                        />
                        <span className="ml-2 text-sm text-gray-700">
                          {category}
                        </span>
                      </label>
                    ))}
                  </div>
                </div>

                <div className="card p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">
                    Ключевые слова
                  </h3>
                  <div>
                    <input
                      type="text"
                      placeholder="Добавить ключевое слово"
                      className="input mb-3"
                    />
                    <div className="flex flex-wrap gap-2">
                      {['GPT-5', 'Machine Learning', 'AI Safety', 'LLM'].map((keyword) => (
                        <span
                          key={keyword}
                          className="badge badge-gray flex items-center"
                        >
                          {keyword}
                          <button className="ml-1 text-gray-400 hover:text-gray-600">
                            ×
                          </button>
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'security' && (
              <div className="space-y-6">
                <div className="card p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">
                    Изменить пароль
                  </h3>
                  <form className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Текущий пароль
                      </label>
                      <input type="password" className="input" />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Новый пароль
                      </label>
                      <input type="password" className="input" />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Подтвердите пароль
                      </label>
                      <input type="password" className="input" />
                    </div>
                    <button className="btn btn-primary btn-md">
                      Изменить пароль
                    </button>
                  </form>
                </div>

                <div className="card p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">
                    Двухфакторная аутентификация
                  </h3>
                  <p className="text-gray-600 mb-4">
                    Добавьте дополнительный уровень безопасности к вашему аккаунту
                  </p>
                  <button className="btn btn-outline btn-md">
                    Включить 2FA
                  </button>
                </div>

                <div className="card p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">
                    Активные сессии
                  </h3>
                  <div className="space-y-3">
                    <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                      <div>
                        <p className="text-sm font-medium text-gray-900">Текущая сессия</p>
                        <p className="text-xs text-gray-500">Chrome на Windows • Москва, Россия</p>
                      </div>
                      <span className="badge badge-success">Активна</span>
                    </div>
                    <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                      <div>
                        <p className="text-sm font-medium text-gray-900">Мобильное приложение</p>
                        <p className="text-xs text-gray-500">iPhone • Москва, Россия</p>
                      </div>
                      <button className="text-red-600 hover:text-red-700 text-sm">
                        Завершить
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
