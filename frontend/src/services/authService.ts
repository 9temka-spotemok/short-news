import {
    AuthResponse,
    LoginRequest,
    RefreshTokenRequest,
    RefreshTokenResponse,
    RegisterRequest,
    User
} from '@/types'
import { ApiService } from './api'

export const authService = {
  // Login with enhanced error handling
  login: async (credentials: LoginRequest): Promise<AuthResponse> => {
    try {
      return await ApiService.login(credentials)
    } catch (error) {
      console.error('Login error:', error)
      throw error
    }
  },

  // Register with enhanced validation
  register: async (userData: RegisterRequest): Promise<AuthResponse> => {
    try {
      return await ApiService.register(userData)
    } catch (error) {
      console.error('Registration error:', error)
      throw error
    }
  },

  // Logout
  logout: async (): Promise<void> => {
    try {
      await ApiService.logout()
    } catch (error) {
      console.error('Logout error:', error)
      // Don't throw error on logout to ensure user is always logged out locally
    }
  },

  // Get current user
  getCurrentUser: async (): Promise<User> => {
    try {
      return await ApiService.getCurrentUser()
    } catch (error) {
      console.error('Get current user error:', error)
      throw error
    }
  },

  // Refresh token
  refreshToken: async (refreshToken: string): Promise<RefreshTokenResponse> => {
    try {
      const refreshData: RefreshTokenRequest = { refresh_token: refreshToken }
      return await ApiService.refreshToken(refreshData)
    } catch (error) {
      console.error('Refresh token error:', error)
      throw error
    }
  },

  // Reset password
  resetPassword: async (_email: string): Promise<{ message: string }> => {
    try {
      // Note: This endpoint might not exist in the current backend
      // You may need to implement it or use a different approach
      throw new Error('Password reset endpoint not implemented')
    } catch (error) {
      console.error('Reset password error:', error)
      throw error
    }
  },

  // Update user profile
  updateProfile: async (userData: Partial<User>): Promise<User> => {
    try {
      return await ApiService.updateUser(userData)
    } catch (error) {
      console.error('Update profile error:', error)
      throw error
    }
  },

  // Verify email (if implemented)
  verifyEmail: async (_token: string): Promise<{ message: string }> => {
    try {
      // Note: This endpoint might not exist in the current backend
      // You may need to implement it
      throw new Error('Email verification endpoint not implemented')
    } catch (error) {
      console.error('Email verification error:', error)
      throw error
    }
  }
}
