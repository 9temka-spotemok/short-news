import { useAuthStore } from '@/store/authStore'
import type {
    ApiResponse,
    AuthResponse,
    Company,
    LoginRequest,
    NewsCategoryInfo,
    NewsFilter,
    NewsItem,
    NewsListResponse,
    NewsSearchResponse,
    NewsStats,
    RefreshTokenRequest,
    RefreshTokenResponse,
    RegisterRequest,
    SearchRequest,
    SourceTypeInfo,
    User
} from '@/types'
import axios, { AxiosError, AxiosResponse } from 'axios'
import toast from 'react-hot-toast'

const API_BASE_URL = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000'

// Create axios instance with enhanced configuration
export const api = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 seconds timeout
})

// Request interceptor to add auth token and handle request logging
api.interceptors.request.use(
  (config) => {
    const { accessToken } = useAuthStore.getState()
    if (accessToken) {
      config.headers.Authorization = `Bearer ${accessToken}`
    }
    
    // Log requests in development
    if ((import.meta as any).env?.DEV) {
      console.log(`🚀 API Request: ${config.method?.toUpperCase()} ${config.url}`, config.params)
    }
    
    return config
  },
  (error) => {
    console.error('Request interceptor error:', error)
    return Promise.reject(error)
  }
)

// Enhanced response interceptor with better error handling
api.interceptors.response.use(
  (response: AxiosResponse) => {
    // Log responses in development
    if ((import.meta as any).env?.DEV) {
      console.log(`✅ API Response: ${response.config.method?.toUpperCase()} ${response.config.url}`, response.data)
    }
    return response
  },
  async (error: AxiosError) => {
    const { response, config } = error
    
    // Log errors in development
    if ((import.meta as any).env?.DEV) {
      console.error(`❌ API Error: ${config?.method?.toUpperCase()} ${config?.url}`, error.response?.data)
    }
    
    // Handle different error status codes
    switch (response?.status) {
      case 401:
        // Check if this is a login request - don't redirect if we're already on login page
        const isLoginRequest = config?.url?.includes('/auth/login')
        const isOnLoginPage = window.location.pathname === '/login'
        
        if (isLoginRequest || isOnLoginPage) {
          // This is a login error or we're already on login page - just show error
          const errorData = response.data as ApiResponse<any>
          toast.error(errorData?.message || 'Неверный email или пароль')
        } else {
          // Token expired or invalid - redirect to login
          useAuthStore.getState().logout()
          toast.error('Session expired. Please log in again.')
          window.location.href = '/login'
        }
        break
        
      case 403:
        toast.error('Access denied. You don\'t have permission to perform this action.')
        break
        
      case 404:
        toast.error('Resource not found.')
        break
        
      case 422:
        // Validation error
        const validationError = response.data as ApiResponse<any>
        toast.error(validationError.message || 'Validation failed. Please check your input.')
        break
        
      case 429:
        toast.error('Too many requests. Please try again later.')
        break
        
      case 500:
        toast.error('Server error. Please try again later.')
        break
        
      default:
        const errorData = response?.data as ApiResponse<any>
        toast.error(errorData?.message || 'An unexpected error occurred.')
    }
    
    return Promise.reject(error)
  }
)

// Enhanced API service with typed methods
export class ApiService {
  // News endpoints
  static async getNews(filters: NewsFilter = {}): Promise<NewsListResponse> {
    const params = new URLSearchParams()
    
    if (filters.category) params.append('category', filters.category)
    if (filters.company_id) params.append('company_id', filters.company_id)
    if (filters.company_ids?.length) params.append('company_ids', filters.company_ids.join(','))
    if (filters.source_type) params.append('source_type', filters.source_type)
    if (filters.search_query) params.append('search_query', filters.search_query)
    if (filters.min_priority !== undefined) params.append('min_priority', filters.min_priority.toString())
    if (filters.start_date) params.append('start_date', filters.start_date)
    if (filters.end_date) params.append('end_date', filters.end_date)
    if (filters.limit) params.append('limit', filters.limit.toString())
    if (filters.offset) params.append('offset', filters.offset.toString())
    
    const response = await api.get<NewsListResponse>('/news/', { params })
    return response.data
  }
  
  static async getNewsItem(id: string): Promise<NewsItem> {
    const response = await api.get<NewsItem>(`/news/${id}`)
    return response.data
  }
  
  static async searchNews(searchParams: SearchRequest): Promise<NewsSearchResponse> {
    const params = new URLSearchParams()
    
    params.append('q', searchParams.query)
    if (searchParams.category) params.append('category', searchParams.category)
    if (searchParams.source_type) params.append('source_type', searchParams.source_type)
    if (searchParams.company_id) params.append('company_id', searchParams.company_id)
    if (searchParams.limit) params.append('limit', searchParams.limit.toString())
    if (searchParams.offset) params.append('offset', searchParams.offset.toString())
    
    const response = await api.get<NewsSearchResponse>('/news/search', { params })
    return response.data
  }
  
  static async getNewsStats(): Promise<NewsStats> {
    const response = await api.get<NewsStats>('/news/stats')
    return response.data
  }
  
