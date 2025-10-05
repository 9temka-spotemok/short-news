import { ArrowRight, Bell, Filter, TrendingUp, Zap } from 'lucide-react'
import { Link } from 'react-router-dom'

export default function HomePage() {
  return (
    <div className="bg-white">
      {/* Hero Section */}
      <div className="relative overflow-hidden">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
          <div className="text-center">
            <h1 className="text-4xl md:text-6xl font-bold text-gray-900 mb-6">
              AI Competitor
              <span className="text-primary-600"> Insight Hub</span>
            </h1>
            <p className="text-xl text-gray-600 mb-8 max-w-3xl mx-auto">
              Интеллектуальная платформа для мониторинга новостей из мира ИИ-индустрии. 
              Получайте персонализированные дайджесты и будьте в курсе всех важных событий.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link to="/register" className="btn btn-primary btn-lg">
                Начать бесплатно
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
              <Link to="/news" className="btn btn-outline btn-lg">
                Посмотреть новости
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Features Section */}
      <div className="py-24 bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-gray-900 mb-4">
              Почему выбирают shot-news?
            </h2>
            <p className="text-xl text-gray-600 max-w-2xl mx-auto">
              Мы используем современные технологии ИИ для предоставления 
              наиболее релевантной информации о развитии индустрии.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            <div className="text-center">
              <div className="w-16 h-16 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <TrendingUp className="h-8 w-8 text-primary-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Анализ трендов
              </h3>
              <p className="text-gray-600">
                Отслеживайте ключевые тренды и изменения в ИИ-индустрии
              </p>
            </div>

            <div className="text-center">
              <div className="w-16 h-16 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Filter className="h-8 w-8 text-primary-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Умная фильтрация
              </h3>
              <p className="text-gray-600">
                ИИ-алгоритмы отбирают только релевантные для вас новости
              </p>
            </div>

            <div className="text-center">
              <div className="w-16 h-16 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Bell className="h-8 w-8 text-primary-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Персонализация
              </h3>
              <p className="text-gray-600">
                Получайте дайджесты, адаптированные под ваши интересы
              </p>
            </div>

            <div className="text-center">
              <div className="w-16 h-16 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Zap className="h-8 w-8 text-primary-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Быстро и точно
              </h3>
              <p className="text-gray-600">
                Обновления в реальном времени с высокой точностью
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Stats Section */}
      <div className="py-24 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 text-center">
            <div>
              <div className="text-4xl font-bold text-primary-600 mb-2">50+</div>
              <div className="text-gray-600">Отслеживаемых компаний</div>
            </div>
            <div>
              <div className="text-4xl font-bold text-primary-600 mb-2">1000+</div>
              <div className="text-gray-600">Новостей в день</div>
            </div>
            <div>
              <div className="text-4xl font-bold text-primary-600 mb-2">99.5%</div>
              <div className="text-gray-600">Точность классификации</div>
            </div>
          </div>
        </div>
      </div>

      {/* CTA Section */}
      <div className="py-24 bg-primary-600">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl font-bold text-white mb-4">
            Готовы начать?
          </h2>
          <p className="text-xl text-primary-100 mb-8 max-w-2xl mx-auto">
            Присоединяйтесь к сообществу профессионалов ИИ-индустрии 
            и получайте актуальную информацию первыми.
          </p>
          <Link to="/register" className="btn bg-white text-primary-600 hover:bg-gray-100 btn-lg">
            Создать аккаунт
            <ArrowRight className="ml-2 h-4 w-4" />
          </Link>
        </div>
      </div>
    </div>
  )
}
