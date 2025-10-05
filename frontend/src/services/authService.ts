import { AuthResponse, LoginRequest, RegisterRequest, User } from '@/types'
import api from './api'

export const authService = {
  // Login
  login: async (credentials: LoginRequest): Promise<AuthResponse> => {
    const formData = new FormData()
    formData.append('username', credentials.email)
    formData.append('password', credentials.password)
    
    const response = await api.post('/auth/login', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    })
    
    return response.data
  },

  // Register
  register: async (userData: RegisterRequest): Promise<{ message: string }> => {
    const response = await api.post('/auth/register', userData)
    return response.data
  },

  // Logout
  logout: async (): Promise<{ message: string }> => {
    const response = await api.post('/auth/logout')
    return response.data
  },

  // Get current user
  getCurrentUser: async (): Promise<User> => {
    const response = await api.get('/users/me')
    return response.data
  },

  // Refresh token
  refreshToken: async (refreshToken: string): Promise<AuthResponse> => {
    const response = await api.post('/auth/refresh', { refresh_token: refreshToken })
    return response.data
  },

  // Reset password
  resetPassword: async (email: string): Promise<{ message: string }> => {
    const response = await api.post('/auth/reset-password', { email })
    return response.data
  },
}
