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
  telegram_digest_mode?: 'all' | 'tracked'  // Telegram digest mode: 'all' for all news, 'tracked' for tracked companies only
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
  | 'facebook'
  | 'instagram'
  | 'linkedin'
  | 'youtube'
  | 'tiktok'

export type NewsTopic =
  | 'product'
  | 'strategy'
  | 'finance'
  | 'technology'
  | 'security'
  | 'research'
  | 'community'
  | 'talent'
  | 'regulation'
  | 'market'
  | 'other'

export type SentimentLabel = 'positive' | 'neutral' | 'negative' | 'mixed'

export type AnalyticsPeriod = 'daily' | 'weekly' | 'monthly'

export type ImpactComponentType =
  | 'news_signal'
  | 'pricing_change'
  | 'feature_release'
  | 'funding_event'
  | 'community_event'
  | 'other'

export type AnalyticsEntityType =
  | 'company'
  | 'news_item'
  | 'change_event'
  | 'pricing_snapshot'
  | 'product'
  | 'feature'
  | 'team'
  | 'metric'
  | 'external'

export type RelationshipType =
  | 'causes'
  | 'correlated_with'
  | 'follows'
  | 'amplifies'
  | 'depends_on'

export interface ImpactComponent {
  id: string
  component_type: ImpactComponentType
  weight: number
  score_contribution: number
  metadata: Record<string, any>
}

export interface CompanyAnalyticsSnapshot {
  id: string
  company_id: string
  period: AnalyticsPeriod
  period_start: string
  period_end: string
  news_total: number
  news_positive: number
  news_negative: number
  news_neutral: number
  news_average_sentiment: number
  news_average_priority: number
  pricing_changes: number
  feature_updates: number
  funding_events: number
  impact_score: number
  innovation_velocity: number
  trend_delta: number
  metric_breakdown: Record<string, any>
  components: ImpactComponent[]
}

export interface SnapshotSeries {
  company_id: string
  period: AnalyticsPeriod
  snapshots: CompanyAnalyticsSnapshot[]
}

export interface KnowledgeGraphEdge {
  id: string
  company_id: string | null
  source_entity_type: AnalyticsEntityType
  source_entity_id: string
  target_entity_type: AnalyticsEntityType
  target_entity_id: string
  relationship_type: RelationshipType
  confidence: number
  weight: number
  metadata: Record<string, any>
}

export interface ReportPreset {
  id: string
  user_id: string
  name: string
  description: string | null
  companies: string[]
  filters: Record<string, any>
  visualization_config: Record<string, any>
  is_favorite: boolean
  created_at: string
  updated_at: string
}

export interface ComparisonFilters {
  topics: string[]
  sentiments: string[]
  source_types: string[]
  min_priority?: number | null
}

export interface ComparisonSubjectRequest {
  subject_type: 'company' | 'preset'
  reference_id: string
  label?: string
  color?: string
}

export interface ComparisonCompanySummary {
  id: string
  name: string
  category?: string | null
  logo_url?: string | null
}

export interface AggregatedImpactComponent {
  component_type: string
  score_contribution: number
  weight: number
}

export interface CompanyAnalyticsSnapshotSummary {
  period_start: string
  impact_score: number
  innovation_velocity: number
  trend_delta?: number | null
  news_total: number
  news_positive: number
  news_negative: number
  news_neutral: number
  pricing_changes: number
  feature_updates: number
  funding_events: number
  components: AggregatedImpactComponent[]
}

export interface ComparisonSubjectSummary {
  subject_key: string
  subject_id: string
  subject_type: 'company' | 'preset'
  label: string
  company_ids: string[]
  preset_id?: string | null
  color?: string | null
  companies: ComparisonCompanySummary[]
  filters: ComparisonFilters
}

export interface ComparisonSeriesPoint {
  period_start: string
  impact_score: number
  innovation_velocity: number
  trend_delta?: number | null
  news_total: number
  news_positive: number
  news_negative: number
  news_neutral: number
  pricing_changes: number
  feature_updates: number
  funding_events: number
}