  static async getNewsCategories(): Promise<{
    categories: NewsCategoryInfo[]
    source_types: SourceTypeInfo[]
  }> {
    const response = await api.get<{
      categories: NewsCategoryInfo[]
      source_types: SourceTypeInfo[]
    }>('/news/categories/list')
    return response.data
  }
  
  static async markNewsRead(id: string): Promise<{ message: string; news_id: string; status: string; timestamp: string }> {
    const response = await api.post(`/news/${id}/mark-read`)
    return response.data
  }
  
  static async favoriteNews(id: string): Promise<{ message: string; news_id: string; status: string; timestamp: string }> {
    const response = await api.post(`/news/${id}/favorite`)
    return response.data
  }
  
  static async getNewsByCategory(
    categoryName: string,
    filters: {
      company_id?: string
      company_ids?: string
      source_type?: string
      limit?: number
      offset?: number
    } = {}
  ): Promise<{
    category: string
    category_description: string
    items: NewsItem[]
    total: number
    limit: number
    offset: number
    has_more: boolean
    statistics: {
      top_companies: Array<{ name: string; count: number }>
      source_distribution: Record<string, number>
      total_in_category: number
    }
    filters: {
      company_id?: string
      source_type?: string
    }
  }> {
    const params = new URLSearchParams()
    
    if (filters.company_id) params.append('company_id', filters.company_id)
    if (filters.company_ids) params.append('company_ids', filters.company_ids)
    if (filters.source_type) params.append('source_type', filters.source_type)
    if (filters.limit) params.append('limit', filters.limit.toString())
    if (filters.offset) params.append('offset', filters.offset.toString())
    
    const response = await api.get(`/news/category/${categoryName}`, { params })
    return response.data
  }
  
  // Auth endpoints
  static async login(credentials: LoginRequest): Promise<AuthResponse> {
    const response = await api.post<AuthResponse>('/auth/login', credentials)
    return response.data
  }
  
  static async register(userData: RegisterRequest): Promise<AuthResponse> {
    const response = await api.post<AuthResponse>('/auth/register', userData)
    return response.data
  }
  
  static async refreshToken(refreshData: RefreshTokenRequest): Promise<RefreshTokenResponse> {
    const response = await api.post<RefreshTokenResponse>('/auth/refresh', refreshData)
    return response.data
  }
  
  static async logout(): Promise<void> {
    await api.post('/auth/logout')
  }
  
  // User endpoints
  static async getCurrentUser(): Promise<User> {
    const response = await api.get<User>('/users/me')
    return response.data
  }
  
  static async updateUser(userData: Partial<User>): Promise<User> {
    const response = await api.patch<User>('/users/me', userData)
    return response.data
  }
  
  // Company endpoints
  static async getCompanies(search?: string, limit = 100, offset = 0): Promise<{
    items: Company[]
    total: number
    limit: number
    offset: number
  }> {
    const params = new URLSearchParams()
    if (search) params.append('search', search)
    params.append('limit', limit.toString())
    params.append('offset', offset.toString())
    
    const response = await api.get<{
      items: Company[]
      total: number
      limit: number
      offset: number
    }>('/companies/', { params })
    return response.data
  }
  
  static async getCompany(id: string): Promise<Company> {
    const response = await api.get<Company>(`/companies/${id}`)
    return response.data
  }
  
  // User preferences endpoints
  static async getUserPreferences(): Promise<{
    subscribed_companies: string[]
    interested_categories: string[]
    keywords: string[]
    notification_frequency: string
    digest_enabled: boolean
    digest_frequency: string
    digest_custom_schedule: Record<string, any>
    digest_format: string
    digest_include_summaries: boolean
    telegram_chat_id: string | null
    telegram_enabled: boolean
    timezone: string
    week_start_day: number
  }> {
    const response = await api.get('/users/preferences')
    return response.data
  }
  
  static async updateUserPreferences(preferences: {
    subscribed_companies?: string[]
    interested_categories?: string[]
    keywords?: string[]
    notification_frequency?: string
  }): Promise<{
    status: string
    preferences: {
      subscribed_companies: string[]
      interested_categories: string[]
      keywords: string[]
      notification_frequency: string
    }
  }> {
    const response = await api.put('/users/preferences', preferences)
    return response.data
  }
  
  static async subscribeToCompany(companyId: string): Promise<{
    status: string
    company_id: string
    company_name: string
    message: string
  }> {
    const response = await api.post(`/users/companies/${companyId}/subscribe`)
    return response.data
  }
  
  static async unsubscribeFromCompany(companyId: string): Promise<{
    status: string
    company_id: string
    message: string
  }> {
    const response = await api.delete(`/users/companies/${companyId}/unsubscribe`)
    return response.data
  }
  
  static async getCompaniesByIds(companyIds: string[]): Promise<Company[]> {
    if (companyIds.length === 0) return []
    
    // Get all companies and filter by IDs (backend max limit is 200)
    const allCompanies = await this.getCompanies('', 200, 0)
    return allCompanies.items.filter(company => companyIds.includes(company.id))
  }
  
  // Health check
  static async healthCheck(): Promise<{
    status: string
    service: string
    version: string
    endpoints: Record<string, string>
  }> {
    const response = await api.get('/health')
    return response.data
  }
}

// Export the default api instance for backward compatibility
export default api
