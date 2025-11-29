import { useAuthStore } from '@/store/authStore'
import type {
    AnalyticsChangeLogResponse,
    AnalyticsExportRequestPayload,
    AnalyticsExportResponse,
    AnalyticsPeriod,
    ApiResponse,
    AuthResponse,
    ChangeProcessingStatus,
    Company,
    CompanyAnalyticsSnapshot,
    CompanyScanRequest,
    CompanyScanResult,
    ComparisonFilters,
    ComparisonRequestPayload,
    ComparisonResponse,
    CompetitorChangeEvent,
    CreateCompanyRequest,
    CreateCompanyResponse,
    CreateSubscriptionRequest,
    KnowledgeGraphEdge,
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
    Report,
    ReportCreateRequest,
    ReportCreateResponse,
    ReportPreset,
    ReportPresetCreateRequest,
    ReportStatusResponse,
    ReportsListResponse,
    SearchRequest,
    SnapshotSeries,
    SourceTypeInfo,
    Subscription,
    SubscriptionAccessResponse,
    User
} from '@/types'
import axios, { AxiosError, AxiosInstance, AxiosResponse } from 'axios'
import JSZip from 'jszip'
import toast from 'react-hot-toast'

const normalizeUrl = (value?: string | null): string | null => {
  if (typeof value !== 'string') {
    return null
  }

  const trimmed = value.trim()
  if (!trimmed.length) {
    return null
  }

  return trimmed.replace(/\/$/, '')
}

const resolveApiBaseUrl = (): string => {
  const envUrl = normalizeUrl((import.meta as any).env?.VITE_API_URL)
  if (envUrl) {
    return envUrl
  }

  let runtimeUrl: string | null = null
  if (typeof window !== 'undefined') {
    runtimeUrl = normalizeUrl((window as any).__SHOT_NEWS_API_URL__)
  }
  if (runtimeUrl) {
    console.warn(
      '[shot-news] VITE_API_URL не задан. Используется window.__SHOT_NEWS_API_URL__. Задайте переменную окружения, чтобы избавиться от предупреждения.'
    )
    return runtimeUrl
  }

  const devFallback = normalizeUrl((import.meta as any).env?.VITE_DEV_API_URL)
  if (devFallback) {
    console.warn(
      '[shot-news] VITE_API_URL не задан. Используется fallback из VITE_DEV_API_URL. Задайте основную переменную для фронтенда.'
    )
    return devFallback
  }

  if (typeof window !== 'undefined') {
    const { hostname } = window.location
    if (hostname === 'localhost' || hostname === '127.0.0.1') {
      console.warn(
        '[shot-news] VITE_API_URL не задан. Используется fallback http://localhost:8000. Установите переменную, чтобы исключить таймауты за пределами dev-сервера.'
      )
      return 'http://localhost:8000'
    }
  }

  console.error(
    '[shot-news] API base URL не сконфигурирован. Установите VITE_API_URL в frontend/.env или определите window.__SHOT_NEWS_API_URL__.'
  )
  return ''
}

const API_BASE_URL = resolveApiBaseUrl()
const API_V1_BASE = API_BASE_URL ? `${API_BASE_URL}/api/v1` : '/api/v1'
const API_V2_BASE = API_BASE_URL ? `${API_BASE_URL}/api/v2` : '/api/v2'