export interface ComparisonSeries {
  subject_key: string
  subject_id: string
  snapshots: ComparisonSeriesPoint[]
}

export interface ComparisonMetricSummary {
  subject_key: string
  subject_id: string
  news_volume: number
  activity_score: number
  avg_priority: number
  impact_score: number
  trend_delta: number
  innovation_velocity: number
  sentiment_distribution: Record<string, number>
  category_distribution: Record<string, number>
  topic_distribution: Record<string, number>
  daily_activity: Record<string, number>
  top_news: Array<{
    id: string
    title: string
    category: string | null
    topic: string | null
    sentiment: string | null
    source_type: string | null
    published_at: string
    source_url: string
    priority_score: number
  }>
  impact_components: AggregatedImpactComponent[]
  snapshot: CompanyAnalyticsSnapshotSummary | null
}

export interface ComparisonResponse {
  generated_at: string
  period: AnalyticsPeriod
  lookback: number
  date_from: string
  date_to: string
  subjects: ComparisonSubjectSummary[]
  metrics: ComparisonMetricSummary[]
  series: ComparisonSeries[]
  change_log: Record<string, CompetitorChangeEvent[]>
  knowledge_graph: Record<string, KnowledgeGraphEdge[]>
}

export interface ComparisonRequestPayload {
  subjects: ComparisonSubjectRequest[]
  period?: AnalyticsPeriod
  lookback?: number
  date_from?: string
  date_to?: string
  filters?: ComparisonFilters
  include_series?: boolean
  include_components?: boolean
  include_change_log?: boolean
  include_knowledge_graph?: boolean
  change_log_limit?: number
  knowledge_graph_limit?: number
  top_news_limit?: number
}

export interface ExportIncludeOptions {
  include_notifications: boolean
  include_presets: boolean
}

export interface AnalyticsExportRequestPayload extends ComparisonRequestPayload {
  export_format?: 'json' | 'pdf' | 'csv'
  include?: ExportIncludeOptions
}

export interface NotificationSettingsSummary {
  notification_frequency: string
  digest_enabled: boolean
  digest_frequency: string
  digest_format: string
  digest_custom_schedule: Record<string, any>
  subscribed_companies: string[]
  interested_categories: string[]
  keywords: string[]
  telegram_enabled: boolean
  telegram_chat_id?: string | null
  telegram_digest_mode: string
  timezone?: string | null
  week_start_day?: number | null
}

export interface AnalyticsExportResponse {
  version: string
  generated_at: string
  export_format?: string | null
  timeframe: {
    period: AnalyticsPeriod
    lookback: number
    date_from: string
    date_to: string
  }
  comparison: ComparisonResponse
  notification_settings?: NotificationSettingsSummary | null
  presets: ReportPreset[]
}

export interface AnalyticsChangeLogResponse {
  events: CompetitorChangeEvent[]
  next_cursor: string | null
  total: number
}

export interface ReportPresetCreateRequest {
  name: string
  description?: string | null
  companies?: string[]
  filters?: Record<string, any>
  visualization_config?: Record<string, any>
  is_favorite?: boolean
}

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
  topic?: NewsTopic | null
  sentiment?: SentimentLabel | null
  raw_snapshot_url?: string | null
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
  // Social media URLs
  facebook_url?: string | null
  instagram_url?: string | null
  linkedin_url?: string | null
  youtube_url?: string | null
  tiktok_url?: string | null
  created_at: string
  updated_at: string
}

// API Response types - Enhanced with backend response formats
export interface ApiResponse<T> {
  data?: T
  message?: string
  status?: 'success' | 'error'
  error?: string
  detail?: string
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
  topic_distribution?: Record<string, Record<string, number>>
  sentiment_distribution?: Record<string, Record<string, number>>
  avg_priority?: Record<string, number>
}

export type ChangeProcessingStatus = 'success' | 'skipped' | 'error'
export type ChangeNotificationStatus = 'pending' | 'sent' | 'failed' | 'skipped'

