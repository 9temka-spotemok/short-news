// User types
export interface User {
  id: string
  email: string
  full_name: string
  is_active: boolean
  is_verified: boolean
  created_at: string
  updated_at: string
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

// News types
export type NewsCategory = 
  | 'product_update'
  | 'pricing_change'
  | 'strategic_announcement'
  | 'technical_update'
  | 'funding_news'
  | 'research_paper'
  | 'community_event'

export type SourceType = 
  | 'blog'
  | 'twitter'
  | 'github'
  | 'reddit'
  | 'news_site'
  | 'press_release'

export type NotificationFrequency = 
  | 'realtime'
  | 'daily'
  | 'weekly'
  | 'never'

export interface NewsItem {
  id: string
  title: string
  content: string
  summary: string
  source_url: string
  source_type: SourceType
  company_id: string
  category: NewsCategory
  priority_score: number
  published_at: string
  created_at: string
  updated_at: string
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

// API Response types
export interface ApiResponse<T> {
  data: T
  message: string
  status: 'success' | 'error'
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  pages: number
  limit: number
  offset: number
}

// Auth types
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

// Filter types
export interface NewsFilter {
  category?: NewsCategory
  company?: string
  date_from?: string
  date_to?: string
  keywords?: string[]
  limit?: number
  offset?: number
}

// Search types
export interface SearchRequest {
  query: string
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
