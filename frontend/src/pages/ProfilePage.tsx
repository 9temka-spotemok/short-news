import { useAuthStore } from '@/store/authStore'
import { format } from 'date-fns'
import { ru } from 'date-fns/locale'
import { Calendar, CheckCircle, Mail, User, XCircle } from 'lucide-react'
import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

export default function ProfilePage() {
  const { user, isAuthenticated } = useAuthStore()
  const navigate = useNavigate()

  useEffect(() => {
    console.log('ProfilePage - isAuthenticated:', isAuthenticated)
    console.log('ProfilePage - user:', user)
    
    // Если не авторизован, перенаправляем на логин
    if (!isAuthenticated) {
      console.log('Redirecting to login - not authenticated')
      navigate('/login')
    }
  }, [isAuthenticated, navigate, user])

  // Показываем загрузку только если авторизован но user еще не загрузился
  if (isAuthenticated && !user) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
          <p className="mt-4 text-gray-500">Загрузка профиля...</p>
        </div>
      </div>
    )
  }

  // Если нет пользователя и не авторизован, ничего не показываем (идет редирект)
  if (!user) {
    return null
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Page Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Личный кабинет</h1>
          <p className="mt-2 text-gray-600">Управление профилем и настройками</p>
        </div>

        {/* Profile Card */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
          {/* Header with Avatar */}
          <div className="bg-gradient-to-r from-primary-600 to-primary-700 px-6 py-8">
            <div className="flex items-center space-x-4">
              <div className="w-20 h-20 bg-white rounded-full flex items-center justify-center">
                <User className="h-10 w-10 text-primary-600" />
              </div>
              <div>
                <h2 className="text-2xl font-bold text-white">{user.full_name}</h2>
                <p className="text-primary-100">{user.email}</p>
              </div>
            </div>
          </div>

          {/* User Information */}
          <div className="px-6 py-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Информация о профиле</h3>
            
            <div className="space-y-4">
              {/* Email */}
              <div className="flex items-start space-x-3 p-4 bg-gray-50 rounded-lg">
                <Mail className="h-5 w-5 text-gray-400 mt-0.5" />
                <div className="flex-1">
                  <p className="text-sm font-medium text-gray-700">Email адрес</p>
                  <p className="text-sm text-gray-900 mt-1">{user.email}</p>
                </div>
              </div>

              {/* Full Name */}
              <div className="flex items-start space-x-3 p-4 bg-gray-50 rounded-lg">
                <User className="h-5 w-5 text-gray-400 mt-0.5" />
                <div className="flex-1">
                  <p className="text-sm font-medium text-gray-700">Полное имя</p>
                  <p className="text-sm text-gray-900 mt-1">{user.full_name}</p>
                </div>
              </div>

              {/* Status */}
              <div className="flex items-start space-x-3 p-4 bg-gray-50 rounded-lg">
                {user.is_active ? (
                  <CheckCircle className="h-5 w-5 text-green-500 mt-0.5" />
                ) : (
                  <XCircle className="h-5 w-5 text-red-500 mt-0.5" />
                )}
                <div className="flex-1">
                  <p className="text-sm font-medium text-gray-700">Статус аккаунта</p>
                  <p className={`text-sm mt-1 ${user.is_active ? 'text-green-600' : 'text-red-600'}`}>
                    {user.is_active ? 'Активен' : 'Неактивен'}
                  </p>
                </div>
              </div>

              {/* Verification Status */}
              <div className="flex items-start space-x-3 p-4 bg-gray-50 rounded-lg">
                {user.is_verified ? (
                  <CheckCircle className="h-5 w-5 text-green-500 mt-0.5" />
                ) : (
                  <XCircle className="h-5 w-5 text-yellow-500 mt-0.5" />
                )}
                <div className="flex-1">
                  <p className="text-sm font-medium text-gray-700">Верификация email</p>
                  <p className={`text-sm mt-1 ${user.is_verified ? 'text-green-600' : 'text-yellow-600'}`}>
                    {user.is_verified ? 'Подтвержден' : 'Не подтвержден'}
                  </p>
                </div>
              </div>

              {/* Created Date */}
              <div className="flex items-start space-x-3 p-4 bg-gray-50 rounded-lg">
                <Calendar className="h-5 w-5 text-gray-400 mt-0.5" />
                <div className="flex-1">
                  <p className="text-sm font-medium text-gray-700">Дата регистрации</p>
                  <p className="text-sm text-gray-900 mt-1">
                    {format(new Date(user.created_at), 'dd MMMM yyyy, HH:mm', { locale: ru })}
                  </p>
                </div>
              </div>

              {/* User ID */}
              <div className="flex items-start space-x-3 p-4 bg-gray-50 rounded-lg">
                <User className="h-5 w-5 text-gray-400 mt-0.5" />
                <div className="flex-1">
                  <p className="text-sm font-medium text-gray-700">ID пользователя</p>
                  <p className="text-sm text-gray-500 mt-1 font-mono">{user.id}</p>
                </div>
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="px-6 py-4 bg-gray-50 border-t border-gray-200">
            <div className="flex items-center justify-between">
              <p className="text-sm text-gray-500">
                Последнее обновление: {format(new Date(user.updated_at), 'dd MMMM yyyy, HH:mm', { locale: ru })}
              </p>
            </div>
          </div>
        </div>

        {/* Additional Info Card */}
        <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-start space-x-3">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="flex-1">
              <h3 className="text-sm font-medium text-blue-900">Информация</h3>
              <p className="mt-1 text-sm text-blue-700">
                Здесь отображается основная информация о вашем профиле. 
                Для изменения настроек уведомлений и предпочтений перейдите в раздел "Настройки".
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

