import { authService } from '@/services/authService'
import { useAuthStore } from '@/store/authStore'
import type { LoginRequest, RegisterRequest } from '@/types'
import { Eye, EyeOff, Lock, Mail, User, X } from 'lucide-react'
import { useState } from 'react'
import toast from 'react-hot-toast'

interface OnboardingRegisterModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: (userId?: string) => void
}

type AuthMode = 'register' | 'login'

export default function OnboardingRegisterModal({
  isOpen,
  onClose,
  onSuccess
}: OnboardingRegisterModalProps) {
  const { login } = useAuthStore()
  const [mode, setMode] = useState<AuthMode>('register')
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [agreeToTerms, setAgreeToTerms] = useState(false)
  
  // Register form
  const [registerData, setRegisterData] = useState({
    email: '',
    password: '',
    full_name: '',
    confirmPassword: ''
  })
  const [registerErrors, setRegisterErrors] = useState<Record<string, string>>({})
  
  // Login form
  const [loginData, setLoginData] = useState({
    email: '',
    password: ''
  })
  const [loginErrors, setLoginErrors] = useState<Record<string, string>>({})

  if (!isOpen) return null

  const validateRegister = () => {
    const newErrors: Record<string, string> = {}

    if (!registerData.full_name.trim()) {
      newErrors.full_name = 'Full name is required'
    }

    if (!registerData.email.trim()) {
      newErrors.email = 'Email is required'
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(registerData.email)) {
      newErrors.email = 'Invalid email address'
    }

    if (!registerData.password) {
      newErrors.password = 'Password is required'
    } else if (registerData.password.length < 8) {
      newErrors.password = 'Password must be at least 8 characters'
    }

    if (registerData.password !== registerData.confirmPassword) {
      newErrors.confirmPassword = 'Passwords do not match'
    }

    if (!agreeToTerms) {
      newErrors.terms = 'You must agree to the terms of service'
    }

    setRegisterErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const validateLogin = () => {
    const newErrors: Record<string, string> = {}

    if (!loginData.email.trim()) {
      newErrors.email = 'Email is required'
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(loginData.email)) {
      newErrors.email = 'Invalid email address'
    }

    if (!loginData.password) {
      newErrors.password = 'Password is required'
    }

    setLoginErrors(newErrors)
    return Object.keys(newErrors).length === 0
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
      
      // Set auth state
      login(response)

      toast.success('Registration successful!')
      onSuccess(response.user.id)
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Registration error'
      toast.error(errorMessage)
      if (errorMessage.includes('email')) {
        setRegisterErrors({ email: errorMessage })
      }
    } finally {
      setIsLoading(false)
    }
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
      toast.success('Sign in successful!')
      onSuccess()
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Sign in error'
      toast.error(errorMessage)
      if (errorMessage.includes('email') || errorMessage.includes('password')) {
        setLoginErrors({ email: errorMessage, password: errorMessage })
      }
    } finally {
      setIsLoading(false)
    }
  }

  const resetForms = () => {
    setRegisterData({ email: '', password: '', full_name: '', confirmPassword: '' })
    setLoginData({ email: '', password: '' })
    setRegisterErrors({})
    setLoginErrors({})
    setShowPassword(false)
    setShowConfirmPassword(false)
    setAgreeToTerms(false)
  }

  const handleModeChange = (newMode: AuthMode) => {
    resetForms()
    setMode(newMode)
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-8 relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-gray-400 hover:text-gray-600 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Logo */}
        <div className="flex justify-center mb-6">
          <div className="w-16 h-16 bg-primary-600 rounded-full flex items-center justify-center">
            <span className="text-white font-bold text-2xl">AI</span>
          </div>
        </div>

        {/* Register Form */}
        {mode === 'register' && (
          <>
            <h2 className="text-3xl font-bold text-gray-900 text-center mb-2">
              Create Account
            </h2>
            <p className="text-gray-600 text-center mb-6">
              Or{' '}
              <button
                type="button"
                onClick={() => handleModeChange('login')}
                className="text-primary-600 hover:text-primary-700 font-medium"
              >
                sign in to existing account
              </button>
            </p>

            <form onSubmit={handleRegister} className="space-y-4">
              <div>
                <label htmlFor="register-full_name" className="block text-sm font-medium text-gray-700 mb-1">
                  Full Name
                </label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
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
                    placeholder="John Doe"
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
                  <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
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
                  Password
                </label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
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
                      <EyeOff className="h-5 w-5" />
                    ) : (
                      <Eye className="h-5 w-5" />
                    )}
                  </button>
                </div>
                {registerErrors.password && (
                  <p className="mt-1 text-sm text-red-600">{registerErrors.password}</p>
                )}
              </div>

              <div>
                <label htmlFor="register-confirmPassword" className="block text-sm font-medium text-gray-700 mb-1">
                  Confirm Password
                </label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
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
                      <EyeOff className="h-5 w-5" />
                    ) : (
                      <Eye className="h-5 w-5" />
                    )}
                  </button>
                </div>
                {registerErrors.confirmPassword && (
                  <p className="mt-1 text-sm text-red-600">{registerErrors.confirmPassword}</p>
                )}
              </div>

              <div className="flex items-start gap-2">
                <input
                  type="checkbox"
                  id="terms"
                  checked={agreeToTerms}
                  onChange={(e) => {
                    setAgreeToTerms(e.target.checked)
                    setRegisterErrors({ ...registerErrors, terms: '' })
                  }}
                  className="mt-1 w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
                />
                <label htmlFor="terms" className="text-sm text-gray-700">
                  I agree to the{' '}
                  <a href="#" className="text-primary-600 hover:text-primary-700">
                    terms of service
                  </a>{' '}
                  and{' '}
                  <a href="#" className="text-primary-600 hover:text-primary-700">
                    privacy policy
                  </a>
                </label>
              </div>
              {registerErrors.terms && (
                <p className="text-sm text-red-600">{registerErrors.terms}</p>
              )}

              <button
                type="submit"
                disabled={isLoading}
                className="w-full bg-primary-600 text-white px-4 py-3 rounded-lg hover:bg-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-medium"
              >
                {isLoading ? 'Creating Account...' : 'Create Account'}
              </button>
            </form>
          </>
        )}

        {/* Login Form */}
        {mode === 'login' && (
          <>
            <h2 className="text-3xl font-bold text-gray-900 text-center mb-2">
              Sign In to Your Account
            </h2>
            <p className="text-gray-600 text-center mb-6">
              Or{' '}
              <button
                type="button"
                onClick={() => handleModeChange('register')}
                className="text-primary-600 hover:text-primary-700 font-medium"
              >
                create a new account
              </button>
            </p>

            <form onSubmit={handleLogin} className="space-y-4">
              <div>
                <label htmlFor="login-email" className="block text-sm font-medium text-gray-700 mb-1">
                  Email
                </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
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
                  Password
                </label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
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
                      <EyeOff className="h-5 w-5" />
                    ) : (
                      <Eye className="h-5 w-5" />
                    )}
                  </button>
                </div>
                {loginErrors.password && (
                  <p className="mt-1 text-sm text-red-600">{loginErrors.password}</p>
                )}
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="w-full bg-primary-600 text-white px-4 py-3 rounded-lg hover:bg-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-medium"
              >
                {isLoading ? 'Signing In...' : 'Sign In'}
              </button>
            </form>
          </>
        )}
      </div>
    </div>
  )
}