const attachInterceptors = (instance: AxiosInstance) => {
  instance.interceptors.request.use(
    (config) => {
      const { accessToken } = useAuthStore.getState()
      if (accessToken) {
        config.headers.Authorization = `Bearer ${accessToken}`
      }

      if ((import.meta as any).env?.DEV) {
        // Для GET запросов показываем params, для POST/PUT/PATCH - data
        const requestData = config.method?.toUpperCase() === 'GET' ? config.params : config.data
        console.log(`🚀 API Request: ${config.method?.toUpperCase()} ${config.url}`, requestData)
      }

      return config
    },
    (error) => {
      console.error('Request interceptor error:', error)
      return Promise.reject(error)
    }
  )

  instance.interceptors.response.use(
    (response: AxiosResponse) => {
      if ((import.meta as any).env?.DEV) {
        console.log(`✅ API Response: ${response.config.method?.toUpperCase()} ${response.config.url}`, response.data)
      }
      return response
    },
    async (error: AxiosError) => {
      const { response, config, code } = error

      // Handle timeout errors (ECONNABORTED) silently for polling endpoints
      const isTimeoutError = code === 'ECONNABORTED'
      const isPollingEndpoint = config?.url?.includes('/notifications/unread') || 
                                config?.url?.includes('/news/')
      
      if (isTimeoutError && isPollingEndpoint) {
        // Silently ignore timeout errors for polling endpoints
        if ((import.meta as any).env?.DEV) {
          console.warn(`⚠️ Request timeout (silent): ${config?.method?.toUpperCase()} ${config?.url}`)
        }
        return Promise.reject(error)
      }

      const requestUrl = config?.url ?? ''
      const suppressNotFoundToast =
        requestUrl.includes('/analytics/companies/') &&
        (requestUrl.includes('/impact/latest') || requestUrl.includes('/snapshots'))
      const isAnalytics404 = suppressNotFoundToast && response?.status === 404
      const isAnalyticsGraph404 = requestUrl.includes('/analytics/graph') && response?.status === 404

      if ((import.meta as any).env?.DEV) {
        // Для 404 на аналитике не логируем - это ожидаемое поведение (аналитика может быть еще не построена)
        if (!isAnalytics404 && !isAnalyticsGraph404) {
          console.error(`❌ API Error: ${config?.method?.toUpperCase()} ${config?.url}`, error.response?.data)
        }
      }

      // Handle timeout errors for non-polling endpoints
      // Don't show toast for recompute/sync endpoints - they have their own error handling
      const isRecomputeEndpoint = requestUrl.includes('/recompute') || requestUrl.includes('/graph/sync')
      if (isTimeoutError && !isPollingEndpoint && !isRecomputeEndpoint) {
        toast.error('Request timeout. Please check your connection and try again.')
        return Promise.reject(error)
      }
      
      // For recompute/sync endpoints, just reject without extra toast (already handled in component)
      if (isTimeoutError && isRecomputeEndpoint) {
        return Promise.reject(error)
      }

      switch (response?.status) {
        case 401: {
          const isLoginRequest = config?.url?.includes('/auth/login')
          const isOnLoginPage = window.location.pathname === '/login'

          if (isLoginRequest || isOnLoginPage) {
            const errorData = response.data as ApiResponse<any>
            toast.error(errorData?.message || 'Неверный email или пароль')
          } else {
            useAuthStore.getState().logout()
            toast.error('Session expired. Please log in again.')
            window.location.href = '/login'
          }

          break
        }

        case 403:
          toast.error('Access denied. You don\'t have permission to perform this action.')
          break

        case 404:
          if (!suppressNotFoundToast) {
            toast.error('Resource not found.')
          }
          break

        case 410: {
          // Session expired (Gone) - для онбординга
          const isOnboardingRequest = config?.url?.includes('/onboarding/')
          if (isOnboardingRequest) {
            // Очистить истекшую сессию и начать новую
            sessionStorage.removeItem('onboarding_session_token')
            toast.error('Сессия онбординга истекла. Начинаем новую сессию...')
            // Перезагрузить страницу для создания новой сессии
            if (window.location.pathname.includes('/onboarding')) {
              window.location.reload()
            }
          } else {
            toast.error('Resource no longer available.')
          }
          break
        }

        case 422: {
          const validationError = response.data as ApiResponse<any>
          toast.error(validationError.message || 'Validation failed. Please check your input.')
          break
        }

        case 429:
          toast.error('Too many requests. Please try again later.')
          break

        case 500:
          toast.error('Server error. Please try again later.')
          break

        default: {
          const errorData = response?.data as ApiResponse<any>
          toast.error(errorData?.message || 'An unexpected error occurred.')
        }
      }

      return Promise.reject(error)
    }
  )
}

export const api = axios.create({
  baseURL: API_V1_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
})

export const apiV2 = axios.create({
  baseURL: API_V2_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
})

// API для сканирования с увеличенным таймаутом (90 секунд)
export const apiScan = axios.create({
  baseURL: API_V1_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 90000, // 90 секунд для сканирования
})

