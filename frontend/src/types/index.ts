// User types - Enhanced with backend Pydantic schemas
export interface User {
  id: string
  email: string
  full_name: string | null
  is_active: boolean
  is_verified: boolean
  created_at: string
  updated_at: string
}

export interface UserCreateRequest {
  email: string
  password: string
  full_name: string
}

export interface UserUpdateRequest {
  full_name?: string
  is_active?: boolean
}

export interface UserLoginRequest {
  email: string
  password: string
}

export interface PasswordResetRequest {
  email: string
}

export interface PasswordResetConfirm {
  token: string
  new_password: string
}

export interface UserPreferences {
  id: string
  user_id: string
  subscribed_companies: string[]
  interested_categories: NewsCategory[]
  keywords: string[]
  notification_frequency: NotificationFrequency
  created_at: string
  updated_at: string
}

export interface DigestSettings {
  digest_enabled: boolean
  digest_frequency: DigestFrequency
  digest_custom_schedule: CustomSchedule | null
  digest_format: DigestFormat
  digest_include_summaries: boolean
  telegram_chat_id: string | null
  telegram_enabled: boolean
  timezone?: string  // User's timezone (e.g., "UTC", "America/New_York", "Europe/Moscow")
  week_start_day?: number  // 0=Sunday, 1=Monday
}

export type DigestFrequency = 'daily' | 'weekly' | 'custom'
export type DigestFormat = 'short' | 'detailed'

export interface CustomSchedule {
  time: string  // "09:00"
  days: number[]  // [1,2,3,4,5] for Monday-Friday
  timezone: string  // "UTC"
}

// News types - Enhanced with backend enums and schemas
export type NewsCategory = 
  | 'product_update'
  | 'pricing_change'
  | 'strategic_announcement'
  | 'technical_update'
  | 'funding_news'
  | 'research_paper'
  | 'community_event'
  | 'partnership'
  | 'acquisition'
  | 'integration'
  | 'security_update'
  | 'api_update'
  | 'model_release'
  | 'performance_improvement'
  | 'feature_deprecation'

export type SourceType = 
  | 'blog'
  | 'twitter'
  | 'github'
  | 'reddit'
  | 'news_site'
  | 'press_release'

export interface NewsCategoryInfo {
  value: NewsCategory
  description: string
}

export interface SourceTypeInfo {
  value: SourceType
  description: string
}

export type NotificationFrequency = 
  | 'realtime'
  | 'daily'
  | 'weekly'
  | 'never'

// Enhanced NewsItem with backend improvements
export interface NewsItem {
  id: string
  title: string
  title_truncated: string
  content: string | null
  summary: string | null
  source_url: string
  source_type: SourceType
  company_id: string | null
  category: NewsCategory | null
  priority_score: number
  priority_level: 'High' | 'Medium' | 'Low'
  published_at: string
  created_at: string
  updated_at: string
  is_recent: boolean
  company?: Company | null
  keywords?: NewsKeyword[]
  activities?: UserActivity[]
}

export interface NewsKeyword {
  keyword: string
  relevance: number
  created_at: string
}

export interface NewsStats {
  total_count: number
  category_counts: Record<string, number>
  source_type_counts: Record<string, number>
  recent_count: number
  high_priority_count: number
}

// Company types
export interface Company {
  id: string
  name: string
  website: string
  description: string
  logo_url: string
  category: string
  twitter_handle: string
  github_org: string
  created_at: string
  updated_at: string
}

// API Response types - Enhanced with backend response formats
export interface ApiResponse<T> {
  data?: T
  message?: string
  status?: 'success' | 'error'
  error?: string
  details?: Record<string, any>
  status_code?: number
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  limit: number
  offset: number
  has_more: boolean
  filters?: Record<string, any>
}

export interface NewsListResponse extends PaginatedResponse<NewsItem> {
  filters: {
    category?: NewsCategory | null
    company_id?: string | null
    source_type?: SourceType | null
    search_query?: string | null
    min_priority?: number | null
  }
}

export interface NewsSearchResponse extends PaginatedResponse<NewsItem> {
  query: string
  filters: {
    category?: NewsCategory | null
    source_type?: SourceType | null
    company_id?: string | null
  }
}

// Auth types - Enhanced with backend schemas
export interface LoginRequest {
  email: string
  password: string
}

export interface RegisterRequest {
  email: string
  password: string
  full_name: string
}

export interface AuthResponse {
  access_token: string
  refresh_token: string
  token_type: string
  user: User
}

export interface RefreshTokenRequest {
  refresh_token: string
}

export interface RefreshTokenResponse {
  access_token: string
  token_type: string
}

// Digest types
export interface Digest {
  date: string
  news_count: number
  categories: {
    product_updates: NewsItem[]
    pricing_changes: NewsItem[]
    strategic_announcements: NewsItem[]
    technical_updates: NewsItem[]
    funding_news: NewsItem[]
    research_papers: NewsItem[]
    community_events: NewsItem[]
  }
}

// Filter types - Enhanced with backend parameters
export interface NewsFilter {
  category?: NewsCategory
  company_id?: string
  company_ids?: string[]
  source_type?: SourceType
  search_query?: string
  min_priority?: number
  start_date?: string
  end_date?: string
  limit?: number
  offset?: number
}

// Search types - Enhanced with backend search schema
export interface SearchRequest {
  query: string
  category?: NewsCategory
  source_type?: SourceType
  company_id?: string
  limit?: number
  offset?: number
}

// Activity types
export type ActivityType = 'viewed' | 'favorited' | 'marked_read' | 'shared'

export interface UserActivity {
  id: string
  user_id: string
  news_id: string
  action: ActivityType
  created_at: string
}

// Notification types
export type NotificationType =
  | 'new_news'
  | 'company_active'
  | 'pricing_change'
  | 'funding_announcement'
  | 'product_launch'
  | 'category_trend'
  | 'keyword_match'
  | 'competitor_milestone'

export type NotificationPriority = 'low' | 'medium' | 'high'

export interface Notification {
  id: string
  type: NotificationType
  title: string
  message: string
  data: Record<string, any>
  is_read: boolean
  priority: NotificationPriority
  created_at: string
}

export interface NotificationSettings {
  id: string
  enabled: boolean
  notification_types: Record<string, boolean>
  min_priority_score: number
  company_alerts: boolean
  category_trends: boolean
  keyword_alerts: boolean
}

// Competitor analysis types
export interface CompetitorComparison {
  id?: string
  companies: Company[]
  date_from: string
  date_to: string
  metrics: ComparisonMetrics
  created_at?: string
}

export interface ComparisonMetrics {
  news_volume: Record<string, number>
  category_distribution: Record<string, Record<string, number>>
  activity_score: Record<string, number>
  daily_activity?: Record<string, Record<string, number>>
  top_news?: Record<string, NewsItem[]>
}

export interface CompareRequest {
  company_ids: string[]
  date_from?: string
  date_to?: string
  name?: string
}