export interface CompetitorSnapshotReference {
  id: string | null
  parser_version: string | null
  raw_snapshot_url: string | null
  extraction_metadata: Record<string, any>
  warnings: string[]
  processing_status: ChangeProcessingStatus
}

export interface CompetitorChangeEvent {
  id: string
  company_id: string
  source_type: SourceType
  change_summary: string
  changed_fields: Array<Record<string, any>>
  raw_diff: Record<string, any>
  detected_at: string
  processing_status: ChangeProcessingStatus
  notification_status: ChangeNotificationStatus
  current_snapshot: CompetitorSnapshotReference | null
  previous_snapshot: CompetitorSnapshotReference | null
}

export interface CompareRequest {
  company_ids: string[]
  date_from?: string
  date_to?: string
  name?: string
  topics?: NewsTopic[]
  sentiments?: SentimentLabel[]
  source_types?: SourceType[]
  min_priority?: number
}

// Company scanning types
export interface CompanyScanRequest {
  website_url: string
  news_page_url?: string
  max_articles?: number  // Количество статей для сканирования (по умолчанию 10)
  sources?: ScraperSourceOverride[]
}

export interface CompanyScanResult {
  company_preview: {
    name: string
    website: string
    description?: string
    logo_url?: string
    category?: string
  }
  news_preview: {
    total_found: number
    categories: Record<string, number>
    source_types: Record<string, number>
    sample_items: Array<{
      title: string
      source_url: string
      source_type: string
      category: string
      topic?: string | null
      sentiment?: string | null
      raw_snapshot_url?: string | null
      published_at: string
    }>
  }
  all_news_items: Array<{
    title: string
    content?: string
    summary?: string
    source_url: string
    source_type: string
    category: string
    topic?: string | null
    sentiment?: string | null
    raw_snapshot_url?: string | null
    priority_score?: number
    published_at: string
  }>
}

export interface ScraperSourceOverride {
  id?: string
  url?: string
  urls?: string[]
  source_type?: string
  timeout?: number
  retry?: {
    attempts?: number
    backoff_factor?: number
  }
  rate_limit?: {
    requests?: number
    interval?: number
  }
  min_delay?: number
  use_headless?: boolean
  use_proxy?: boolean
  max_articles?: number
  selectors?: string[]
}

export interface CreateCompanyRequest {
  company: {
    name: string
    website: string
    description?: string
    logo_url?: string
    category?: string
    twitter_handle?: string
    github_org?: string
  }
  news_items: Array<{
    title: string
    content?: string
    summary?: string
    source_url: string
    source_type: string
    category: string
    topic?: string | null
    sentiment?: string | null
    raw_snapshot_url?: string | null
    priority_score?: number
    published_at: string
  }>
}

export interface CreateCompanyResponse {
  status: string
  action: 'created' | 'updated'
  company: Company
  news_stats: {
    saved: number
    skipped: number
    total: number
  }
}

// Report types
export type ReportStatus = 'processing' | 'ready' | 'error'

export interface CategoryStats {
  category: string
  technicalCategory: string
  count: number
}

export interface SourceStats {
  url: string
  type: string
  count: number
}

export interface PricingInfo {
  description?: string
  news?: NewsItem[]
}

export interface CompetitorInfo {
  company: Company
  similarity_score: number
  common_categories: string[]
  reason: string
}

export interface Report {
  id: string
  query: string
  status: ReportStatus
  company_id?: string
  company?: Company
  error_message?: string
  created_at: string
  completed_at?: string
  // Данные отчёта (только для status='ready')
  categories?: CategoryStats[]
  news?: NewsItem[]
  sources?: SourceStats[]
  pricing?: PricingInfo
  competitors?: CompetitorInfo[]
}

export interface ReportCreateRequest {
  query: string
}

export interface ReportCreateResponse {
  report_id: string
  status: string
  created_at: string
}

export interface ReportStatusResponse {
  status: ReportStatus
  error?: string
}

export interface ReportsListResponse {
  items: Report[]
  total: number
  limit: number
  offset: number
}