attachInterceptors(api)
attachInterceptors(apiScan)
attachInterceptors(apiV2)
attachInterceptors(apiScan)

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
    const response = await api.put<User>('/users/me', userData)
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
  
  // Competitor analysis endpoints
  static async suggestCompetitors(companyId: string, params: {
    limit?: number
    days?: number
  } = {}): Promise<{
    company_id: string
    period_days: number
    suggestions: Array<{
      company: Company
      similarity_score: number
      common_categories: string[]
      reason: string
    }>
  }> {
    const response = await api.get(`/competitors/suggest/${companyId}`, { params })
    return response.data
  }
  
  static async analyzeThemes(companyIds: string[], params: {
    date_from?: string
    date_to?: string
  } = {}): Promise<{
    themes: Record<string, {
      total_mentions: number
      by_company: Record<string, number>
      example_titles: string[]
    }>
    unique_themes: Record<string, string[]>
  }> {
    const response = await api.post('/competitors/themes', {
      company_ids: companyIds,
      ...params
    })
    return response.data
  }
  
  static async getCompanyActivity(companyId: string, params: {
    days?: number
  } = {}): Promise<{
    company_id: string
    period_days: number
    date_from: string
    date_to: string
    metrics: {
      news_volume: number
      category_distribution: Record<string, number>
      activity_score: number
      daily_activity: Record<string, number>
      top_news: Array<{
        id: string
        title: string
        category: string
        published_at: string
        source_url: string
        priority_score: number
      }>
    }
  }> {
    const response = await api.get(`/competitors/activity/${companyId}`, { params })
    return response.data
  }
  
  static async searchCompanies(query: string, params: {
    limit?: number
  } = {}): Promise<{
    items: Company[]
    total: number
    limit: number
    offset: number
  }> {
    const response = await api.get('/companies/', { 
      params: { search: query, ...params } 
    })
    return response.data
  }
  
  static async compareCompanies(request: {
    company_ids: string[]
    date_from?: string
    date_to?: string
    name?: string
    topics?: string[]
    sentiments?: string[]
    source_types?: string[]
    min_priority?: number
  }): Promise<{
    companies: Company[]
    date_from: string
    date_to: string
    metrics: {
      news_volume: Record<string, number>
      category_distribution: Record<string, Record<string, number>>
      activity_score: Record<string, number>
      daily_activity?: Record<string, Record<string, number>>
      top_news?: Record<string, NewsItem[]>
      topic_distribution?: Record<string, Record<string, number>>
      sentiment_distribution?: Record<string, Record<string, number>>
      avg_priority?: Record<string, number>
    }
    filters?: {
      topics?: string[]
      sentiments?: string[]
      source_types?: string[]
      min_priority?: number
    }
  }> {
    console.log('API Service - compareCompanies request:', request)
    console.log('API Service - request type:', typeof request)
    console.log('API Service - company_ids type:', typeof request.company_ids)
    console.log('API Service - company_ids is array:', Array.isArray(request.company_ids))
    
    const response = await api.post('/competitors/compare', request)
    return response.data
  }

  static async getCompetitorChangeEvents(
    companyId: string,
    params: {
      limit?: number
      status?: ChangeProcessingStatus
    } = {}
  ): Promise<{
    events: CompetitorChangeEvent[]
    total: number
  }> {
    const response = await api.get(`/competitors/changes/${companyId}`, { params })
    return response.data
  }

  static async recomputeCompetitorChangeEvent(eventId: string): Promise<CompetitorChangeEvent> {
    const response = await api.post(`/competitors/changes/${eventId}/recompute`)
    return response.data
  }

  // Company scanning endpoints
  static async scanCompany(request: CompanyScanRequest): Promise<CompanyScanResult> {
    const response = await apiScan.post<CompanyScanResult>('/companies/scan', request)
    return response.data
  }

  static async createCompany(request: CreateCompanyRequest): Promise<CreateCompanyResponse> {
    const response = await api.post<CreateCompanyResponse>('/companies/', request)
    return response.data
  }

  // TODO: Add async scanning methods for large sites
  // static async scanCompanyAsync(request: CompanyScanRequest): Promise<{ task_id: string }> {
  //   const response = await api.post('/companies/scan/async', request)
  //   return response.data
  // }
  //
  // static async getScanStatus(taskId: string): Promise<ScanStatus> {
  //   const response = await api.get(`/companies/scan/status/${taskId}`)
  //   return response.data
  // }

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

  // Analytics v2 endpoints
  static async getAnalyticsSnapshots(
    companyId: string,
    period: AnalyticsPeriod = 'daily',
    limit = 60
  ): Promise<SnapshotSeries> {
    const response = await apiV2.get<SnapshotSeries>(`/analytics/companies/${companyId}/snapshots`, {
      params: { period, limit }
    })
    return response.data
  }

  static async getLatestAnalyticsSnapshot(
    companyId: string,
    period: AnalyticsPeriod = 'daily'
  ): Promise<CompanyAnalyticsSnapshot> {
    const response = await apiV2.get<CompanyAnalyticsSnapshot>(`/analytics/companies/${companyId}/impact/latest`, {
      params: { period }
    })
    return response.data
  }

  static async triggerAnalyticsRecompute(
    companyId: string,
    period: AnalyticsPeriod = 'daily',
    lookback = 30
  ): Promise<{ status: string; task_id: string }> {
    const response = await apiV2.post<{ status: string; task_id: string }>(
      `/analytics/companies/${companyId}/recompute`,
      null,
      { 
        params: { period, lookback },
        timeout: 15000 // 15 секунд - увеличен для надежности (бэкенд проверяет Redis и может занять время)
      }
    )
    
    // Validate response data
    if (!response.data || !response.data.task_id) {
      throw new Error('Invalid response: task_id is missing')
    }
    
    return response.data
  }

  static async triggerKnowledgeGraphSync(
    companyId: string,
    periodStartIso: string,
    period: AnalyticsPeriod = 'daily'
  ): Promise<{ status: string; task_id: string }> {
    const response = await apiV2.post<{ status: string; task_id: string }>(
      `/analytics/companies/${companyId}/graph/sync`,
      null,
      { 
        params: { period_start: periodStartIso, period },
        timeout: 15000 // 15 секунд - увеличен для надежности
      }
    )
    
    // Validate response data
    if (!response.data || !response.data.task_id) {
      throw new Error('Invalid response: task_id is missing')
    }
    
    return response.data
  }

  static async getAnalyticsGraph(
    companyId?: string,
    relationship?: string,
    limit = 100
  ): Promise<KnowledgeGraphEdge[]> {
    const params = new URLSearchParams()
    if (companyId) params.append('company_id', companyId)
    if (relationship) params.append('relationship', relationship)
    if (limit) params.append('limit', limit.toString())

    const response = await apiV2.get<KnowledgeGraphEdge[]>('/analytics/graph', { params })
    return response.data
  }

  static async getAnalyticsChangeLog(params: {
    companyId?: string
    subjectKey?: string
    period?: AnalyticsPeriod
    cursor?: string | null
    limit?: number
    filters?: ComparisonFilters
  }): Promise<AnalyticsChangeLogResponse> {
    const queryParams: Record<string, any> = {}

    if (params.companyId) {
      queryParams.company_id = params.companyId
    }
    if (params.subjectKey) {
      queryParams.subject_key = params.subjectKey
    }
    if (params.period) {
      queryParams.period = params.period
    }
    if (params.cursor) {
      queryParams.cursor = params.cursor
    }
    if (typeof params.limit === 'number') {
      queryParams.limit = params.limit
    }
    if (params.filters) {
      if (params.filters.topics?.length) {
        queryParams.topics = params.filters.topics
      }
      if (params.filters.sentiments?.length) {
        queryParams.sentiments = params.filters.sentiments
      }
      if (params.filters.source_types?.length) {
        queryParams.source_types = params.filters.source_types
      }
      if (
        params.filters.min_priority !== undefined &&
        params.filters.min_priority !== null
      ) {
        queryParams.min_priority = params.filters.min_priority
      }
    }

    const response = await apiV2.get<AnalyticsChangeLogResponse>('/analytics/change-log', {
      params: queryParams
    })
    return response.data
  }

  static async listReportPresets(): Promise<ReportPreset[]> {
    const response = await apiV2.get<ReportPreset[]>('/analytics/reports/presets')
    return response.data
  }

  static async createReportPreset(payload: ReportPresetCreateRequest): Promise<ReportPreset> {
    const response = await apiV2.post<ReportPreset>('/analytics/reports/presets', payload)
    return response.data
  }

  static async getAnalyticsComparison(payload: ComparisonRequestPayload): Promise<ComparisonResponse> {
    const response = await apiV2.post<ComparisonResponse>('/analytics/comparisons', payload)
    return response.data
  }

  static async buildAnalyticsExport(payload: AnalyticsExportRequestPayload): Promise<AnalyticsExportResponse> {
    const response = await apiV2.post<AnalyticsExportResponse>('/analytics/export', payload)
    return response.data
  }

  // Export methods
  static async exportAnalysis(
    exportData: AnalyticsExportResponse,
    format: 'json' | 'pdf' | 'csv'
  ): Promise<void> {
    switch (format) {
      case 'json':
        this.exportAsJson(exportData)
        break
      case 'pdf':
        await this.exportAsPdf(exportData)
        break
      case 'csv':
        await this.exportAsCsv(exportData)
        break
    }
  }

  private static exportAsJson(data: AnalyticsExportResponse): void {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    this.triggerDownload(blob, `analytics-export-${this.today()}.json`, 'application/json')
  }

  private static async exportAsPdf(data: AnalyticsExportResponse): Promise<void> {
    const html = this.generateAnalyticsPdfHtml(data)
    const printWindow = window.open('', '_blank')
    if (printWindow) {
      printWindow.document.write(html)
      printWindow.document.close()
      printWindow.focus()
      printWindow.print()
      printWindow.close()
    }
  }

  private static async exportAsCsv(data: AnalyticsExportResponse): Promise<void> {
    const csvFiles = this.generateCsvFiles(data)
    const zip = new JSZip()

    Object.entries(csvFiles).forEach(([filename, content]) => {
      zip.file(filename, content)
    })

    const blob = await zip.generateAsync({ type: 'blob' })
    this.triggerDownload(blob, `analytics-export-${this.today()}.zip`, 'application/zip')
  }


  private static generateAnalyticsPdfHtml(data: AnalyticsExportResponse): string {
    const { comparison, notification_settings: notifications, presets, timeframe } = data
    const subjects = comparison.subjects
    const knowledgeBySubject = comparison.knowledge_graph || {}
    const changeLogBySubject = comparison.change_log || {}

    const subjectRows = subjects
      .map(subject => {
        const companies = subject.companies.map(company => company.name).join(', ')
        return `
          <tr>
            <td>${subject.label}</td>
            <td>${subject.subject_type}</td>
            <td>${companies || '—'}</td>
            <td>${subject.filters.topics.join(', ') || '—'}</td>
            <td>${subject.filters.sentiments.join(', ') || '—'}</td>
            <td>${subject.filters.source_types.join(', ') || '—'}</td>
            <td>${subject.filters.min_priority ?? ''}</td>
          </tr>
        `
      })
      .join('')

    const metricRows = comparison.metrics
      .map(metric => {
        const subject = subjects.find(item => item.subject_key === metric.subject_key)
        const snapshot = metric.snapshot
        const knowledgeCount = knowledgeBySubject[metric.subject_key]?.length || 0
        const changeCount = changeLogBySubject[metric.subject_key]?.length || 0
        return `
          <tr>
            <td>${subject?.label || metric.subject_key}</td>
            <td>${metric.impact_score.toFixed(2)}</td>
            <td>${metric.trend_delta.toFixed(2)}%</td>
            <td>${metric.news_volume}</td>
            <td>${metric.activity_score.toFixed(2)}</td>
            <td>${metric.avg_priority.toFixed(2)}</td>
            <td>${metric.innovation_velocity.toFixed(2)}</td>
            <td>${snapshot?.news_positive ?? 0}/${snapshot?.news_negative ?? 0}/${snapshot?.news_neutral ?? 0}</td>
            <td>${knowledgeCount}</td>
            <td>${changeCount}</td>
          </tr>
        `
      })
      .join('')

    const componentsSections = comparison.metrics
      .map(metric => {
        if (!metric.impact_components.length) return ''
        const subject = subjects.find(item => item.subject_key === metric.subject_key)
        const rows = metric.impact_components
          .map(component => `
            <tr>
              <td>${component.component_type}</td>
              <td>${component.score_contribution.toFixed(2)}</td>
              <td>${component.weight.toFixed(2)}</td>
            </tr>
          `)
          .join('')
        return `
          <div class="section">
            <h3>${subject?.label || metric.subject_key}: Impact Components</h3>
            <table>
              <tr><th>Component</th><th>Score Contribution</th><th>Avg Weight</th></tr>
              ${rows}
            </table>
          </div>
        `
      })
      .join('')

    const knowledgeSections = Object.entries(knowledgeBySubject)
      .map(([subjectKey, edges]) => {
        if (!edges.length) return ''
        const subject = subjects.find(item => item.subject_key === subjectKey)
        const rows = edges
          .map(edge => `
            <tr>
              <td>${edge.relationship_type}</td>
              <td>${edge.source_entity_type}</td>
              <td>${edge.target_entity_type}</td>
              <td>${(edge.confidence * 100).toFixed(0)}%</td>
              <td>${edge.metadata?.category || '—'}</td>
              <td>${edge.metadata?.change_detected_at ? new Date(edge.metadata.change_detected_at).toLocaleDateString() : '—'}</td>
            </tr>
          `)
          .join('')
        return `
          <div class="section">
            <h3>${subject?.label || subjectKey}: Knowledge Graph Highlights</h3>
            <table>
              <tr><th>Relationship</th><th>Source</th><th>Target</th><th>Confidence</th><th>Category</th><th>Detected</th></tr>
              ${rows}
            </table>
          </div>
        `
      })
      .join('')

    const changeLogSections = Object.entries(changeLogBySubject)
      .map(([subjectKey, events]) => {
        if (!events.length) return ''
        const subject = subjects.find(item => item.subject_key === subjectKey)
        const rows = events
          .map(event => `
            <tr>
              <td>${new Date(event.detected_at).toLocaleString()}</td>
              <td>${event.source_type}</td>
              <td>${event.change_summary}</td>
              <td>${event.changed_fields?.map(field => field.type || 'field').join(', ') || '—'}</td>
              <td>${event.processing_status}</td>
            </tr>
          `)
          .join('')
        return `
          <div class="section">
            <h3>${subject?.label || subjectKey}: Change Log</h3>
            <table>
              <tr><th>Detected At</th><th>Source</th><th>Summary</th><th>Changed Fields</th><th>Status</th></tr>
              ${rows}
            </table>
          </div>
        `
      })
      .join('')

    const presetsSection = presets.length
      ? `
        <div class="section">
          <h2>User Presets</h2>
          <table>
            <tr><th>Name</th><th>Description</th><th>Companies</th><th>Created</th><th>Updated</th></tr>
            ${presets
              .map(preset => `
                <tr>
                  <td>${preset.name}</td>
                  <td>${preset.description || '—'}</td>
                  <td>${(preset.companies || []).length}</td>
                  <td>${new Date(preset.created_at).toLocaleDateString()}</td>
                  <td>${new Date(preset.updated_at).toLocaleDateString()}</td>
                </tr>
              `)
              .join('')}
          </table>
        </div>
      `
      : ''

    const notificationsSection = notifications
      ? `
        <div class="section">
          <h2>Notification Settings</h2>
          <p><strong>Frequency:</strong> ${notifications.notification_frequency || '—'}</p>
          <p><strong>Digest Enabled:</strong> ${notifications.digest_enabled ? 'Yes' : 'No'}</p>
          <p><strong>Digest Frequency:</strong> ${notifications.digest_frequency || '—'}</p>
          <p><strong>Digest Format:</strong> ${notifications.digest_format || '—'}</p>
          <p><strong>Subscribed Companies:</strong> ${(notifications.subscribed_companies || []).length}</p>
          <p><strong>Interested Categories:</strong> ${(notifications.interested_categories || []).join(', ') || '—'}</p>
          <p><strong>Keywords:</strong> ${(notifications.keywords || []).join(', ') || '—'}</p>
          <p><strong>Telegram Enabled:</strong> ${notifications.telegram_enabled ? 'Yes' : 'No'}</p>
        </div>
      `
      : ''

    return `
      <!DOCTYPE html>
      <html>
      <head>
        <title>Analytics Comparison Report</title>
        <style>
          body { font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }
          h1 { color: #2563eb; border-bottom: 2px solid #2563eb; padding-bottom: 10px; }
          h2 { color: #374151; margin-top: 30px; border-bottom: 1px solid #e5e7eb; padding-bottom: 5px; }
          h3 { color: #6b7280; margin-top: 20px; }
          table { width: 100%; border-collapse: collapse; margin: 15px 0; }
          th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
          th { background-color: #f3f4f6; font-weight: bold; }
          .section { margin: 25px 0; padding: 15px; border: 1px solid #e5e7eb; border-radius: 8px; }
          .highlight { background-color: #fef3c7; padding: 10px; border-radius: 5px; margin: 10px 0; }
        </style>
      </head>
      <body>
        <h1>Analytics Comparison Report</h1>
        <div class="highlight">
          <p><strong>Generated:</strong> ${new Date(data.generated_at).toLocaleString()}</p>
          <p><strong>Timeframe:</strong> ${new Date(timeframe.date_from).toLocaleDateString()} — ${new Date(timeframe.date_to).toLocaleDateString()} (${timeframe.period})</p>
          <p><strong>Subjects Compared:</strong> ${subjects.length}</p>
        </div>
        
        <div class="section">
          <h2>Subjects</h2>
          <table>
            <tr><th>Label</th><th>Type</th><th>Companies</th><th>Topics</th><th>Sentiments</th><th>Sources</th><th>Min Priority</th></tr>
            ${subjectRows}
          </table>
        </div>
        
        <div class="section">
          <h2>Metric Summary</h2>
          <table>
            <tr>
              <th>Subject</th>
              <th>Impact Score</th>
              <th>Trend Δ</th>
              <th>News Volume</th>
              <th>Activity Score</th>
              <th>Avg Priority</th>
              <th>Innovation Velocity</th>
              <th>Positive/Negative/Neutral</th>
              <th>Knowledge Links</th>
              <th>Change Events</th>
            </tr>
            ${metricRows}
          </table>
        </div>
        
        ${componentsSections}
        ${knowledgeSections}
        ${changeLogSections}
        ${notificationsSection}
        ${presetsSection}
        
        <div class="section">
          <p style="text-align: center; color: #9ca3af; font-size: 12px;">
            Generated by Shot News Analytics Platform
          </p>
        </div>
      </body>
      </html>
    `
  }

  private static generateCsvFiles(data: AnalyticsExportResponse): Record<string, string> {
    const files: Record<string, string> = {}
    const { comparison, notification_settings: notifications } = data

    const subjectHeaders = [
      'subject_key',
      'label',
      'subject_type',
      'company_ids',
      'preset_id',
      'filters_topics',
      'filters_sentiments',
      'filters_source_types',
      'filters_min_priority'
    ]
    const subjectRows = comparison.subjects.map(subject => [
      subject.subject_key,
      subject.label,
      subject.subject_type,
      subject.company_ids.join('|'),
      subject.preset_id || '',
      subject.filters.topics.join('|'),
      subject.filters.sentiments.join('|'),
      subject.filters.source_types.join('|'),
      subject.filters.min_priority ?? ''
    ])
    files['subjects.csv'] = this.toCsv(subjectHeaders, subjectRows)

    const metricHeaders = [
      'subject_key',
      'impact_score',
      'trend_delta',
      'news_volume',
      'activity_score',
      'avg_priority',
      'innovation_velocity',
      'news_positive',
      'news_negative',
      'news_neutral',
      'knowledge_links',
      'change_events'
    ]
    const knowledgeBySubject = comparison.knowledge_graph || {}
    const changeLogBySubject = comparison.change_log || {}
    const metricRows = comparison.metrics.map(metric => {
      const snapshot = metric.snapshot
      const knowledgeCount = knowledgeBySubject[metric.subject_key]?.length || 0
      const changeCount = changeLogBySubject[metric.subject_key]?.length || 0
      return [
        metric.subject_key,
        metric.impact_score.toFixed(2),
        metric.trend_delta.toFixed(2),
        metric.news_volume,
        metric.activity_score.toFixed(2),
        metric.avg_priority.toFixed(2),
        metric.innovation_velocity.toFixed(2),
        snapshot?.news_positive ?? 0,
        snapshot?.news_negative ?? 0,
        snapshot?.news_neutral ?? 0,
        knowledgeCount,
        changeCount
      ]
    })
    files['metrics.csv'] = this.toCsv(metricHeaders, metricRows)

    const componentHeaders = ['subject_key', 'component_type', 'score_contribution', 'weight']
    const componentRows: Array<(string | number)>[] = []
    comparison.metrics.forEach(metric => {
      metric.impact_components.forEach(component => {
        componentRows.push([
          metric.subject_key,
          component.component_type,
          component.score_contribution.toFixed(2),
          component.weight.toFixed(2)
        ])
      })
    })
    files['impact_components.csv'] = this.toCsv(componentHeaders, componentRows)

    const seriesHeaders = [
      'subject_key',
      'period_start',
      'impact_score',
      'innovation_velocity',
      'trend_delta',
      'news_total',
      'news_positive',
      'news_negative',
      'news_neutral',
      'pricing_changes',
      'feature_updates',
      'funding_events'
    ]
    const seriesRows: Array<(string | number)>[] = []
    comparison.series.forEach(series => {
      series.snapshots.forEach(snapshot => {
        seriesRows.push([
          series.subject_key,
          snapshot.period_start,
          snapshot.impact_score.toFixed(2),
          snapshot.innovation_velocity.toFixed(2),
          snapshot.trend_delta?.toFixed(2) ?? '',
          snapshot.news_total,
          snapshot.news_positive,
          snapshot.news_negative,
          snapshot.news_neutral,
          snapshot.pricing_changes,
          snapshot.feature_updates,
          snapshot.funding_events
        ])
      })
    })
    files['series.csv'] = this.toCsv(seriesHeaders, seriesRows)

    const topNewsHeaders = [
      'subject_key',
      'news_id',
      'title',
      'category',
      'topic',
      'sentiment',
      'source_type',
      'priority_score',
      'published_at',
      'source_url'
    ]
    const topNewsRows: Array<(string | number)>[] = []
    comparison.metrics.forEach(metric => {
      metric.top_news.forEach(news => {
        topNewsRows.push([
          metric.subject_key,
          news.id,
          news.title,
          news.category || '',
          news.topic || '',
          news.sentiment || '',
          news.source_type || '',
          news.priority_score.toFixed(2),
          news.published_at,
          news.source_url
        ])
      })
    })
    files['top_news.csv'] = this.toCsv(topNewsHeaders, topNewsRows)

    const kgHeaders = [
      'subject_key',
      'edge_id',
      'relationship_type',
      'source_entity_type',
      'target_entity_type',
      'confidence',
      'category',
      'detected_at'
    ]
    const kgRows: Array<(string | number)>[] = []
    Object.entries(knowledgeBySubject).forEach(([subjectKey, edges]) => {
      edges.forEach(edge => {
        kgRows.push([
          subjectKey,
          edge.id,
          edge.relationship_type,
          edge.source_entity_type,
          edge.target_entity_type,
          (edge.confidence * 100).toFixed(2),
          edge.metadata?.category || '',
          edge.metadata?.change_detected_at || ''
        ])
      })
    })
    files['knowledge_graph.csv'] = this.toCsv(kgHeaders, kgRows)

    const changeHeaders = [
      'subject_key',
      'event_id',
      'detected_at',
      'source_type',
      'processing_status',
      'notification_status',
      'change_summary'
    ]
    const changeRows: Array<(string | number)>[] = []
    Object.entries(changeLogBySubject).forEach(([subjectKey, events]) => {
      events.forEach(event => {
        changeRows.push([
          subjectKey,
          event.id,
          event.detected_at,
          event.source_type,
          event.processing_status,
          event.notification_status,
          event.change_summary
        ])
      })
    })
    files['change_log.csv'] = this.toCsv(changeHeaders, changeRows)

    if (notifications) {
      const notificationHeaders = [
        'notification_frequency',
        'digest_enabled',
        'digest_frequency',
        'digest_format',
        'subscribed_companies',
        'interested_categories',
        'keywords',
        'telegram_enabled',
        'telegram_chat_id',
        'telegram_digest_mode',
        'timezone',
        'week_start_day'
      ]
      const notificationRow = [[
        notifications.notification_frequency,
        notifications.digest_enabled ? 'true' : 'false',
        notifications.digest_frequency,
        notifications.digest_format,
        notifications.subscribed_companies.join('|'),
        notifications.interested_categories.join('|'),
        notifications.keywords.join('|'),
        notifications.telegram_enabled ? 'true' : 'false',
        notifications.telegram_chat_id || '',
        notifications.telegram_digest_mode,
        notifications.timezone || '',
        notifications.week_start_day ?? ''
      ]]
      files['notification_settings.csv'] = this.toCsv(notificationHeaders, notificationRow)
    }

    if (data.presets?.length) {
      const presetHeaders = ['preset_id', 'name', 'description', 'companies', 'is_favorite', 'created_at', 'updated_at']
      const presetRows = data.presets.map(preset => [
        preset.id,
        preset.name,
        preset.description || '',
        (preset.companies || []).join('|'),
        preset.is_favorite ? 'true' : 'false',
        preset.created_at,
        preset.updated_at
      ])
      files['presets.csv'] = this.toCsv(presetHeaders, presetRows)
    }

    return files
  }

  private static toCsv(headers: (string | number)[], rows: Array<Array<string | number>>): string {
    const headerRow = headers.map(this.escapeCsv).join(',')
    const dataRows = rows.map(row => row.map(this.escapeCsv).join(','))
    return [headerRow, ...dataRows].join('\n')
  }

  private static escapeCsv(value: string | number | undefined | null): string {
    if (value === null || value === undefined) {
      return ''
    }
    const stringValue = String(value)
    if (stringValue.includes(',') || stringValue.includes('"') || stringValue.includes('\n')) {
      return `"${stringValue.replace(/"/g, '""')}"`
    }
    return stringValue
  }

  private static triggerDownload(blob: Blob, filename: string, mime: string): void {
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    link.type = mime
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  private static today(): string {
    return new Date().toISOString().split('T')[0]
  }

  // Report methods
  /**
   * Create a new report
   */
  static async createReport(query: string): Promise<ReportCreateResponse> {
    const response = await api.post<ReportCreateResponse>(
      '/reports/create',
      { query } as ReportCreateRequest
    )
    return response.data
  }

  /**
   * Get report status
   */
  static async getReportStatus(reportId: string): Promise<ReportStatusResponse> {
    const response = await api.get<ReportStatusResponse>(
      `/reports/${reportId}/status`
    )
    return response.data
  }

  /**
   * Get full report data
   * @param reportId - Report ID
   * @param includeCompetitors - Whether to include competitors (may be slow, default: false)
   */
  static async getReport(reportId: string, includeCompetitors: boolean = false): Promise<Report> {
    const response = await api.get<Report>(
      `/reports/${reportId}`,
      {
        params: {
          include_competitors: includeCompetitors
        }
      }
    )
    return response.data
  }

  /**
   * Get list of user's reports
   */
  static async getReports(limit: number = 20, offset: number = 0): Promise<ReportsListResponse> {
    const response = await api.get<ReportsListResponse>(
      '/reports/',
      {
        params: { limit, offset }
      }
    )
    return response.data
  }

  /**
   * Delete a report
   */
  static async deleteReport(reportId: string): Promise<void> {
    await api.delete(`/reports/${reportId}`)
  }

  /**
   * Quick company analysis using existing database data
   * @param query - Company name or URL
   * @param includeCompetitors - Whether to include competitors (default: false)
   */
  static async quickCompanyAnalysis(query: string, includeCompetitors: boolean = false): Promise<Report> {
    const response = await api.post<Report>('/companies/quick-analysis', {
      query: query.trim(),
      include_competitors: includeCompetitors
    })
    return response.data
  }

  // Onboarding endpoints
  /**
   * Start a new onboarding session
   */
  static async startOnboarding(): Promise<{
    session_token: string
    session_id: string
    current_step: string
  }> {
    const response = await api.post('/onboarding/start')
    return response.data
  }

  /**
   * Get company data from onboarding session
   */
  static async getOnboardingCompany(sessionToken: string): Promise<{
    company: any
    current_step: string
  }> {
    const response = await api.get('/onboarding/company', {
      params: { session_token: sessionToken }
    })
    return response.data
  }

  /**
   * Analyze company website for onboarding
   */
  static async analyzeCompanyForOnboarding(websiteUrl: string, sessionToken: string): Promise<{
    company: any
    current_step: string
  }> {
    const response = await api.post('/onboarding/company/analyze', {
      website_url: websiteUrl,
      session_token: sessionToken
    })
    return response.data
  }

  /**
   * Suggest competitors for onboarding
   */
  static async suggestCompetitorsForOnboarding(sessionToken: string, limit: number = 10): Promise<{
    competitors: Array<{
      company: any
      similarity_score: number
      common_categories: string[]
      reason: string
    }>
    current_step: string
  }> {
    // Use apiScan for onboarding endpoints with longer timeout (90 seconds)
    // GPT generation can take time
    const response = await apiScan.get('/onboarding/competitors/suggest', {
      params: { session_token: sessionToken, limit }
    })
    return response.data
  }

  /**
   * Select competitors in onboarding
   */
  static async selectCompetitorsInOnboarding(sessionToken: string, competitorIds: string[], competitorData?: any[]): Promise<{
    status: string
    current_step: string
  }> {
    const response = await api.post('/onboarding/competitors/select', {
      session_token: sessionToken,
      selected_competitor_ids: competitorIds,
      competitor_data: competitorData
    })
    return response.data
  }

  /**
   * Setup observation for competitors
   */
  static async setupObservation(sessionToken: string): Promise<{
    task_id: string
    status: string
  }> {
    const response = await apiScan.post('/onboarding/observation/setup', {
      session_token: sessionToken
    })
    return response.data
  }

  /**
   * Get observation setup status
   */
  static async getObservationStatus(taskId: string): Promise<{
    status: string
    progress: number
  }> {
    const response = await api.get('/onboarding/observation/status', {
      params: { task_id: taskId }
    })
    return response.data
  }

  /**
   * Replace competitor in onboarding
   */
  static async replaceCompetitorInOnboarding(sessionToken: string, competitorIdToReplace: string): Promise<{
    company: any
    similarity_score: number
    common_categories: string[]
    reason: string
  }> {
    const response = await api.post('/onboarding/competitors/replace', {
      session_token: sessionToken,
      competitor_id_to_replace: competitorIdToReplace
    })
    return response.data
  }

  /**
   * Complete onboarding
   */
  static async completeOnboarding(sessionToken: string, userId?: string): Promise<{
    status: string
    company_id: string | null
    competitor_count: number
  }> {
    const response = await api.post('/onboarding/complete', {
      session_token: sessionToken,
      user_id: userId
    })
    return response.data
  }

  // Monitoring endpoints
  /**
   * Get monitoring status for companies
   */
  static async getMonitoringStatus(companyIds: string[]): Promise<{
    statuses: Array<{
      company_id: string
      company_name: string
      is_active: boolean
      last_updated: string | null
      sources_count: {
        social_media: number
        website_pages: number
        news_sources: number
        marketing_sources: number
        seo_signals: number
      }
      last_checks: {
        social_media: string | null
        website_structure: string | null
        press_releases: string | null
        marketing_changes: string | null
        seo_signals: string | null
      }
    }>
  }> {
    const response = await api.get('/companies/monitoring/status', {
      params: { company_ids: companyIds.join(',') }
    })
    return response.data
  }

  /**
   * Get monitoring matrix for a company
   */
  static async getMonitoringMatrix(companyId: string): Promise<{
    company_id: string
    monitoring_config: Record<string, any>
    social_media_sources: Record<string, any>
    website_sources: Record<string, any>
    news_sources: Record<string, any>
    marketing_sources: Record<string, any>
    seo_signals: Record<string, any>
    last_updated: string
  }> {
    const response = await api.get(`/companies/${companyId}/monitoring/matrix`)
    return response.data
  }

  /**
   * Get monitoring changes for companies
   */
  static async getMonitoringChanges(filters: {
    company_ids?: string[]
    change_types?: string[]
    date_from?: string
    date_to?: string
    limit?: number
    offset?: number
  }): Promise<{
    events: Array<{
      id: string
      company_id: string
      change_type: string
      change_summary: string
      detected_at: string
      details: Record<string, any>
    }>
    total: number
    has_more: boolean
  }> {
    const params = new URLSearchParams()
    if (filters.company_ids?.length) params.append('company_ids', filters.company_ids.join(','))
    if (filters.change_types?.length) params.append('change_types', filters.change_types.join(','))
    if (filters.date_from) params.append('date_from', filters.date_from)
    if (filters.date_to) params.append('date_to', filters.date_to)
    if (filters.limit) params.append('limit', filters.limit.toString())
    if (filters.offset) params.append('offset', filters.offset.toString())
    
    const response = await api.get('/companies/monitoring/changes', { params })
    return response.data
  }

  /**
   * Get monitoring stats
   */
  static async getMonitoringStats(): Promise<{
    total_companies: number
    active_monitoring: number
    total_changes_detected: number
    changes_by_type: Record<string, number>
    last_24h_changes: number
  }> {
    const response = await api.get('/companies/monitoring/stats')
    return response.data
  }

  /**
   * Get monitoring preferences
   */
  static async getMonitoringPreferences(): Promise<{
    enabled: boolean
    check_frequency: {
      website_structure: number
      marketing_changes: number
      seo_signals: number
      press_releases: number
    }
    notification_enabled: boolean
    notification_types: string[]
  }> {
    const response = await api.get('/users/monitoring/preferences')
    return response.data
  }

  /**
   * Update monitoring preferences
   */
  static async updateMonitoringPreferences(preferences: {
    enabled?: boolean
    check_frequency?: {
      website_structure?: number
      marketing_changes?: number
      seo_signals?: number
      press_releases?: number
    }
    notification_enabled?: boolean
    notification_types?: string[]
  }): Promise<{
    status: string
    preferences: {
      enabled: boolean
      check_frequency: {
        website_structure: number
        marketing_changes: number
        seo_signals: number
        press_releases: number
      }
      notification_enabled: boolean
      notification_types: string[]
    }
  }> {
    const response = await api.put('/users/monitoring/preferences', preferences)
    return response.data
  }

  /**
   * Get current subscription for authenticated user
   */
  static async getCurrentSubscription(): Promise<{ subscription: Subscription | null }> {
    const response = await api.get<{ subscription: Subscription | null }>('/subscriptions/current')
    return response.data
  }

  /**
   * Check subscription access
   */
  static async checkSubscriptionAccess(): Promise<SubscriptionAccessResponse> {
    const response = await api.get<SubscriptionAccessResponse>('/subscriptions/check-access')
    return response.data
  }

  /**
   * Create or activate subscription after payment
   */
  static async createSubscription(
    paymentData: CreateSubscriptionRequest
  ): Promise<{ subscription: Subscription }> {
    const response = await api.post<{ subscription: Subscription }>('/subscriptions/create', paymentData)
    return response.data
  }

  /**
   * Cancel subscription
   */
  static async cancelSubscription(): Promise<{ status: string; message: string }> {
    const response = await api.post<{ status: string; message: string }>('/subscriptions/cancel')
    return response.data
  }
}

// Export the default api instance for backward compatibility
export default api
