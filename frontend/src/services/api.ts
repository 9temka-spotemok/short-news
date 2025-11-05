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
  }): Promise<{
    companies: Company[]
    date_from: string
    date_to: string
    metrics: {
      news_volume: Record<string, number>
      category_distribution: Record<string, Record<string, number>>
      activity_score: Record<string, number>
      daily_activity?: Record<string, Record<string, number>>
      top_news?: Record<string, any[]>
    }
  }> {
    console.log('API Service - compareCompanies request:', request)
    console.log('API Service - request type:', typeof request)
    console.log('API Service - company_ids type:', typeof request.company_ids)
    console.log('API Service - company_ids is array:', Array.isArray(request.company_ids))
    
    const response = await api.post('/competitors/compare', request)
    return response.data
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

  // Export methods
  static async exportAnalysis(
    analysisData: any,
    format: 'json' | 'pdf' | 'csv'
  ): Promise<void> {
    switch (format) {
      case 'json':
        this.exportAsJson(analysisData)
        break
      case 'pdf':
        await this.exportAsPdf(analysisData)
        break
      case 'csv':
        this.exportAsCsv(analysisData)
        break
    }
  }

  private static exportAsJson(data: any): void {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `competitor-analysis-${new Date().toISOString().split('T')[0]}.json`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  private static async exportAsPdf(data: any): Promise<void> {
    // Для PDF используем простой HTML-to-PDF подход
    const html = this.generatePdfHtml(data)
    const printWindow = window.open('', '_blank')
    if (printWindow) {
      printWindow.document.write(html)
      printWindow.document.close()
      printWindow.focus()
      printWindow.print()
      printWindow.close()
    }
  }

  private static exportAsCsv(data: any): void {
    const csvContent = this.generateCsvContent(data)
    const blob = new Blob([csvContent], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `competitor-analysis-${new Date().toISOString().split('T')[0]}.csv`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  private static generatePdfHtml(data: any): string {
    const companies = data.companies || []
    const metrics = data.metrics || {}
    const report = data.report || {}
    const mainCompany = report.company || companies[0]
    
    return `
      <!DOCTYPE html>
      <html>
      <head>
        <title>Competitor Analysis Report - ${mainCompany?.name || 'Unknown Company'}</title>
        <style>
          body { font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }
          h1 { color: #2563eb; border-bottom: 2px solid #2563eb; padding-bottom: 10px; }
          h2 { color: #374151; margin-top: 30px; border-bottom: 1px solid #e5e7eb; padding-bottom: 5px; }
          h3 { color: #6b7280; margin-top: 20px; }
          table { width: 100%; border-collapse: collapse; margin: 15px 0; }
          th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
          th { background-color: #f3f4f6; font-weight: bold; }
          .metric-card { display: inline-block; margin: 10px; padding: 15px; border: 1px solid #ddd; border-radius: 8px; background-color: #f9fafb; }
          .section { margin: 25px 0; padding: 15px; border: 1px solid #e5e7eb; border-radius: 8px; }
          .highlight { background-color: #fef3c7; padding: 10px; border-radius: 5px; margin: 10px 0; }
        </style>
      </head>
      <body>
        <h1>Competitor Analysis Report</h1>
        <div class="highlight">
          <p><strong>Company:</strong> ${mainCompany?.name || 'N/A'}</p>
          <p><strong>Analysis Date:</strong> ${report.analysisDate ? new Date(report.analysisDate).toLocaleDateString() : 'N/A'}</p>
          <p><strong>Date Range:</strong> ${data.date_from} to ${data.date_to}</p>
          <p><strong>Analysis Mode:</strong> ${report.analysisMode || 'N/A'}</p>
        </div>
        
        <div class="section">
          <h2>Company Overview</h2>
          <table>
            <tr><th>Name</th><th>Category</th><th>Website</th><th>Description</th></tr>
            <tr>
              <td>${mainCompany?.name || 'N/A'}</td>
              <td>${mainCompany?.category || 'N/A'}</td>
              <td>${mainCompany?.website || 'N/A'}</td>
              <td>${mainCompany?.description || 'N/A'}</td>
            </tr>
          </table>
        </div>
        
        <div class="section">
          <h2>Business Intelligence</h2>
          <p><strong>Total Activity:</strong> ${report.businessIntelligence?.totalActivity || 0}</p>
          <p><strong>Activity Score:</strong> ${report.businessIntelligence?.activityScore?.toFixed(2) || '0.00'}/10</p>
          <p><strong>Competitor Count:</strong> ${report.businessIntelligence?.competitorCount || 0}</p>
          
          <h3>Business Intelligence Metrics</h3>
          <table>
            <tr><th>Metric</th><th>Count</th></tr>
            <tr><td>Funding News</td><td>${report.businessIntelligence?.metrics?.funding_news || 0}</td></tr>
            <tr><td>Partnerships</td><td>${report.businessIntelligence?.metrics?.partnership || 0}</td></tr>
            <tr><td>Acquisitions</td><td>${report.businessIntelligence?.metrics?.acquisition || 0}</td></tr>
            <tr><td>Strategic Announcements</td><td>${report.businessIntelligence?.metrics?.strategic_announcement || 0}</td></tr>
            <tr><td>Integrations</td><td>${report.businessIntelligence?.metrics?.integration || 0}</td></tr>
          </table>
          
          <h3>Top Activity Categories</h3>
          <table>
            <tr><th>Category</th><th>Count</th></tr>
            ${Object.entries(report.businessIntelligence?.metrics || {})
              .filter(([key]) => !['funding_news', 'partnership', 'acquisition', 'strategic_announcement', 'integration'].includes(key))
              .sort(([, a], [, b]) => Number(b) - Number(a))
              .slice(0, 5)
              .map(([cat, count]) => `<tr><td>${cat.replace(/_/g, ' ').replace(/\\b\\w/g, l => l.toUpperCase())}</td><td>${count}</td></tr>`)
              .join('')}
          </table>
        </div>
        
        <div class="section">
          <h2>Innovation & Technology</h2>
          <p><strong>Total News:</strong> ${report.innovationTechnology?.totalNews || 0}</p>
          <p><strong>Technical Activity:</strong> ${report.innovationTechnology?.technicalActivity || 0}</p>
          
          <h3>Technology Metrics</h3>
          <table>
            <tr><th>Category</th><th>Count</th></tr>
            <tr><td>Technical Updates</td><td>${report.innovationTechnology?.metrics?.technical_update || 0}</td></tr>
            <tr><td>API Updates</td><td>${report.innovationTechnology?.metrics?.api_update || 0}</td></tr>
            <tr><td>Research Papers</td><td>${report.innovationTechnology?.metrics?.research_paper || 0}</td></tr>
            <tr><td>Model Releases</td><td>${report.innovationTechnology?.metrics?.model_release || 0}</td></tr>
            <tr><td>Performance Improvements</td><td>${report.innovationTechnology?.metrics?.performance_improvement || 0}</td></tr>
            <tr><td>Security Updates</td><td>${report.innovationTechnology?.metrics?.security_update || 0}</td></tr>
          </table>
        </div>
        
        <div class="section">
          <h2>Team & Culture</h2>
          <p><strong>Total News:</strong> ${report.teamCulture?.totalNews || 0}</p>
          <p><strong>Activity Score:</strong> ${report.teamCulture?.activityScore?.toFixed(2) || '0.00'}/10</p>
          <p><strong>Team Activity:</strong> ${report.teamCulture?.teamActivity || 0}</p>
          
          <h3>Team Metrics</h3>
          <table>
            <tr><th>Category</th><th>Count</th></tr>
            <tr><td>Community Events</td><td>${report.teamCulture?.metrics?.community_event || 0}</td></tr>
            <tr><td>Strategic Announcements</td><td>${report.teamCulture?.metrics?.strategic_announcement || 0}</td></tr>
            <tr><td>Research Papers</td><td>${report.teamCulture?.metrics?.research_paper || 0}</td></tr>
          </table>
        </div>
        
        <div class="section">
          <h2>Market Position</h2>
          <p><strong>News Volume:</strong> ${report.marketPosition?.metrics?.news_volume || 0}</p>
          <p><strong>Activity Score:</strong> ${report.marketPosition?.metrics?.activity_score?.toFixed(2) || '0.00'}/10</p>
          <p><strong>Total Market News:</strong> ${report.marketPosition?.totalNews || 0}</p>
          <p><strong>Competitors:</strong> ${report.marketPosition?.competitors?.length || 0}</p>
          
          <h3>Top Categories</h3>
          <table>
            <tr><th>Category</th><th>Count</th></tr>
            ${Object.entries(report.marketPosition?.metrics?.category_distribution || {})
              .sort(([, a], [, b]) => Number(b) - Number(a))
              .map(([cat, count]) => `<tr><td>${cat.replace(/_/g, ' ').replace(/\\b\\w/g, l => l.toUpperCase())}</td><td>${count}</td></tr>`)
              .join('')}
          </table>
        </div>
        
        <div class="section">
          <h2>News Volume Comparison</h2>
          <table>
            <tr><th>Company</th><th>Total News</th><th>Activity Score</th><th>Avg Priority</th></tr>
            ${companies.map((company: any) => {
              const volume = metrics.news_volume?.[company.id] || 0
              const activity = metrics.activity_score?.[company.id] || 0
              const priority = metrics.avg_priority?.[company.id] || 0
              return `<tr><td>${company.name}</td><td>${volume}</td><td>${activity.toFixed(2)}</td><td>${priority.toFixed(2)}</td></tr>`
            }).join('')}
          </table>
        </div>
        
        <div class="section">
          <h2>Detailed Category Distribution</h2>
          ${companies.map((company: any) => {
            const categories = metrics.category_distribution?.[company.id] || {}
            const categoryRows = Object.entries(categories).map(([cat, count]) => 
              `<tr><td>${cat.replace(/_/g, ' ').replace(/\\b\\w/g, l => l.toUpperCase())}</td><td>${count}</td></tr>`
            ).join('')
            return `
              <h3>${company.name}</h3>
              <table>
                <tr><th>Category</th><th>Count</th></tr>
                ${categoryRows}
              </table>
            `
          }).join('')}
        </div>
      </body>
      </html>
    `
  }

  private static generateCsvContent(data: any): string {
    const companies = data.companies || []
    const metrics = data.metrics || {}
    const report = data.report || {}
    const mainCompany = report.company || companies[0]
    
    let csv = `Competitor Analysis Report - ${mainCompany?.name || 'Unknown Company'}\n`
    csv += `Analysis Date,${report.analysisDate ? new Date(report.analysisDate).toLocaleDateString() : 'N/A'}\n`
    csv += `Date Range,${data.date_from} to ${data.date_to}\n`
    csv += `Analysis Mode,${report.analysisMode || 'N/A'}\n\n`
    
    // Company Overview
    csv += `COMPANY OVERVIEW\n`
    csv += `Name,Category,Website,Description\n`
    csv += `"${mainCompany?.name || 'N/A'}","${mainCompany?.category || 'N/A'}","${mainCompany?.website || 'N/A'}","${mainCompany?.description || 'N/A'}"\n\n`
    
    // Business Intelligence
    csv += `BUSINESS INTELLIGENCE\n`
    csv += `Metric,Value\n`
    csv += `Total Activity,${report.businessIntelligence?.totalActivity || 0}\n`
    csv += `Activity Score,${report.businessIntelligence?.activityScore?.toFixed(2) || '0.00'}\n`
    csv += `Competitor Count,${report.businessIntelligence?.competitorCount || 0}\n`
    csv += `Funding News,${report.businessIntelligence?.metrics?.funding_news || 0}\n`
    csv += `Partnerships,${report.businessIntelligence?.metrics?.partnership || 0}\n`
    csv += `Acquisitions,${report.businessIntelligence?.metrics?.acquisition || 0}\n`
    csv += `Strategic Announcements,${report.businessIntelligence?.metrics?.strategic_announcement || 0}\n`
    csv += `Integrations,${report.businessIntelligence?.metrics?.integration || 0}\n\n`
    
    // Innovation & Technology
    csv += `INNOVATION & TECHNOLOGY\n`
    csv += `Metric,Value\n`
    csv += `Total News,${report.innovationTechnology?.totalNews || 0}\n`
    csv += `Technical Activity,${report.innovationTechnology?.technicalActivity || 0}\n`
    csv += `Technical Updates,${report.innovationTechnology?.metrics?.technical_update || 0}\n`
    csv += `API Updates,${report.innovationTechnology?.metrics?.api_update || 0}\n`
    csv += `Research Papers,${report.innovationTechnology?.metrics?.research_paper || 0}\n`
    csv += `Model Releases,${report.innovationTechnology?.metrics?.model_release || 0}\n`
    csv += `Performance Improvements,${report.innovationTechnology?.metrics?.performance_improvement || 0}\n`
    csv += `Security Updates,${report.innovationTechnology?.metrics?.security_update || 0}\n\n`
    
    // Team & Culture
    csv += `TEAM & CULTURE\n`
    csv += `Metric,Value\n`
    csv += `Total News,${report.teamCulture?.totalNews || 0}\n`
    csv += `Activity Score,${report.teamCulture?.activityScore?.toFixed(2) || '0.00'}\n`
    csv += `Team Activity,${report.teamCulture?.teamActivity || 0}\n`
    csv += `Community Events,${report.teamCulture?.metrics?.community_event || 0}\n`
    csv += `Strategic Announcements,${report.teamCulture?.metrics?.strategic_announcement || 0}\n`
    csv += `Research Papers,${report.teamCulture?.metrics?.research_paper || 0}\n\n`
    
    // Market Position
    csv += `MARKET POSITION\n`
    csv += `Metric,Value\n`
    csv += `News Volume,${report.marketPosition?.metrics?.news_volume || 0}\n`
    csv += `Activity Score,${report.marketPosition?.metrics?.activity_score?.toFixed(2) || '0.00'}\n`
    csv += `Total Market News,${report.marketPosition?.totalNews || 0}\n`
    csv += `Competitors,${report.marketPosition?.competitors?.length || 0}\n\n`
    
    // News Volume Comparison
    csv += `NEWS VOLUME COMPARISON\n`
    csv += `Company,Category,Total News,Activity Score,Avg Priority\n`
    companies.forEach((company: any) => {
      const volume = metrics.news_volume?.[company.id] || 0
      const activity = metrics.activity_score?.[company.id] || 0
      const priority = metrics.avg_priority?.[company.id] || 0
      csv += `"${company.name}","${company.category}",${volume},${activity.toFixed(2)},${priority.toFixed(2)}\n`
    })
    
    return csv
  }
}

// Export the default api instance for backward compatibility
export default api