// Onboarding types
export type OnboardingStep = 
  | 'company_input'
  | 'company_card'
  | 'competitor_selection'
  | 'observation_setup'
  | 'subscription_confirm'
  | 'completed'

export interface OnboardingSession {
  id: string
  user_id?: string | null
  session_token: string
  current_step: OnboardingStep
  company_data?: OnboardingCompanyData | null
  selected_competitors?: OnboardingCompetitor[] | null
  observation_config?: OnboardingObservationConfig | null
  created_at: string
  updated_at: string
  completed_at?: string | null
}

export interface OnboardingCompanyData {
  name: string
  website: string
  description: string  // AI-generated description
  logo_url?: string | null
  category?: string | null
  industry_signals?: string[]
  meta_description?: string | null
}

export interface OnboardingCompetitor {
  id: string  // Can be temporary UUID for new competitors
  name: string
  website: string
  logo_url?: string | null
  category?: string | null
  description?: string | null
  ai_description?: string  // AI-generated description (optional, falls back to description)
  similarity_score?: number
  common_categories?: string[]
  reason?: string
}

export interface OnboardingObservationConfig {
  task_id: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  progress?: number
  message?: string
  started_at?: string
  competitor_count?: number
}

export interface OnboardingStartResponse {
  session_token: string
  session_id: string
  current_step: OnboardingStep
}

export interface OnboardingCompanyAnalyzeRequest {
  website_url: string
  session_token: string
}

export interface OnboardingCompanyAnalyzeResponse {
  company: OnboardingCompanyData
  current_step: OnboardingStep
}

// Monitoring types
export interface SocialMediaSources {
  facebook?: { url: string; handle: string | null; last_checked: string } | null
  instagram?: { url: string; handle: string | null; last_checked: string } | null
  linkedin?: { url: string; handle: string | null; last_checked: string } | null
  youtube?: { url: string; handle: string | null; last_checked: string } | null
  tiktok?: { url: string; handle: string | null; last_checked: string } | null
  twitter?: { url: string; handle: string | null; last_checked: string } | null
}

export interface WebsitePage {
  type: 'pricing' | 'features' | 'about' | 'blog' | 'news' | 'careers'
  url: string | null
  found: boolean
}

export interface WebsiteStructure {
  website_url: string
  captured_at: string
  navigation: {
    links: Array<{ url: string; text: string; href: string }>
    count: number
    hash: string
  }
  key_pages: WebsitePage[]
  metadata: {
    title: string | null
    description: string | null
    keywords: string | null
    og_tags: Record<string, string>
    twitter_tags: Record<string, string>
  }
  html_structure: {
    sections: Array<{ tag: string; id: string; class: string }>
    headings: Array<{ level: string; text: string }>
    hash: string
  }
}

export interface SEOSignals {
  website_url: string
  collected_at: string
  meta_tags: {
    title: string | null
    description: string | null
    keywords: string | null
    og_tags: Record<string, string>
    twitter_tags: Record<string, string>
    other_meta: Record<string, string>
  }
  structured_data: Array<Record<string, any>>
  robots_txt: {
    exists: boolean
    content: string | null
    sitemap_urls: string[]
    user_agents: string[]
  }
  sitemap: {
    exists: boolean
    urls: string[]
    sitemap_index: boolean
    sitemap_urls: string[]
  }
  canonical_urls: string[]
  hreflang_tags: Array<{ hreflang: string; href: string }>
}

