import { authService } from '@/services/authService'
import { useAuthStore } from '@/store/authStore'
import type { LoginRequest, RegisterRequest } from '@/types'
import { Eye, EyeOff, Lock, Mail, User, X } from 'lucide-react'
import { useState } from 'react'
import toast from 'react-hot-toast'

interface AuthModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: (userId: string) => void
}

type AuthMode = 'login' | 'register'

export default function AuthModal({
  isOpen,
  onClose,
  onSuccess
}: AuthModalProps) {
  const { login } = useAuthStore()
  const [mode, setMode] = useState<AuthMode>('login')
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  
  // Login form
  const [loginData, setLoginData] = useState({
    email: '',
    password: ''
  })
  const [loginErrors, setLoginErrors] = useState<Record<string, string>>({})
  
  // Register form
  const [registerData, setRegisterData] = useState({
    email: '',
    password: '',
    full_name: '',
    confirmPassword: ''
  })
  const [registerErrors, setRegisterErrors] = useState<Record<string, string>>({})

  if (!isOpen) return null

  const validateLogin = () => {
    const newErrors: Record<string, string> = {}

    if (!loginData.email.trim()) {
      newErrors.email = 'Email обязателен'
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(loginData.email)) {
      newErrors.email = 'Некорректный email'
    }

    if (!loginData.password) {
      newErrors.password = 'Пароль обязателен'
    }

    setLoginErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const validateRegister = () => {
    const newErrors: Record<string, string> = {}

    if (!registerData.email.trim()) {
      newErrors.email = 'Email обязателен'
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(registerData.email)) {
      newErrors.email = 'Некорректный email'
    }

    if (!registerData.password) {
      newErrors.password = 'Пароль обязателен'
    } else if (registerData.password.length < 8) {
      newErrors.password = 'Пароль должен быть не менее 8 символов'
    }

    if (registerData.password !== registerData.confirmPassword) {
      newErrors.confirmPassword = 'Пароли не совпадают'
    }

    if (!registerData.full_name.trim()) {
      newErrors.full_name = 'Имя обязательно'
    }

    setRegisterErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!validateLogin()) {
      return
    }

    setIsLoading(true)
    try {
      const loginRequest: LoginRequest = {
        email: loginData.email.trim(),
        password: loginData.password
      }

      const response = await authService.login(loginRequest)
      login(response)
      toast.success('Вход выполнен успешно!')
      onSuccess(response.user.id)
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Ошибка при входе'
      toast.error(errorMessage)
      if (errorMessage.includes('email') || errorMessage.includes('пароль')) {
        setLoginErrors({ email: errorMessage, password: errorMessage })
      }
    } finally {
      setIsLoading(false)
    }
  }

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!validateRegister()) {
      return
    }

    setIsLoading(true)
    try {
      const registerRequest: RegisterRequest = {
        email: registerData.email.trim(),
        password: registerData.password,
        full_name: registerData.full_name.trim()
      }

      const response = await authService.register(registerRequest)
      
      // After registration, automatically login
      login(response)
      toast.success('Регистрация успешна!')
      onSuccess(response.user.id)
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Ошибка при регистрации'
      toast.error(errorMessage)
      if (errorMessage.includes('email')) {
        setRegisterErrors({ email: errorMessage })
      }
    } finally {
      setIsLoading(false)
    }
  }

  const resetForms = () => {
    setLoginData({ email: '', password: '' })
    setRegisterData({ email: '', password: '', full_name: '', confirmPassword: '' })
    setLoginErrors({})
    setRegisterErrors({})
    setShowPassword(false)
    setShowConfirmPassword(false)
  }

  const handleModeChange = (newMode: AuthMode) => {
    resetForms()
    setMode(newMode)
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6 relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-gray-400 hover:text-gray-600"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Tabs */}
        <div className="flex gap-4 mb-6 border-b border-gray-200">
          <button
            onClick={() => handleModeChange('login')}
            className={`flex-1 pb-3 text-center font-medium transition-colors ${
              mode === 'login'
                ? 'text-primary-600 border-b-2 border-primary-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            Войти
          </button>
          <button
            onClick={() => handleModeChange('register')}
            className={`flex-1 pb-3 text-center font-medium transition-colors ${
              mode === 'register'
                ? 'text-primary-600 border-b-2 border-primary-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            Зарегистрироваться
          </button>
        </div>

        {/* Login Form */}
        {mode === 'login' && (
          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <h2 className="text-2xl font-bold text-gray-900 mb-2">
                Вход в систему
              </h2>
              <p className="text-gray-600 mb-6">
                Войдите, чтобы продолжить работу с платформой
              </p>
            </div>

            <div>
              <label htmlFor="login-email" className="block text-sm font-medium text-gray-700 mb-1">
                Email
              </label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                <input
                  id="login-email"
                  type="email"
                  value={loginData.email}
                  onChange={(e) => {
                    setLoginData({ ...loginData, email: e.target.value })
                    setLoginErrors({ ...loginErrors, email: '' })
                  }}
                  className={`w-full pl-10 pr-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 ${
                    loginErrors.email ? 'border-red-500' : 'border-gray-300'
                  }`}
                  placeholder="your@email.com"
                  disabled={isLoading}
                />
              </div>
              {loginErrors.email && (
                <p className="mt-1 text-sm text-red-600">{loginErrors.email}</p>
              )}
            </div>

            <div>
              <label htmlFor="login-password" className="block text-sm font-medium text-gray-700 mb-1">
                Пароль
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                <input
                  id="login-password"
                  type={showPassword ? 'text' : 'password'}
                  value={loginData.password}
                  onChange={(e) => {
                    setLoginData({ ...loginData, password: e.target.value })
                    setLoginErrors({ ...loginErrors, password: '' })
                  }}
                  className={`w-full pl-10 pr-10 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 ${
                    loginErrors.password ? 'border-red-500' : 'border-gray-300'
                  }`}
                  placeholder="••••••••"
                  disabled={isLoading}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-500"
                >
                  {showPassword ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </button>
              </div>
              {loginErrors.password && (
                <p className="mt-1 text-sm text-red-600">{loginErrors.password}</p>
              )}
            </div>

            <div className="flex gap-3 pt-4">
              <button
                type="button"
                onClick={onClose}
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors"
                disabled={isLoading}
              >
                Отмена
              </button>
              <button
                type="submit"
                disabled={isLoading}
                className="flex-1 bg-primary-600 text-white px-4 py-2 rounded-lg hover:bg-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? 'Вход...' : 'Войти'}
              </button>
            </div>
          </form>
        )}

        {/* Register Form */}
        {mode === 'register' && (
          <form onSubmit={handleRegister} className="space-y-4">
            <div>
              <h2 className="text-2xl font-bold text-gray-900 mb-2">
                Регистрация
              </h2>
              <p className="text-gray-600 mb-6">
                Создайте аккаунт, чтобы продолжить работу с платформой
              </p>
            </div>

            <div>
              <label htmlFor="register-full_name" className="block text-sm font-medium text-gray-700 mb-1">
                Имя
              </label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                <input
                  id="register-full_name"
                  type="text"
                  value={registerData.full_name}
                  onChange={(e) => {
                    setRegisterData({ ...registerData, full_name: e.target.value })
                    setRegisterErrors({ ...registerErrors, full_name: '' })
                  }}
                  className={`w-full pl-10 pr-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 ${
                    registerErrors.full_name ? 'border-red-500' : 'border-gray-300'
                  }`}
                  placeholder="Иван Иванов"
                  disabled={isLoading}
                />
              </div>
              {registerErrors.full_name && (
                <p className="mt-1 text-sm text-red-600">{registerErrors.full_name}</p>
              )}
            </div>

            <div>
              <label htmlFor="register-email" className="block text-sm font-medium text-gray-700 mb-1">
                Email
              </label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                <input
                  id="register-email"
                  type="email"
                  value={registerData.email}
                  onChange={(e) => {
                    setRegisterData({ ...registerData, email: e.target.value })
                    setRegisterErrors({ ...registerErrors, email: '' })
                  }}
                  className={`w-full pl-10 pr-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 ${
                    registerErrors.email ? 'border-red-500' : 'border-gray-300'
                  }`}
                  placeholder="your@email.com"
                  disabled={isLoading}
                />
              </div>
              {registerErrors.email && (
                <p className="mt-1 text-sm text-red-600">{registerErrors.email}</p>
              )}
            </div>

            <div>
              <label htmlFor="register-password" className="block text-sm font-medium text-gray-700 mb-1">
                Пароль
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                <input
                  id="register-password"
                  type={showPassword ? 'text' : 'password'}
                  value={registerData.password}
                  onChange={(e) => {
                    setRegisterData({ ...registerData, password: e.target.value })
                    setRegisterErrors({ ...registerErrors, password: '' })
                  }}
                  className={`w-full pl-10 pr-10 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 ${
                    registerErrors.password ? 'border-red-500' : 'border-gray-300'
                  }`}
                  placeholder="••••••••"
                  disabled={isLoading}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-500"
                >
                  {showPassword ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </button>
              </div>
              {registerErrors.password && (
                <p className="mt-1 text-sm text-red-600">{registerErrors.password}</p>
              )}
            </div>

            <div>
              <label htmlFor="register-confirmPassword" className="block text-sm font-medium text-gray-700 mb-1">
                Подтвердите пароль
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                <input
                  id="register-confirmPassword"
                  type={showConfirmPassword ? 'text' : 'password'}
                  value={registerData.confirmPassword}
                  onChange={(e) => {
                    setRegisterData({ ...registerData, confirmPassword: e.target.value })
                    setRegisterErrors({ ...registerErrors, confirmPassword: '' })
                  }}
                  className={`w-full pl-10 pr-10 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 ${
                    registerErrors.confirmPassword ? 'border-red-500' : 'border-gray-300'
                  }`}
                  placeholder="••••••••"
                  disabled={isLoading}
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-500"
                >
                  {showConfirmPassword ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </button>
              </div>
              {registerErrors.confirmPassword && (
                <p className="mt-1 text-sm text-red-600">{registerErrors.confirmPassword}</p>
              )}
            </div>

            <div className="flex gap-3 pt-4">
              <button
                type="button"
                onClick={onClose}
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors"
                disabled={isLoading}
              >
                Отмена
              </button>
              <button
                type="submit"
                disabled={isLoading}
                className="flex-1 bg-primary-600 text-white px-4 py-2 rounded-lg hover:bg-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? 'Регистрация...' : 'Зарегистрироваться'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}