export interface MonitoringMatrix {
  company_id: string
  monitoring_config: Record<string, any>
  social_media_sources: SocialMediaSources
  website_sources: {
    snapshots: WebsiteStructure[]
    current_snapshot: WebsiteStructure | null
    last_snapshot_at: string | null
    website_url: string | null
    status: string
    key_pages_count: number
  }
  news_sources: {
    last_scraped_at: string | null
    press_release_url: string | null
    press_releases_count: number
    status: string
  }
  marketing_sources: {
    last_checked_at: string | null
    banners: {
      banners: Array<{ url: string; alt: string; hash: string }>
      count: number
      hash: string
      extracted_at: string
    } | null
    pricing: {
      plans: Array<{ name: string; price: string; text: string }>
      count: number
      hash: string
      extracted_at: string
    } | null
    products: {
      products: Array<{ name: string; description: string; url: string | null }>
      count: number
      hash: string
      extracted_at: string
    } | null
    job_postings: {
      jobs: Array<{ name: string; description: string; location: string; url: string | null }>
      count: number
      hash: string
      extracted_at: string
    } | null
  }
  seo_signals: {
    current_signals: SEOSignals | null
    last_collected_at: string | null
    meta_tags_count: number
    structured_data_count: number
    robots_txt_exists: boolean
    sitemap_exists: boolean
    history: SEOSignals[]
  }
  last_updated: string
}

export interface MonitoringStatus {
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
}

export interface MonitoringChangeEvent {
  id: string
  company_id: string
  change_type: 'navigation' | 'key_pages' | 'metadata' | 'banners' | 'pricing' | 'products' | 'job_postings' | 'meta_tags' | 'structured_data' | 'sitemap'
  change_summary: string
  detected_at: string
  details: Record<string, any>
}

export interface MonitoringStats {
  total_companies: number
  active_monitoring: number
  total_changes_detected: number
  changes_by_type: Record<string, number>
  last_24h_changes: number
}

export interface MonitoringPreferences {
  enabled: boolean
  check_frequency: {
    website_structure: number  // hours
    marketing_changes: number  // hours
    seo_signals: number  // hours
    press_releases: number  // hours
  }
  notification_enabled: boolean
  notification_types: string[]
}

export interface OnboardingCompanyResponse {
  company: OnboardingCompanyData
  current_step: OnboardingStep
}

export interface OnboardingCompetitorsSuggestResponse {
  competitors: Array<{
    company: OnboardingCompetitor
    similarity_score: number
    common_categories: string[]
    reason: string
  }>
  total: number
}

export interface OnboardingCompetitorReplaceRequest {
  session_token: string
  competitor_id_to_replace?: string
}

export interface OnboardingCompetitorReplaceResponse {
  company: OnboardingCompetitor
  similarity_score: number
  common_categories: string[]
  reason: string
}

export interface OnboardingCompetitorsSelectRequest {
  session_token: string
  selected_competitor_ids: string[]
}

export interface OnboardingCompetitorsSelectResponse {
  status: string
  selected_count: number
  current_step: OnboardingStep
}

export interface OnboardingObservationSetupRequest {
  session_token: string
}

export interface OnboardingObservationSetupResponse {
  task_id: string
  status: string
  message: string
}

export interface OnboardingObservationStatusResponse {
  task_id: string
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'completed_with_errors'
  progress?: number
  message?: string
  current_step?: string
  current_company?: string
  total?: number
  completed?: number
  errors?: number
}

export interface OnboardingCompleteRequest {
  session_token: string
  user_id?: string
}

export interface OnboardingCompleteResponse {
  status: string
  message: string
  company_id: string
  competitor_count: number
  companies?: Array<{
    id: string
    name: string
    website?: string
  }>
  completed_at?: string | null
}

// Subscription types
export enum SubscriptionStatus {
  TRIAL = 'trial',
  ACTIVE = 'active',
  CANCELLED = 'cancelled',
  EXPIRED = 'expired'
}

export interface Subscription {
  id: string
  status: SubscriptionStatus
  plan_type: string
  price: number
  currency: string
  trial_started_at?: string | null
  trial_ends_at?: string | null
  started_at?: string | null
  expires_at?: string | null
  days_remaining: number
  is_active: boolean
}

export interface SubscriptionAccessResponse {
  has_access: boolean
  days_remaining?: number | null
  reason?: string | null
  status?: SubscriptionStatus | null
}

export interface CreateSubscriptionRequest {
  payment_provider: string
  payment_subscription_id: string
  subscription_id?: string | null
}