import AddCompetitorModal from '@/components/AddCompetitorModal'
import CompanyMultiSelect from '@/components/CompanyMultiSelect'
import CompanySearchModal from '@/components/CompanySearchModal'
import TrackedCompaniesManager from '@/components/TrackedCompaniesManager'
import AddCompetitorsModal from '@/components/dashboard/AddCompetitorsModal'
import ConfirmDeleteModal from '@/components/dashboard/ConfirmDeleteModal'
import FilterChips from '@/components/dashboard/FilterChips'
import NewsGroupedList from '@/components/dashboard/NewsGroupedList'
import QuickLinks from '@/components/dashboard/QuickLinks'
import Recommendations from '@/components/dashboard/Recommendations'
import ReportCard from '@/components/dashboard/ReportCard'
import SkeletonLoader from '@/components/dashboard/SkeletonLoader'
import StatsCards from '@/components/dashboard/StatsCards'
import MonitoringStatusCard from '@/components/monitoring/MonitoringStatusCard'
import SubscriptionBanner from '@/components/subscription/SubscriptionBanner'
import api, { ApiService } from '@/services/api'
import { useAuthStore } from '@/store/authStore'
import type { Company, Report } from '@/types'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { formatDistance } from 'date-fns'
import { enUS } from 'date-fns/locale'
import { Bell, CheckCircle, ChevronDown, ChevronUp, ExternalLink, Github, Globe, Search, Sparkles, TrendingUp, Twitter } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import toast from 'react-hot-toast'
import { useNavigate } from 'react-router-dom'
 

interface NewsItem {
  id: string
  title: string
  summary: string
  source_url: string
  source_type: string
  category: string
  published_at: string
  created_at: string
  company?: {
    id: string
    name: string
    website?: string
  }
}

interface DashboardStats {
  todayNews: number
  totalNews: number
  categoriesBreakdown: { category: string; technicalCategory?: string; count: number; percentage: number }[]
}

interface DigestData {
  date_from: string
  date_to: string
  news_count: number
  format: string
  categories?: Record<string, NewsItem[]>
  companies?: Record<string, {
    company: {
      id: string
      name: string
      logo_url?: string
    }
    news: NewsItem[]
    stats: {
      total: number
      by_category: Record<string, number>
    }
  }>
  companies_count?: number
  statistics?: {
    total_news: number
    by_category: Record<string, number>
    by_source: Record<string, number>
    avg_priority: number
  }
}

// Category labels - константа, вынесена за пределы компонента
const categoryLabels: Record<string, string> = {
  'product_update': 'Product Updates',
  'technical_update': 'Technical Updates',
  'strategic_announcement': 'Strategic Announcements',
  'funding_news': 'Funding News',
  'pricing_change': 'Pricing Changes',
  'research_paper': 'Research Papers',
  'community_event': 'Community Events',
  'partnership': 'Partnerships',
  'acquisition': 'Acquisitions',
  'integration': 'Integrations',
  'security_update': 'Security Updates',
  'api_update': 'API Updates',
  'model_release': 'Model Releases',
  'performance_improvement': 'Performance Improvements',
  'feature_deprecation': 'Feature Deprecations',
}

export default function DashboardPage() {
  const { isAuthenticated, user, accessToken } = useAuthStore()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState(() => {
    const saved = localStorage.getItem('dashboard-activeTab')
    // For new users without saved preference, default to 'discover'
    return saved || 'discover'
  })
  
  // State for onboarding
  const [showOnboarding, setShowOnboarding] = useState(false)
  const [recentNews, setRecentNews] = useState<NewsItem[]>([])
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [loading, setLoading] = useState(true)
  const isFetchingRef = useRef(false) // Ref для отслеживания активного запроса
  const [selectedCategory, setSelectedCategory] = useState('')
  const [selectedCompanies, setSelectedCompanies] = useState<string[]>([])
  const [selectedDate, setSelectedDate] = useState('')
  const [availableCategories, setAvailableCategories] = useState<{ value: string; description: string }[]>([])
  const [showAllCategories, setShowAllCategories] = useState(false)
  const [showAllCompanies, setShowAllCompanies] = useState(false)
  // Load showTrackedOnly state from localStorage, default to false
  const [showTrackedOnly, setShowTrackedOnly] = useState(() => {
    const saved = localStorage.getItem('dashboard-showTrackedOnly')
    return saved ? JSON.parse(saved) : false
  })

  // Companies list state
  const [companies, setCompanies] = useState<Company[]>([])
  const [companiesLoading, setCompaniesLoading] = useState(false)
  const [companiesSearchQuery, setCompaniesSearchQuery] = useState('')
  const [companiesTotal, setCompaniesTotal] = useState(0)
  const [companiesOffset, setCompaniesOffset] = useState(0)
  const companiesLimit = 20
  const [expandedCompanies, setExpandedCompanies] = useState<Set<string>>(new Set())
  
  // Состояние для источников новостей компаний
  const [companySources, setCompanySources] = useState<Record<string, {
    sources: Array<{ url: string; type: string; count: number }>
    loading: boolean
  }>>({})

  // Состояние для модального окна добавления конкурента
  const [showAddModal, setShowAddModal] = useState(false)
  
  // Состояние для модального окна поиска компаний
  const [showSearchModal, setShowSearchModal] = useState(false)

  // Состояния для табов и данных компаний
  const [companyTabs, setCompanyTabs] = useState<Record<string, string>>({})
  const [companyNews, setCompanyNews] = useState<Record<string, NewsItem[]>>({})
  const [companyCategories, setCompanyCategories] = useState<Record<string, { category: string; technicalCategory: string; count: number }[]>>({})
  const [companyPricing, setCompanyPricing] = useState<Record<string, { news: NewsItem[]; description?: string }>>({})
  const [loadingCompanyData, setLoadingCompanyData] = useState<Record<string, { news: boolean; categories: boolean; pricing: boolean }>>({})

  // State для Discover/Reports
  const [discoverSearchQuery, setDiscoverSearchQuery] = useState('')
  const [reports, setReports] = useState<Report[]>([])
  const [expandedReports, setExpandedReports] = useState<Set<string>>(new Set())
  const [reportTabs, setReportTabs] = useState<Record<string, 'news' | 'sources' | 'pricing' | 'competitors' | 'monitoring'>>({})
  const [reportData, setReportData] = useState<Record<string, Report>>({})
  const [pollingIntervals, setPollingIntervals] = useState<Record<string, NodeJS.Timeout>>({})
  const [reportsLoaded, setReportsLoaded] = useState(false) // Флаг для отслеживания загрузки отчётов
  const [deleteModal, setDeleteModal] = useState<{ isOpen: boolean; report: Report | null }>({ isOpen: false, report: null })
  const [isDeleting, setIsDeleting] = useState(false)
  const [addCompetitorsModal, setAddCompetitorsModal] = useState<{ isOpen: boolean; report: Report | null }>({ isOpen: false, report: null })
  const [isCreatingReport, setIsCreatingReport] = useState(false) // Состояние загрузки для создания отчёта
  const [inputType, setInputType] = useState<'url' | 'text' | null>(null) // Для динамической иконки в поиске
  const [isValidInput, setIsValidInput] = useState(false) // Для валидации ввода
  const searchInputRef = useRef<HTMLInputElement>(null) // Ref для автофокуса


  // Save showTrackedOnly locally and persist telegram_digest_mode to backend
  const handleToggleTrackedOnly = async (value: boolean) => {
    setShowTrackedOnly(value)
    localStorage.setItem('dashboard-showTrackedOnly', JSON.stringify(value))
    // try {
    //   await api.put('/users/preferences/digest', {
    //     telegram_digest_mode: value ? 'tracked' : 'all',
    //   })
    // } catch (err) {
    //   console.error('Failed to persist telegram_digest_mode', err)
    // }
  }

  // Save active tab state to localStorage when it changes
  const handleTabChange = (tabId: string) => {
    setActiveTab(tabId)
    localStorage.setItem('dashboard-activeTab', tabId)
  }

  // Notifications are handled globally in NotificationCenter
  
  // Digest state
  const [digest, setDigest] = useState<DigestData | null>(null)
  const [digestLoading, setDigestLoading] = useState(false)
  const [digestError, setDigestError] = useState<string | null>(null)
  
  // Note: We now build statistics locally instead of using useNewsAnalytics
  // const { stats: allStats, categoryTrends } = useNewsAnalytics()
  
  // Debug authentication state
  useEffect(() => {
    console.log('DashboardPage auth state:', {
      isAuthenticated,
      user: user?.email,
      hasToken: !!accessToken,
      tokenPreview: accessToken ? accessToken.substring(0, 50) + '...' : 'None'
    })
  }, [isAuthenticated, user, accessToken])

  const tabs = [
    { 
      id: 'discover', 
      label: 'Discover',
      icon: Search,
      description: 'Search and add competitors to track'
    },
    { 
      id: 'overview', 
      label: 'Overview',
      icon: TrendingUp,
      description: 'View statistics and recent news'
    },
    { 
      id: 'competitors', 
      label: 'My Competitors',
      icon: Globe,
      description: 'Manage your tracked competitors'
    },
    { 
      id: 'digest', 
      label: 'Digests',
      icon: Bell,
      description: 'Generate personalized news digests'
    },
  ]

  // Create reverse mapping from display names to technical names
  const categoryTechnicalNames: Record<string, string> = Object.fromEntries(
    Object.entries(categoryLabels).map(([tech, display]) => [display, tech])
  )

  // Load categories/source types metadata
  const { data: categoriesData } = useQuery({
    queryKey: ['news-categories'],
    queryFn: ApiService.getNewsCategories,
    staleTime: 1000 * 60 * 60,
  })

  // Load user preferences for personalization
  const { data: userPreferences } = useQuery({
    queryKey: ['user-preferences'],
    queryFn: ApiService.getUserPreferences,
    staleTime: 1000 * 60 * 5, // 5 minutes
  })

  // Load monitoring status for subscribed companies
  const subscribedCompanies = userPreferences?.subscribed_companies || []
  const { data: monitoringStatus, isLoading: monitoringLoading } = useQuery({
    queryKey: ['monitoring-status', subscribedCompanies],
    queryFn: () => ApiService.getMonitoringStatus(subscribedCompanies),
    enabled: subscribedCompanies.length > 0,
    staleTime: 1000 * 60 * 5, // 5 minutes
  })

  // Fetch dashboard data function - wrapped in useCallback to use latest values
  const fetchDashboardData = useCallback(async () => {
    // Предотвращаем множественные одновременные запросы
    if (isFetchingRef.current) {
      return
    }
    
    try {
      isFetchingRef.current = true
      setLoading(true)
      
      // Load recent news for display (first 20)
      const params: any = { limit: 20 }
      
      // Apply company filter only if user wants to see tracked companies AND has them
      const subscribedCompanies = userPreferences?.subscribed_companies
      if (showTrackedOnly && subscribedCompanies?.length) {
        params.company_ids = subscribedCompanies.join(',')
      }
      
      // Fetch recent news for UI
      const newsResponse = await api.get('/news/', { params })
      setRecentNews(newsResponse.data.items)
      
      // Get accurate statistics using stats endpoint
      let categoriesBreakdown
      let totalNews
      let todayNews
      
      if (showTrackedOnly && subscribedCompanies?.length) {
        // For tracked companies, use stats endpoint filtered by companies
        const statsResponse = await api.get('/news/stats/by-companies', {
          params: { company_ids: subscribedCompanies.join(',') }
        })
        
        const total = statsResponse.data.total_count
        const categoryCounts = statsResponse.data.category_counts
        const recentCount = statsResponse.data.recent_count
        
        categoriesBreakdown = Object.entries(categoryCounts)
          .map(([category, count]) => ({
            category: categoryLabels[category] || category,
            technicalCategory: category,
            count: Number(count),
            percentage: total > 0 ? Math.round((Number(count) / total) * 100) : 0
          }))
          .sort((a, b) => b.count - a.count)
        
        totalNews = total
        todayNews = recentCount
      } else {
        // For all news, use general stats endpoint
        const statsResponse = await api.get('/news/stats')
        
        const total = statsResponse.data.total_count
        const categoryCounts = statsResponse.data.category_counts
        const recentCount = statsResponse.data.recent_count
        
        categoriesBreakdown = Object.entries(categoryCounts)
          .map(([category, count]) => ({
            category: categoryLabels[category] || category,
            technicalCategory: category,
            count: Number(count),
            percentage: total > 0 ? Math.round((Number(count) / total) * 100) : 0
          }))
          .sort((a, b) => b.count - a.count)
        
        totalNews = total
        todayNews = recentCount
      }
      
      setStats({
        todayNews,
        totalNews,
        categoriesBreakdown
      })
      
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error)
    } finally {
      setLoading(false)
      isFetchingRef.current = false
    }
  }, [showTrackedOnly, userPreferences?.subscribed_companies]) // Убрали categoryLabels (константа) и userPreferences целиком

  // Show onboarding for new users (no companies tracked)
  useEffect(() => {
    if (userPreferences && !userPreferences.subscribed_companies?.length) {
      const hasSeenOnboarding = localStorage.getItem('has-seen-dashboard-onboarding')
      if (!hasSeenOnboarding && activeTab === 'discover') {
        // Show onboarding after a short delay
        const timer = setTimeout(() => {
          setShowOnboarding(true)
        }, 500)
        return () => clearTimeout(timer)
      }
    }
  }, [userPreferences, activeTab])

  // Auto-switch to discover tab for new users
  useEffect(() => {
    if (userPreferences && !userPreferences.subscribed_companies?.length) {
      const savedTab = localStorage.getItem('dashboard-activeTab')
      // Only auto-switch if user hasn't manually selected a tab
      if (!savedTab && activeTab !== 'discover') {
        setActiveTab('discover')
        localStorage.setItem('dashboard-activeTab', 'discover')
      }
    }
  }, [userPreferences, activeTab])

  useEffect(() => {
    // Don't fetch if we're in tracked mode but userPreferences haven't loaded yet
    // This prevents fetching "All News" data when user has "Tracked" mode selected after page reload
    if (showTrackedOnly && !userPreferences) {
      // Wait for preferences to load; once loaded, we'll fetch.
      return
    }
    fetchDashboardData()
  }, [userPreferences?.subscribed_companies, showTrackedOnly, fetchDashboardData, userPreferences])

  // Invalidate cache when tracked companies change
  useEffect(() => {
    if (userPreferences?.subscribed_companies) {
      queryClient.invalidateQueries({ queryKey: ['news'] })
    }
  }, [userPreferences?.subscribed_companies, queryClient])

  // Listen for global refresh event from NotificationCenter
  useEffect(() => {
    const handler = () => {
      fetchDashboardData()
    }
    window.addEventListener('app:refresh-news', handler as EventListener)
    return () => window.removeEventListener('app:refresh-news', handler as EventListener)
  }, [fetchDashboardData])
  
  // Auto-focus search input when discover tab is active
  useEffect(() => {
    if (activeTab === 'discover' && searchInputRef.current) {
      // Небольшая задержка для плавности
      const timer = setTimeout(() => {
        searchInputRef.current?.focus()
      }, 100)
      return () => clearTimeout(timer)
    }
  }, [activeTab])
  
  // Recompute available categories based on recentNews usage
  useEffect(() => {
    if (!categoriesData) return
    const used = new Set(recentNews.map((n) => n.category).filter(Boolean))
    const all = categoriesData.categories
    const filtered = all.filter((c: any) => used.has(c.value))
    setAvailableCategories(showAllCategories ? all : filtered)
  }, [categoriesData, recentNews, showAllCategories])

  // Уведомления перенесены в глобальный NotificationCenter

  // Refetch when filters change on news tab
  useEffect(() => {
    if (activeTab === 'news') {
      fetchFilteredNews()
    }
  }, [selectedCategory, selectedCompanies, activeTab])

  const fetchCompanies = useCallback(async () => {
    try {
      setCompaniesLoading(true)
      const response = await ApiService.getCompanies(
        companiesSearchQuery || undefined,
        companiesLimit,
        companiesOffset
      )
      setCompanies(response.items)
      setCompaniesTotal(response.total)
    } catch (error) {
      console.error('Failed to fetch companies:', error)
    } finally {
      setCompaniesLoading(false)
    }
  }, [companiesSearchQuery, companiesOffset, companiesLimit])

  // Reset offset when search query changes (but only if search is not empty)
  useEffect(() => {
    if (activeTab === 'competitors') {
      setCompaniesOffset(0)
    }
  }, [companiesSearchQuery, activeTab])

  // Fetch companies when competitors tab is active or search/offset changes
  useEffect(() => {
    if (activeTab === 'competitors') {
      const timer = setTimeout(() => {
        fetchCompanies()
      }, companiesSearchQuery ? 500 : 0) // Debounce only for search
      return () => clearTimeout(timer)
    }
  }, [activeTab, companiesSearchQuery, companiesOffset, fetchCompanies])

  const fetchFilteredNews = async () => {
    try {
      setLoading(true)
      
      const params: any = { limit: 20 }
      if (selectedCategory) {
        params.category = selectedCategory
      }
      if (selectedCompanies.length > 0) {
        params.companies = selectedCompanies.join(',')
      }
      
      const response = await api.get('/news/', { params })
      setRecentNews(response.data.items)
      
    } catch (error) {
      console.error('Failed to fetch filtered news:', error)
    } finally {
      setLoading(false)
    }
  }

  const fetchDigest = async (type: 'daily' | 'weekly' | 'custom') => {
    try {
      setDigestLoading(true)
      setDigestError(null)
      
      // Check if user is trying to get tracked digest but has no tracked companies
      if (showTrackedOnly && (!userPreferences?.subscribed_companies || userPreferences.subscribed_companies.length === 0)) {
        setDigestError('No tracked companies found. Please add companies to your preferences first.')
        return
      }
      
      console.log('Fetching digest:', type, 'showTrackedOnly:', showTrackedOnly)
      
      let endpoint = ''
      switch (type) {
        case 'daily':
          endpoint = `/digest/daily?tracked_only=${showTrackedOnly}`
          break
        case 'weekly':
          endpoint = `/digest/weekly?tracked_only=${showTrackedOnly}`
          break
        case 'custom':
          // Default to last 7 days for custom
          const dateFrom = new Date()
          dateFrom.setDate(dateFrom.getDate() - 7)
          endpoint = `/digest/custom?date_from=${dateFrom.toISOString().split('T')[0]}&date_to=${new Date().toISOString().split('T')[0]}&tracked_only=${showTrackedOnly}`
          break
      }
      
      console.log('Making request to:', endpoint)
      const response = await api.get(endpoint)
      console.log('Digest response:', response.data)
      setDigest(response.data)
      
    } catch (error: any) {
      console.error('Failed to fetch digest:', error)
      console.error('Error details:', {
        message: error.message,
        status: error.response?.status,
        statusText: error.response?.statusText,
        data: error.response?.data
      })
      setDigestError(error.response?.data?.detail || error.response?.data?.message || 'Failed to load digest')
    } finally {
      setDigestLoading(false)
    }
  }

  // Функция для загрузки источников новостей компании
  const fetchCompanySources = useCallback(async (companyId: string) => {
    // Проверяем, не загружаем ли уже или уже загружено
    setCompanySources(prev => {
      if (prev[companyId] && !prev[companyId].loading) {
        return prev // Уже загружено
      }
      if (prev[companyId]?.loading) {
        return prev // Уже загружается
      }
      
      return {
        ...prev,
        [companyId]: { sources: [], loading: true }
      }
    })

    try {
      // Загружаем новости компании для получения источников
      const response = await api.get('/news/', {
        params: {
          company_id: companyId,
          limit: 100 // Достаточно для получения разнообразных источников
        }
      })

      // Группируем по домену для получения уникальных источников
      const sourcesMap = new Map<string, { type: string; count: number }>()
      
      response.data.items.forEach((item: any) => {
        try {
          const url = item.source_url
          const domain = new URL(url).origin
          
          if (!sourcesMap.has(domain)) {
            sourcesMap.set(domain, {
              type: item.source_type || 'unknown',
              count: 0
            })
          }
          sourcesMap.get(domain)!.count++
        } catch (e) {
          // Пропускаем некорректные URL
          console.warn('Invalid URL:', item.source_url)
        }
      })

      const sources = Array.from(sourcesMap.entries())
        .map(([url, data]) => ({
          url,
          type: data.type,
          count: data.count
        }))
        .sort((a, b) => b.count - a.count) // Сортируем по количеству новостей

      setCompanySources(prev => ({
        ...prev,
        [companyId]: { sources, loading: false }
      }))
    } catch (error) {
      console.error('Failed to fetch company sources:', error)
      setCompanySources(prev => ({
        ...prev,
        [companyId]: { sources: [], loading: false }
      }))
    }
  }, [])

  // Функция для загрузки новостей компании
  const fetchCompanyNews = useCallback(async (companyId: string) => {
    if (companyNews[companyId]) return
    
    setLoadingCompanyData(prev => ({ ...prev, [companyId]: { ...prev[companyId], news: true } }))
    try {
      const response = await api.get('/news/', {
        params: { company_id: companyId, limit: 5 }
      })
      setCompanyNews(prev => ({ ...prev, [companyId]: response.data.items }))
    } catch (error) {
      console.error('Failed to fetch company news:', error)
    } finally {
      setLoadingCompanyData(prev => ({ ...prev, [companyId]: { ...prev[companyId], news: false } }))
    }
  }, [companyNews])

  // Функция для загрузки категорий новостей компании
  const fetchCompanyCategories = useCallback(async (companyId: string) => {
    if (companyCategories[companyId]) return
    
    setLoadingCompanyData(prev => ({ ...prev, [companyId]: { ...prev[companyId], categories: true } }))
    try {
      const statsResponse = await api.get('/news/stats/by-companies', {
        params: { company_ids: companyId }
      })
      const categoryCounts = statsResponse.data.category_counts
      const categories = Object.entries(categoryCounts)
        .map(([category, count]) => ({
          category: categoryLabels[category] || category,
          technicalCategory: category,
          count: Number(count)
        }))
        .sort((a, b) => b.count - a.count)
      setCompanyCategories(prev => ({ ...prev, [companyId]: categories }))
    } catch (error) {
      console.error('Failed to fetch company categories:', error)
    } finally {
      setLoadingCompanyData(prev => ({ ...prev, [companyId]: { ...prev[companyId], categories: false } }))
    }
  }, [companyCategories])

  // Функция для загрузки pricing информации
  const fetchCompanyPricing = useCallback(async (companyId: string, description?: string) => {
    if (companyPricing[companyId]) return
    
    setLoadingCompanyData(prev => ({ ...prev, [companyId]: { ...prev[companyId], pricing: true } }))
    try {
      const response = await api.get('/news/', {
        params: { company_id: companyId, category: 'pricing_change', limit: 10 }
      })
      setCompanyPricing(prev => ({
        ...prev,
        [companyId]: {
          news: response.data.items,
          description: description
        }
      }))
    } catch (error) {
      console.error('Failed to fetch company pricing:', error)
    } finally {
      setLoadingCompanyData(prev => ({ ...prev, [companyId]: { ...prev[companyId], pricing: false } }))
    }
  }, [companyPricing])

  const toggleCompanyExpanded = (companyId: string) => {
    setExpandedCompanies((prev) => {
      const newSet = new Set(prev)
      const isExpanded = newSet.has(companyId)
      
      if (isExpanded) {
        newSet.delete(companyId)
      } else {
        newSet.add(companyId)
        // Загружаем все данные при разворачивании
        fetchCompanySources(companyId)
        const company = companies.find(c => c.id === companyId)
        fetchCompanyNews(companyId)
        fetchCompanyCategories(companyId)
        fetchCompanyPricing(companyId, company?.description)
        setCompanyTabs(prev => ({ ...prev, [companyId]: 'news' }))
      }
      return newSet
    })
  }

  const formatDate = (dateString: string) => {
    try {
      const date = new Date(dateString)
      return formatDistance(date, new Date(), { addSuffix: true, locale: enUS })
    } catch {
      return 'Recently'
    }
  }

  // Валидация URL
  const validateUrlFormat = (url: string): boolean => {
    const trimmed = url.trim()
    if (!trimmed) return false
    
    try {
      const urlObj = new URL(trimmed)
      return urlObj.protocol === 'http:' || urlObj.protocol === 'https:'
    } catch {
      // Проверяем, является ли это доменом без протокола
      const domainPattern = /^([a-z0-9]+(-[a-z0-9]+)*\.)+[a-z]{2,}$/i
      return domainPattern.test(trimmed)
    }
  }

  // Обработчик изменения поискового запроса
  const handleSearchQueryChange = (value: string) => {
    setDiscoverSearchQuery(value)
    if (value.trim()) {
      const isUrl = validateUrlFormat(value)
      setInputType(isUrl ? 'url' : 'text')
      setIsValidInput(isUrl || value.trim().length > 2) // URL или достаточно длинный текст
    } else {
      setInputType(null)
      setIsValidInput(false)
    }
  }


  // Report functions
  const handleCreateReport = async (query: string) => {
    if (!query.trim()) {
      toast.error('Please enter a company name or URL')
      return
    }

    if (isCreatingReport) {
      return // Предотвратить множественные запросы
    }

    setIsCreatingReport(true)
    try {
      const toastId = toast.loading('Creating report...', { id: `create-report-${Date.now()}` })
      
      const { report_id, status, created_at } = await ApiService.createReport(query.trim())
      
      // Добавить в список отчётов
      const newReport: Report = {
        id: report_id,
        query: query.trim(),
        status: status as 'ready' | 'processing' | 'error',
        created_at,
      }
      
      setReports(prev => [newReport, ...prev]) // Новые отчёты вверху
      
      // Если отчёт готов, загрузить данные; если processing - начать polling
      if (status === 'ready') {
        await loadReportData(report_id)
        toast.success('Report ready!', { id: toastId })
      } else if (status === 'processing') {
        startPollingReportStatus(report_id)
        toast.success('Report creation started!', { id: toastId })
      } else {
        toast.error('Failed to create report', { id: toastId })
      }
      
      // Очистить поле ввода
      setDiscoverSearchQuery('')
      setInputType(null)
      setIsValidInput(false)
    } catch (error: any) {
      const errorMessage = error?.response?.data?.detail || 'Failed to create report'
      toast.error(errorMessage, { id: `create-report-${Date.now()}` })
      console.error('Failed to create report:', error)
    } finally {
      setIsCreatingReport(false)
    }
  }

  const startPollingReportStatus = (reportId: string) => {
    // Очистить предыдущий интервал, если есть
    if (pollingIntervals[reportId]) {
      clearInterval(pollingIntervals[reportId])
      delete pollingIntervals[reportId]
    }

    // Проверить, что отчёт существует и имеет статус processing
    const report = reports.find(r => r.id === reportId)
    if (!report || report.status !== 'processing') {
      // Не запускать polling для отчётов, которые не в статусе processing
      return
    }

    const MAX_POLLING_TIME = 5 * 60 * 1000 // 5 минут
    const POLLING_INTERVAL = 2000 // 2 секунды
    const startTime = Date.now()

    const intervalId = setInterval(async () => {
      // Проверка таймаута
      if (Date.now() - startTime > MAX_POLLING_TIME) {
        clearInterval(intervalId)
        setReports(prev => prev.map(r => r.id === reportId ? { ...r, status: 'error', error_message: 'Report creation timeout' } : r))
        toast.error('Report creation timeout', { id: `report-${reportId}` })
        setPollingIntervals(prev => {
          const next = { ...prev }
          delete next[reportId]
          return next
        })
        return
      }

      try {
        const statusResponse = await ApiService.getReportStatus(reportId)
        const currentStatus = statusResponse.status
        
        // Проверить, что отчёт всё ещё существует
        const currentReport = reports.find(r => r.id === reportId)
        if (!currentReport) {
          // Отчёт был удалён, остановить polling
          clearInterval(intervalId)
          setPollingIntervals(prev => {
            const next = { ...prev }
            delete next[reportId]
            return next
          })
          return
        }
        
        setReports(prev => prev.map(r => r.id === reportId ? { ...r, status: currentStatus, error_message: statusResponse.error || undefined } : r))
        
        if (currentStatus === 'ready') {
          clearInterval(intervalId)
          // Удалить из polling intervals
          setPollingIntervals(prev => {
            const next = { ...prev }
            delete next[reportId]
            return next
          })
          // Загрузить данные отчёта
          await loadReportData(reportId)
          toast.success('Report ready!', { id: `report-${reportId}` })
        } else if (currentStatus === 'error') {
          clearInterval(intervalId)
          setPollingIntervals(prev => {
            const next = { ...prev }
            delete next[reportId]
            return next
          })
          toast.error(`Report failed: ${statusResponse.error || 'Unknown error'}`, { 
            id: `report-${reportId}` 
          })
        }
        // Если статус всё ещё 'processing', продолжаем polling
      } catch (error) {
        console.error('Failed to check report status:', error)
        // Продолжать polling при ошибках сети, но только если не прошло слишком много времени
        if (Date.now() - startTime > MAX_POLLING_TIME) {
          clearInterval(intervalId)
          setPollingIntervals(prev => {
            const next = { ...prev }
            delete next[reportId]
            return next
          })
        }
      }
    }, POLLING_INTERVAL)

    // Сохранить interval ID для cleanup
    setPollingIntervals(prev => ({ ...prev, [reportId]: intervalId }))
  }

  const loadReportData = async (reportId: string, includeCompetitors: boolean = false) => {
    try {
      const report = await ApiService.getReport(reportId, includeCompetitors)
      setReportData(prev => ({ ...prev, [reportId]: report }))
      
      // Обновить отчёт в списке
      setReports(prev => prev.map(r => r.id === reportId ? report : r))
    } catch (error) {
      console.error('Failed to load report data:', error)
      toast.error('Failed to load report data', { id: `report-${reportId}` })
    }
  }

  // Загрузить отчёты при монтировании и при переключении на discover tab
  useEffect(() => {
    if (activeTab === 'discover' && isAuthenticated && !reportsLoaded) {
      const loadReports = async () => {
        try {
          const response = await ApiService.getReports(20, 0)
          
          // Объединить отчёты с сервера с локальными, сохраняя локальные изменения для processing отчётов
          setReports(prev => {
            const serverReportsMap = new Map(response.items.map(r => [r.id, r]))
            const localReportsMap = new Map(prev.map(r => [r.id, r]))
            
            // Объединить: приоритет у серверных данных, кроме локальных processing отчётов
            const merged = response.items.map(serverReport => {
              const localReport = localReportsMap.get(serverReport.id)
              // Если локальный отчёт в processing и серверный тоже, сохранить локальный (может быть только что создан)
              if (localReport?.status === 'processing' && serverReport.status === 'processing') {
                return localReport
              }
              return serverReport
            })
            
            // Добавить локальные отчёты, которых нет на сервере (только что созданные)
            localReportsMap.forEach((localReport, id) => {
              if (!serverReportsMap.has(id)) {
                merged.unshift(localReport)
              }
            })
            
            return merged
          })
          
          // Загрузить полные данные для готовых отчётов
          const readyReports = response.items.filter(r => r.status === 'ready')
          for (const report of readyReports) {
            try {
              const fullReport = await ApiService.getReport(report.id)
              setReportData(prev => ({ ...prev, [report.id]: fullReport }))
            } catch (error) {
              console.error(`Failed to load report ${report.id}:`, error)
            }
          }
          
          // Возобновить polling для отчётов со статусом processing
          // Но только если polling ещё не запущен
          response.items.forEach((report) => {
            if (report.status === 'processing' && !pollingIntervals[report.id]) {
              startPollingReportStatus(report.id)
            }
          })
          
          setReportsLoaded(true)
        } catch (error) {
          console.error('Failed to load reports:', error)
        }
      }
      loadReports()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab, isAuthenticated, reportsLoaded])
  
  // Сбросить флаг загрузки при переключении с discover tab
  useEffect(() => {
    if (activeTab !== 'discover') {
      setReportsLoaded(false)
    }
  }, [activeTab])

  // Cleanup polling intervals при размонтировании
  useEffect(() => {
    return () => {
      // Очистить все polling intervals
      Object.values(pollingIntervals).forEach(intervalId => {
        clearInterval(intervalId)
      })
    }
  }, [pollingIntervals])
  
  const filteredNews = selectedDate
    ? recentNews.filter((item) => {
        const itemDate = new Date(item.published_at || item.created_at)
        const filterDate = new Date(selectedDate)
        return itemDate.toDateString() === filterDate.toDateString()
      })
    : recentNews

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Subscription Banner */}
        <SubscriptionBanner />
        
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 mb-2">Dashboard</h1>
              <div className="flex items-center space-x-4">
                {userPreferences?.subscribed_companies?.length ? (
                  <p className="text-gray-600">
                    {showTrackedOnly ? `Personalized for ${userPreferences.subscribed_companies.length} tracked companies` : 'Showing all news'}
                  </p>
                ) : (
                  <p className="text-gray-600">
                    <span className="text-primary-600">Add companies to personalize</span>
                  </p>
                )}
                
                {/* Mode Tabs */}
                {userPreferences?.subscribed_companies && userPreferences.subscribed_companies.length > 0 && (
                  <div className="inline-flex items-center bg-gray-100 rounded-lg p-1">
                    <button
                      onClick={() => handleToggleTrackedOnly(false)}
                      className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${
                        !showTrackedOnly
                          ? 'bg-white text-gray-900 shadow-sm'
                          : 'text-gray-600 hover:text-gray-900'
                      }`}
                    >
                      <span className="flex items-center gap-2">
                        🌍 All News
                      </span>
                    </button>
                    <button
                      onClick={() => handleToggleTrackedOnly(true)}
                      className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${
                        showTrackedOnly
                          ? 'bg-white text-gray-900 shadow-sm'
                          : 'text-gray-600 hover:text-gray-900'
                      }`}
                    >
                      <span className="flex items-center gap-2">
                        ⭐ Tracked ({userPreferences.subscribed_companies.length})
                      </span>
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="border-b border-gray-200 mb-6">
          <nav className="-mb-px flex space-x-8">
            {tabs.map((tab) => {
              const Icon = tab.icon
              return (
                <button
                  key={tab.id}
                  onClick={() => handleTabChange(tab.id)}
                  className={`group relative py-3 px-2 border-b-2 font-medium text-sm transition-all ${
                    activeTab === tab.id
                      ? 'border-primary-500 text-primary-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                  title={tab.description}
                >
                  <div className="flex items-center gap-2">
                    {Icon && <Icon className="h-4 w-4" />}
                    <span>{tab.label}</span>
                  </div>
                </button>
              )
            })}
          </nav>
          {/* Active tab description */}
          <div className="mt-2">
            <p className="text-sm text-gray-600">
              {tabs.find(t => t.id === activeTab)?.description}
            </p>
          </div>
        </div>

        {/* Tab Content */}
        {activeTab === 'overview' && (
          <div className="space-y-8">
            {/* Stats Cards - Improved */}
            <StatsCards
              todayNews={stats?.todayNews || 0}
              totalNews={stats?.totalNews || 0}
              categoriesCount={stats?.categoriesBreakdown.length || 0}
              categoriesBreakdown={stats?.categoriesBreakdown}
              loading={loading}
              showLinkToAnalytics={true}
            />

            {/* Monitoring Status Section */}
            {subscribedCompanies.length > 0 && (
              <>
                {monitoringLoading ? (
                  <div>
                    <h2 className="text-xl font-semibold text-gray-900 mb-4">Monitoring Status</h2>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                      {[1, 2, 3].map((i) => (
                        <div key={i} className="bg-white rounded-lg border border-gray-200 p-4 animate-pulse">
                          <div className="h-4 bg-gray-200 rounded w-3/4 mb-3"></div>
                          <div className="h-3 bg-gray-200 rounded w-1/2 mb-2"></div>
                          <div className="h-3 bg-gray-200 rounded w-2/3"></div>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : monitoringStatus?.statuses && monitoringStatus.statuses.length > 0 ? (
                  <div>
                    <h2 className="text-xl font-semibold text-gray-900 mb-4">Monitoring Status</h2>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                      {monitoringStatus.statuses.map((status) => (
                        <MonitoringStatusCard
                          key={status.company_id}
                          status={status}
                          onViewDetails={() => {
                            // Navigate to company details or monitoring page
                            navigate(`/competitor-analysis?company_id=${status.company_id}`)
                          }}
                        />
                      ))}
                    </div>
                  </div>
                ) : null}
              </>
            )}

            {/* Quick Links to other pages */}
            <div>
              <h2 className="text-xl font-semibold text-gray-900 mb-4">Quick Access</h2>
              <QuickLinks />
            </div>

            {/* Recommendations */}
            {(() => {
              const recommendations = []
              if (!userPreferences?.subscribed_companies?.length) {
                recommendations.push({
                  id: 'no-companies',
                  type: 'action' as const,
                  title: 'Get Started',
                  message: 'Add companies to track their news and get personalized insights.',
                  actionLabel: 'Discover Companies',
                  onAction: () => handleTabChange('discover')
                })
              }
              if (stats && stats.todayNews > 10) {
                recommendations.push({
                  id: 'high-activity',
                  type: 'info' as const,
                  title: 'High Activity Today',
                  message: `You have ${stats.todayNews} news items today. Check out detailed analytics.`,
                  actionLabel: 'View Analytics',
                  actionLink: '/news-analytics'
                })
              }
              return recommendations.length > 0 ? (
                <Recommendations recommendations={recommendations} />
              ) : null
            })()}

            {/* Tracked Companies Manager */}
            <TrackedCompaniesManager />

            {/* Recent News and Categories */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              {/* Recent News - Improved with grouping */}
              <div className="card p-6 flex flex-col" style={{ height: '510px' }}>
                <div className="flex items-center justify-between mb-4 flex-shrink-0">
                  <h3 className="text-lg font-semibold text-gray-900">
                    Recent News
                  </h3>
                </div>
                <div className="flex-1 min-h-0">
                  {loading ? (
                    <SkeletonLoader type="list" count={5} />
                  ) : recentNews.length > 0 ? (
                    <NewsGroupedList
                      news={recentNews}
                      categoryLabels={categoryLabels}
                      maxItemsPerGroup={10}
                      maxHeight="550px"
                    />
                  ) : (
                    <p className="text-sm text-gray-500">No news yet</p>
                  )}
                </div>
              </div>

                  {/* Top Categories - With scroll */}
                  <div className="card p-6 flex flex-col" style={{ height: '510px' }}>
                    <div className="flex items-center justify-between mb-4 flex-shrink-0">
                      <h3 className="text-lg font-semibold text-gray-900 flex items-center">
                        Top Categories
                        {!showTrackedOnly && (
                          <span className="ml-2 text-sm font-normal text-gray-600">
                            (all news)
                          </span>
                        )}
                      </h3>
                    </div>
                    <div 
                      className="flex-1 overflow-y-auto space-y-3 pr-2"
                      style={{ maxHeight: '550px' }}
                    >
                      {stats?.categoriesBreakdown.map((category, index) => {
                        // Get technical name for navigation - prefer technicalCategory if available
                        const technicalName = category.technicalCategory || categoryTechnicalNames[category.category] || category.category
                        return (
                        <button
                          key={category.category}
                          onClick={() => {
                            const params = new URLSearchParams()
                            if (showTrackedOnly && userPreferences?.subscribed_companies?.length) {
                              params.set('tracked', 'true')
                            }
                            const queryString = params.toString()
                            navigate(`/category/${technicalName}${queryString ? `?${queryString}` : ''}`)
                          }}
                          className="w-full flex items-center justify-between hover:bg-gray-50 p-2 rounded-lg transition-colors cursor-pointer group"
                        >
                          <div className="flex items-center">
                            <span className="text-sm font-medium text-gray-500 w-6">
                              #{index + 1}
                            </span>
                            <span className="text-sm font-medium text-gray-900 ml-2 group-hover:text-primary-600">
                              {category.category}
                            </span>
                          </div>
                          <div className="flex items-center space-x-2">
                            <span className="text-sm text-gray-500">
                              {category.count}
                            </span>
                            <span className="text-xs text-gray-400">
                              ({category.percentage}%)
                            </span>
                          </div>
                        </button>
                        )
                      })}
                      {(!stats || stats.categoriesBreakdown.length === 0) && (
                        <p className="text-sm text-gray-500">No data yet</p>
                      )}
                    </div>
                  </div>
                </div>
          </div>
        )}

        {activeTab === 'discover' && (
          <div className="space-y-6">
            {/* Hero Section with Search Bar - Modern Redesign */}
            <div className="bg-gradient-to-br from-blue-50/50 via-white to-indigo-50/30 border border-blue-100/50 rounded-2xl shadow-lg p-8 md:p-12 transition-all">
              <div className="max-w-3xl mx-auto">
                {/* Header Section */}
                <div className="text-center mb-8">
                  <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-3">
                    Monitor AI Industry News
                  </h2>
                  <p className="text-gray-600 text-lg max-w-2xl mx-auto leading-relaxed">
                    Get personalized digests and stay informed about all important events in the AI industry
                  </p>
                </div>
                
                {/* Search Bar with Integrated Button */}
                <div className="relative mb-4">
                  <div className="relative flex items-center group">
                    {/* Left Icon - Dynamic based on input type with pulse animation */}
                    <div className="absolute left-4 z-10 pointer-events-none transition-all duration-300">
                      {isCreatingReport ? (
                        <div className="w-5 h-5 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
                      ) : isValidInput && inputType === 'url' ? (
                        <div className="flex items-center gap-1.5">
                          <Globe className="h-5 w-5 text-green-600 transition-colors duration-200 animate-pulse" />
                          <CheckCircle className="h-3.5 w-3.5 text-green-600" />
                        </div>
                      ) : inputType === 'url' ? (
                        <Globe className="h-5 w-5 text-blue-600 transition-colors duration-200" />
                      ) : inputType === 'text' ? (
                        <Search className="h-5 w-5 text-gray-400 group-focus-within:text-blue-600 transition-colors duration-200" />
                      ) : (
                        <Sparkles className="h-5 w-5 text-gray-400" />
                      )}
                    </div>
                    
                    {/* Input Field with dynamic border color */}
                    <input
                      ref={searchInputRef}
                      type="text"
                      placeholder="Try 'openai.com', 'anthropic', or any company URL..."
                      className={`input h-14 pl-12 pr-32 text-lg w-full shadow-md bg-white/90 backdrop-blur-sm focus:ring-4 focus:ring-blue-500/10 transition-all duration-200 placeholder:text-gray-400 disabled:bg-gray-50 ${
                        isValidInput && inputType === 'url' 
                          ? 'border-green-500 focus:border-green-500' 
                          : inputType === 'text' && discoverSearchQuery.trim().length > 0
                          ? 'border-blue-500 focus:border-blue-500'
                          : 'border-gray-300 focus:border-blue-500'
                      }`}
                      value={discoverSearchQuery}
                      onChange={(e) => handleSearchQueryChange(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' && discoverSearchQuery.trim() && !isCreatingReport) {
                          handleCreateReport(discoverSearchQuery.trim())
                        }
                      }}
                      disabled={isCreatingReport}
                      aria-label="Search for company by URL or name"
                    />
                    
                    {/* Search Button - Inside Input with scale animation */}
                    <button
                      onClick={() => {
                        if (discoverSearchQuery.trim() && !isCreatingReport) {
                          handleCreateReport(discoverSearchQuery.trim())
                        }
                      }}
                      disabled={!discoverSearchQuery.trim() || isCreatingReport}
                      className="absolute right-2 top-1/2 -translate-y-1/2 h-10 px-6 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 flex items-center gap-2 shadow-sm hover:shadow-md hover:scale-105 active:scale-95 disabled:hover:shadow-sm disabled:hover:scale-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
                      aria-label="Search company"
                    >
                      {isCreatingReport ? (
                        <>
                          <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                          <span className="hidden sm:inline">Creating...</span>
                        </>
                      ) : (
                        <>
                          <Search className="h-4 w-4" />
                          <span className="hidden sm:inline">Search</span>
                        </>
                      )}
                    </button>
                  </div>
                  
                  {/* Keyboard Hint - показывать только когда есть текст и не идет создание */}
                  {discoverSearchQuery.trim() && !isCreatingReport && (
                    <div className="flex items-center justify-center gap-2 mt-3 text-xs text-gray-500 animate-fade-in duration-200">
                      <kbd className="px-2 py-1 bg-gray-100 border border-gray-300 rounded text-gray-600 font-mono shadow-sm">
                        Enter
                      </kbd>
                      <span>to search</span>
                      {isValidInput && inputType === 'url' && (
                        <span className="flex items-center gap-1 text-green-600 ml-2 animate-fade-in">
                          <CheckCircle className="h-3 w-3" />
                          Valid URL
                        </span>
                      )}
                    </div>
                  )}
                </div>

                {/* Additional Info Text */}
                <p className="text-sm text-gray-500 text-center">
                  Find company insights, news and suggested competitors before registering
                </p>
              </div>
            </div>

            {/* Information Cards - показывать только если нет запроса и отчётов */}
            {discoverSearchQuery.length === 0 && reports.length === 0 && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="card p-6 hover:shadow-lg transition-shadow">
                <div className="text-3xl mb-3">🔍</div>
                <h3 className="font-semibold text-gray-900 mb-2">Search</h3>
                <p className="text-sm text-gray-600">
                  Find companies by URL or name. We'll scan their website and social media.
                </p>
              </div>
              <div className="card p-6 hover:shadow-lg transition-shadow">
                <div className="text-3xl mb-3">📰</div>
                <h3 className="font-semibold text-gray-900 mb-2">Analyze</h3>
                <p className="text-sm text-gray-600">
                  Review news, pricing changes, and updates from companies you track.
                </p>
              </div>
              <div className="card p-6 hover:shadow-lg transition-shadow">
                <div className="text-3xl mb-3">🎯</div>
                <h3 className="font-semibold text-gray-900 mb-2">Track</h3>
                <p className="text-sm text-gray-600">
                  Add companies to your list and get personalized news digests.
                </p>
              </div>
            </div>
            )}

            {/* Reports List */}
            {reports.length > 0 && (
              <div className="flex flex-col gap-4">
                {reports.map((report) => {
                  const isExpanded = expandedReports.has(report.id)
                  const activeTab = reportTabs[report.id] || 'news'
                  const fullReportData = reportData[report.id] || report

                  return (
                    <ReportCard
                      key={report.id}
                      report={report}
                      isExpanded={isExpanded}
                      activeTab={activeTab}
                      reportData={fullReportData.status === 'ready' ? fullReportData : undefined}
                      onExpand={() => {
                        const next = new Set(expandedReports)
                        if (next.has(report.id)) {
                          next.delete(report.id)
                        } else {
                          next.add(report.id)
                        }
                        setExpandedReports(next)
                      }}
                      onTabChange={async (tab) => {
                        setReportTabs(prev => ({ ...prev, [report.id]: tab }))
                        // Если переключились на таб competitors и конкурентов ещё нет, загрузить их
                        if (tab === 'competitors' && fullReportData.status === 'ready' && !fullReportData.competitors) {
                          await loadReportData(report.id, true)
                        }
                      }}
                      onLoadCompetitors={async () => {
                        await loadReportData(report.id, true)
                      }}
                      onEdit={() => {
                        // Редактирование = изменение query в поле ввода и создание нового отчёта
                        setDiscoverSearchQuery(report.query)
                        // Можно также показать модальное окно для редактирования
                        toast.success('Query copied to search field. Modify and create a new report.')
                      }}
                      onDelete={() => {
                        setDeleteModal({ isOpen: true, report })
                      }}
                      onRetry={async () => {
                        if (report.query) {
                          // Остановить старый polling, если он был
                          if (pollingIntervals[report.id]) {
                            clearInterval(pollingIntervals[report.id])
                            setPollingIntervals(prev => {
                              const next = { ...prev }
                              delete next[report.id]
                              return next
                            })
                          }
                          
                          // Оптимистично обновить статус на processing
                          setReports(prev => prev.map(r => 
                            r.id === report.id 
                              ? { ...r, status: 'processing' as const, error_message: undefined }
                              : r
                          ))
                          
                          // Создать новый отчёт
                          try {
                            const toastId = toast.loading('Retrying report creation...', { id: `retry-report-${report.id}` })
                            
                            const { report_id, created_at } = await ApiService.createReport(report.query.trim())
                            
                            // Заменить старый отчёт новым
                            const newReport: Report = {
                              id: report_id,
                              query: report.query.trim(),
                              status: 'processing',
                              created_at,
                            }
                            
                            setReports(prev => prev.map(r => r.id === report.id ? newReport : r))
                            
                            // Начать polling для нового отчёта
                            startPollingReportStatus(report_id)
                            
                            toast.success('Report creation restarted!', { id: toastId })
                          } catch (error: any) {
                            // В случае ошибки вернуть статус error
                            setReports(prev => prev.map(r => 
                              r.id === report.id 
                                ? { ...r, status: 'error' as const, error_message: error?.response?.data?.detail || 'Failed to retry report' }
                                : r
                            ))
                            const errorMessage = error?.response?.data?.detail || 'Failed to retry report'
                            toast.error(errorMessage, { id: `retry-report-${report.id}` })
                            console.error('Failed to retry report:', error)
                          }
                        }
                      }}
                      onAddCompetitorsToTracked={() => {
                        // Открыть модалку с конкурентами из текущего отчета
                        setAddCompetitorsModal({ isOpen: true, report: fullReportData })
                      }}
                    />
                  )
                })}
              </div>
            )}
          </div>
        )}

        {activeTab === 'news' && (
          <div className="space-y-6">
            {/* News Filters */}
            <div className="card p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900">News Filters</h3>
                <a href="/news" className="btn btn-outline btn-sm">
                  <Search className="h-4 w-4 mr-2" />
                  Advanced Search
                </a>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <select 
                  className="input"
                  value={selectedCategory}
                  onChange={(e) => setSelectedCategory(e.target.value)}
                >
                  <option value="">Все категории</option>
                  {availableCategories.map((cat) => (
                    <option key={cat.value} value={cat.value}>
                      {categoryLabels[cat.value] || cat.description || cat.value}
                    </option>
                  ))}
                </select>
                <CompanyMultiSelect
                  selectedCompanies={selectedCompanies}
                  onSelectionChange={setSelectedCompanies}
                  placeholder="Выберите компании..."
                  availableCompanyIds={showAllCompanies ? undefined : Array.from(new Set(recentNews.map((n) => n.company?.id).filter((id): id is string => Boolean(id))))}
                />
                <input 
                  type="date" 
                  className="input"
                  value={selectedDate}
                  onChange={(e) => setSelectedDate(e.target.value)}
                />
              </div>
              <div className="flex items-center gap-3 mt-2">
                <label className="text-xs text-gray-600 inline-flex items-center gap-1">
                  <input
                    type="checkbox"
                    className="mr-1"
                    checked={showAllCategories}
                    onChange={(e) => setShowAllCategories(e.target.checked)}
                  />
                  Показать все категории
                </label>
                <label className="text-xs text-gray-600 inline-flex items-center gap-1">
                  <input
                    type="checkbox"
                    className="mr-1"
                    checked={showAllCompanies}
                    onChange={(e) => setShowAllCompanies(e.target.checked)}
                  />
                  Показать все компании
                </label>
              </div>
              {/* Filter Chips - Visual representation of active filters */}
              <FilterChips
                filters={[
                  ...(selectedCategory ? [{
                    id: 'category',
                    label: categoryLabels[selectedCategory] || selectedCategory,
                    onRemove: () => setSelectedCategory('')
                  }] : []),
                  ...selectedCompanies.map((companyId, idx) => {
                    const company = companies.find(c => c.id === companyId)
                    return {
                      id: `company-${companyId}`,
                      label: company?.name || `Company ${idx + 1}`,
                      onRemove: () => setSelectedCompanies(prev => prev.filter(id => id !== companyId))
                    }
                  }),
                  ...(selectedDate ? [{
                    id: 'date',
                    label: new Date(selectedDate).toLocaleDateString('en-US'),
                    onRemove: () => setSelectedDate('')
                  }] : [])
                ]}
                onClearAll={
                  (selectedCategory || selectedCompanies.length > 0 || selectedDate)
                    ? () => {
                        setSelectedCategory('')
                        setSelectedCompanies([])
                        setSelectedDate('')
                      }
                    : undefined
                }
                className="mt-4"
              />
            </div>

            {/* News List - Improved with grouping */}
            {loading ? (
              <SkeletonLoader type="card" count={5} />
            ) : filteredNews.length > 0 ? (
              <NewsGroupedList
                news={filteredNews}
                categoryLabels={categoryLabels}
                maxItemsPerGroup={10}
              />
            ) : (
              <div className="text-center py-12">
                <p className="text-gray-600">No news found</p>
                <button
                  onClick={() => {
                    setSelectedCategory('')
                    setSelectedCompanies([])
                    setSelectedDate('')
                  }}
                  className="mt-4 text-sm text-primary-600 hover:text-primary-700 font-medium"
                >
                  Reset Filters
                </button>
              </div>
            )}

          </div>
        )}

        {activeTab === 'competitors' && (
          <div className="space-y-6">
            {/* Search Bar - только просмотр существующих компаний */}
            <div className="card p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900">My Tracked Companies</h3>
                <p className="text-sm text-gray-500">
                  Use "Discover" tab to add new companies
                </p>
              </div>
              <div className="flex items-center space-x-4">
                <div className="flex-1 relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
                  <input
                    type="text"
                    placeholder="Search companies by name..."
                    value={companiesSearchQuery}
                    onChange={(e) => setCompaniesSearchQuery(e.target.value)}
                    className="input pl-10 w-full"
                  />
                </div>
                {companiesSearchQuery && (
                  <button
                    onClick={() => {
                      setCompaniesSearchQuery('')
                      setCompaniesOffset(0)
                    }}
                    className="btn btn-outline btn-sm"
                  >
                    Clear
                  </button>
                )}
              </div>
              {companiesTotal > 0 && (
                <p className="text-sm text-gray-600 mt-2">
                  Found {companiesTotal} {companiesTotal === 1 ? 'company' : 'companies'}
                </p>
              )}
            </div>

            {/* Companies List */}
            {companiesLoading ? (
              <SkeletonLoader type="card" count={3} />
            ) : companies.length === 0 ? (
              <div className="text-center py-12">
                <p className="text-gray-600">
                  {companiesSearchQuery ? 'No companies found matching your search' : 'No companies available'}
                </p>
              </div>
            ) : (
              <>
                <div className="flex flex-col gap-4">
                  {companies.map((company) => {
                    const isExpanded = expandedCompanies.has(company.id)
                    const activeTab = companyTabs[company.id] || 'news'
                    return (
                      <div key={company.id} className="card p-6 hover:shadow-lg transition-shadow">
                        <div className="flex items-start gap-4">
                          {/* Logo */}
                          <div className="flex-shrink-0">
                            {company.logo_url ? (
                              <img
                                src={company.logo_url}
                                alt={company.name}
                                className="w-16 h-16 rounded-lg object-cover"
                                onError={(e) => {
                                  // Fallback to placeholder if image fails to load
                                  e.currentTarget.style.display = 'none'
                                }}
                              />
                            ) : (
                              <div className="w-16 h-16 rounded-lg bg-gray-200 flex items-center justify-center">
                                <Globe className="h-8 w-8 text-gray-400" />
                              </div>
                            )}
                          </div>

                          {/* Company Info */}
                          <div className="flex-1 min-w-0">
                            {/* Header - always visible */}
                            <div className="flex items-start justify-between gap-4 mb-2">
                              <div className="flex-1 min-w-0">
                                <h3 className="text-lg font-semibold text-gray-900">{company.name}</h3>
                                {company.category && (
                                  <span className="inline-block mt-1 text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded-full">
                                    {company.category}
                                  </span>
                                )}
                              </div>
                              <div className="flex items-center gap-3">
                                {company.created_at && (
                                  <p className="text-xs text-gray-500 whitespace-nowrap">
                                    Added {formatDate(company.created_at)}
                                  </p>
                                )}
                                {/* Expand/Collapse Button */}
                                <button
                                  onClick={() => toggleCompanyExpanded(company.id)}
                                  className="flex-shrink-0 p-1 hover:bg-gray-100 rounded transition-colors"
                                  aria-label={isExpanded ? 'Collapse' : 'Expand'}
                                >
                                  {isExpanded ? (
                                    <ChevronUp className="h-5 w-5 text-gray-500" />
                                  ) : (
                                    <ChevronDown className="h-5 w-5 text-gray-500" />
                                  )}
                                </button>
                              </div>
                            </div>

                            {/* Expanded content */}
                            {isExpanded && (
                              <div className="mt-4 space-y-4">
                                {/* Описание компании - выделенный блок */}
                                {company.description && (
                                  <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-lg p-4">
                                    <p className="text-sm text-gray-700 leading-relaxed">{company.description}</p>
                                  </div>
                                )}

                                {/* Категории новостей - всегда видимы */}
                                {loadingCompanyData[company.id]?.categories ? (
                                  <div className="flex items-center gap-2">
                                    <div className="w-4 h-4 border-2 border-primary-600 border-t-transparent rounded-full animate-spin"></div>
                                    <span className="text-xs text-gray-500">Загрузка категорий...</span>
                                  </div>
                                ) : companyCategories[company.id] && companyCategories[company.id].length > 0 ? (
                                  <div>
                                    <p className="text-xs font-medium text-gray-700 mb-2">Категории новостей:</p>
                                    <div className="flex flex-wrap gap-2">
                                      {companyCategories[company.id].map((cat) => (
                                        <span
                                          key={cat.technicalCategory}
                                          className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-primary-100 text-primary-700 border border-primary-200"
                                        >
                                          {cat.category}
                                          <span className="ml-1.5 px-1.5 py-0.5 bg-primary-200 rounded-full text-primary-800">
                                            {cat.count}
                                          </span>
                                        </span>
                                      ))}
                                    </div>
                                  </div>
                                ) : null}

                                {/* Табы */}
                                <div className="border-t border-gray-200 pt-4">
                                  <div className="flex space-x-1 border-b border-gray-200 mb-4">
                                    {['news', 'sources', 'pricing'].map((tab) => (
                                      <button
                                        key={tab}
                                        onClick={() => setCompanyTabs(prev => ({ ...prev, [company.id]: tab }))}
                                        className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                                          activeTab === tab
                                            ? 'border-primary-500 text-primary-600'
                                            : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                                        }`}
                                      >
                                        {tab === 'news' && 'News'}
                                        {tab === 'sources' && 'Sources'}
                                        {tab === 'pricing' && 'Pricing'}
                                      </button>
                                    ))}
                                  </div>

                                  {/* Tab Content */}
                                  {activeTab === 'news' && (
                                    <div className="space-y-3">
                                      {loadingCompanyData[company.id]?.news ? (
                                        <div className="flex items-center gap-2 py-4">
                                          <div className="w-4 h-4 border-2 border-primary-600 border-t-transparent rounded-full animate-spin"></div>
                                          <span className="text-sm text-gray-500">Загрузка новостей...</span>
                                        </div>
                                      ) : companyNews[company.id]?.length > 0 ? (
                                        companyNews[company.id].map((news) => (
                                          <div key={news.id} className="border-l-2 border-primary-200 pl-3 py-1">
                                            <a
                                              href={news.source_url}
                                              target="_blank"
                                              rel="noopener noreferrer"
                                              className="text-sm text-gray-900 hover:text-primary-600 font-medium block"
                                            >
                                              {news.title}
                                            </a>
                                            <div className="flex items-center gap-2 mt-1">
                                              <span className="text-xs text-gray-500">
                                                {formatDate(news.published_at || news.created_at)}
                                              </span>
                                              {news.category && (
                                                <>
                                                  <span className="text-xs text-gray-400">•</span>
                                                  <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">
                                                    {categoryLabels[news.category] || news.category}
                                                  </span>
                                                </>
                                              )}
                                            </div>
                                          </div>
                                        ))
                                      ) : (
                                        <p className="text-sm text-gray-500 py-4">Новости не найдены</p>
                                      )}
                                    </div>
                                  )}

                                  {activeTab === 'sources' && (
                                    <div>
                                      {companySources[company.id]?.loading ? (
                                        <div className="flex items-center gap-2 py-4">
                                          <div className="w-4 h-4 border-2 border-primary-600 border-t-transparent rounded-full animate-spin"></div>
                                          <span className="text-xs text-gray-500">Загрузка источников...</span>
                                        </div>
                                      ) : companySources[company.id]?.sources.length > 0 ? (
                                        <div className="space-y-2">
                                          {companySources[company.id].sources.map((source, idx) => (
                                            <div key={idx} className="flex items-start justify-between gap-2 p-2 bg-gray-50 rounded text-sm">
                                              <div className="flex-1 min-w-0">
                                                <a
                                                  href={source.url}
                                                  target="_blank"
                                                  rel="noopener noreferrer"
                                                  className="text-primary-600 hover:text-primary-700 break-all inline-flex items-center gap-1"
                                                  onClick={(e) => e.stopPropagation()}
                                                >
                                                  {source.url}
                                                  <ExternalLink className="h-3 w-3" />
                                                </a>
                                                <span className="text-xs text-gray-500 ml-2 capitalize">
                                                  ({source.type})
                                                </span>
                                              </div>
                                              <span className="text-xs text-gray-500 whitespace-nowrap">
                                                {source.count} новостей
                                              </span>
                                            </div>
                                          ))}
                                        </div>
                                      ) : companySources[company.id]?.loading === false ? (
                                        <p className="text-xs text-gray-500 py-4">Источники не найдены</p>
                                      ) : null}
                                    </div>
                                  )}

                                  {activeTab === 'pricing' && (
                                    <div className="space-y-4">
                                      {loadingCompanyData[company.id]?.pricing ? (
                                        <div className="flex items-center gap-2 py-4">
                                          <div className="w-4 h-4 border-2 border-primary-600 border-t-transparent rounded-full animate-spin"></div>
                                          <span className="text-sm text-gray-500">Загрузка информации о ценах...</span>
                                        </div>
                                      ) : (
                                        <>
                                          {/* Текстовая информация о pricing из description */}
                                          {companyPricing[company.id]?.description && 
                                           (companyPricing[company.id]?.description?.toLowerCase().includes('pricing') || 
                                            companyPricing[company.id]?.description?.toLowerCase().includes('price') ||
                                            companyPricing[company.id]?.description?.toLowerCase().includes('$')) && (
                                            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                                              <h4 className="text-sm font-semibold text-gray-900 mb-2">Информация о ценообразовании:</h4>
                                              <p className="text-sm text-gray-700 leading-relaxed">
                                                {companyPricing[company.id]?.description}
                                              </p>
                                            </div>
                                          )}

                                          {/* Новости о pricing изменениях */}
                                          {companyPricing[company.id]?.news && companyPricing[company.id].news.length > 0 ? (
                                            <div>
                                              <h4 className="text-sm font-semibold text-gray-900 mb-3">Последние изменения цен:</h4>
                                              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                                {companyPricing[company.id].news.map((news: NewsItem) => (
                                                  <div key={news.id} className="bg-gradient-to-br from-blue-50 to-indigo-50 border border-blue-200 rounded-lg p-4 hover:shadow-md transition-shadow">
                                                    <a
                                                      href={news.source_url}
                                                      target="_blank"
                                                      rel="noopener noreferrer"
                                                      className="text-sm text-gray-900 hover:text-primary-600 font-semibold block mb-2"
                                                    >
                                                      {news.title}
                                                    </a>
                                                    {news.summary && (
                                                      <p className="text-xs text-gray-600 mb-2 line-clamp-2">{news.summary}</p>
                                                    )}
                                                    <div className="text-xs text-gray-500">
                                                      {formatDate(news.published_at || news.created_at)}
                                                    </div>
                                                  </div>
                                                ))}
                                              </div>
                                            </div>
                                          ) : (
                                            !companyPricing[company.id]?.description && (
                                              <div className="text-center py-8 bg-gray-50 rounded-lg border border-gray-200">
                                                <p className="text-sm text-gray-500">
                                                  Информация о ценообразовании пока недоступна
                                                </p>
                                                <p className="text-xs text-gray-400 mt-1">
                                                  Проверьте сайт компании для актуальной информации
                                                </p>
                                              </div>
                                            )
                                          )}
                                        </>
                                      )}
                                    </div>
                                  )}
                                </div>

                                {/* Website и Social Links - внизу */}
                                <div className="pt-4 border-t border-gray-200 space-y-2">
                                  {company.website && (
                                    <div>
                                      <p className="text-xs font-medium text-gray-700 mb-1">Website:</p>
                                      <a
                                        href={company.website}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="text-sm text-primary-600 hover:text-primary-700 break-all inline-flex items-center gap-1"
                                        onClick={(e) => e.stopPropagation()}
                                      >
                                        {company.website}
                                        <ExternalLink className="h-3 w-3" />
                                      </a>
                                    </div>
                                  )}

                                  {(company.twitter_handle || company.github_org) && (
                                    <div className="flex flex-wrap items-center gap-3">
                                      {company.twitter_handle && (
                                        <a
                                          href={`https://twitter.com/${company.twitter_handle}`}
                                          target="_blank"
                                          rel="noopener noreferrer"
                                          className="inline-flex items-center space-x-1 text-sm text-blue-600 hover:text-blue-700"
                                          onClick={(e) => e.stopPropagation()}
                                        >
                                          <Twitter className="h-4 w-4" />
                                          <span>Twitter</span>
                                          <ExternalLink className="h-3 w-3" />
                                        </a>
                                      )}
                                      {company.github_org && (
                                        <a
                                          href={`https://github.com/${company.github_org}`}
                                          target="_blank"
                                          rel="noopener noreferrer"
                                          className="inline-flex items-center space-x-1 text-sm text-gray-600 hover:text-gray-700"
                                          onClick={(e) => e.stopPropagation()}
                                        >
                                          <Github className="h-4 w-4" />
                                          <span>GitHub</span>
                                          <ExternalLink className="h-3 w-3" />
                                        </a>
                                      )}
                                    </div>
                                  )}
                                </div>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>

                {/* Pagination */}
                {companiesTotal > companiesLimit && (
                  <div className="flex items-center justify-between pt-4">
                    <button
                      onClick={() => setCompaniesOffset(Math.max(0, companiesOffset - companiesLimit))}
                      disabled={companiesOffset === 0}
                      className="btn btn-outline btn-sm disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Previous
                    </button>
                    <span className="text-sm text-gray-600">
                      Showing {companiesOffset + 1}-{Math.min(companiesOffset + companiesLimit, companiesTotal)} of {companiesTotal}
                    </span>
                    <button
                      onClick={() => setCompaniesOffset(companiesOffset + companiesLimit)}
                      disabled={companiesOffset + companiesLimit >= companiesTotal}
                      className="btn btn-outline btn-sm disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Next
                    </button>
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {activeTab === 'digest' && (
          <div className="space-y-6">
            {/* Settings Link */}
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <Bell className="w-5 h-5 text-blue-600" />
                  <p className="text-sm text-blue-900">
                    Configure digest settings for automatic delivery
                  </p>
                </div>
                <a href="/digest-settings" className="text-sm font-medium text-blue-600 hover:text-blue-700">
                  Go to Settings →
                </a>
              </div>
            </div>

            <div className="card p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">
                Generate Digests
              </h3>
              <p className="text-gray-600 mb-6">
                Create personalized digests grouped by companies
              </p>
              
              {/* Warning message for tracked mode without companies */}
              {showTrackedOnly && (!userPreferences?.subscribed_companies || userPreferences.subscribed_companies.length === 0) && (
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
                  <div className="flex items-center">
                    <div className="text-yellow-600 mr-2">⚠️</div>
                    <div>
                      <p className="text-sm text-yellow-800 font-medium">No tracked companies found</p>
                      <p className="text-sm text-yellow-700 mt-1">
                        Add companies to your preferences to enable personalized digests in tracked mode.
                      </p>
                    </div>
                  </div>
                </div>
              )}
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <button 
                  onClick={() => fetchDigest('daily')}
                  disabled={digestLoading || (showTrackedOnly && (!userPreferences?.subscribed_companies || userPreferences.subscribed_companies.length === 0))}
                  className="btn btn-outline btn-md flex flex-col items-center p-4"
                >
                  <span className="font-medium">
                    Daily Digest
                  </span>
                </button>
                <button 
                  onClick={() => fetchDigest('weekly')}
                  disabled={digestLoading || (showTrackedOnly && (!userPreferences?.subscribed_companies || userPreferences.subscribed_companies.length === 0))}
                  className="btn btn-outline btn-md flex flex-col items-center p-4"
                >
                  <span className="font-medium">
                    Weekly Digest
                  </span>
                </button>
                <button 
                  onClick={() => fetchDigest('custom')}
                  disabled={digestLoading || (showTrackedOnly && (!userPreferences?.subscribed_companies || userPreferences.subscribed_companies.length === 0))}
                  className="btn btn-outline btn-md flex flex-col items-center p-4"
                >
                  <span className="font-medium">
                    Custom Period
                  </span>
                </button>
              </div>
            </div>

            {/* Error Message */}
            {digestError && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                <p className="text-sm text-red-800">{digestError}</p>
              </div>
            )}

            {/* Digest Results */}
            <div className="card p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900">
                  Digest Results
                </h3>
                {digest && (
                  <span className="text-sm text-gray-500">
                    {digest.news_count} news items • {digest.format}
                  </span>
                )}
              </div>

              {digestLoading && (
                <div className="text-center py-8">
                  <SkeletonLoader type="text" count={3} />
                  <p className="text-gray-600 mt-4">Generating digest...</p>
                </div>
              )}

              {!digestLoading && !digest && !digestError && (
                <div className="text-center py-8">
                  <p className="text-gray-600">Click a button above to generate a digest</p>
                  <p className="text-sm text-gray-500 mt-2">
                    Digests are grouped by companies for better organization
                  </p>
                </div>
              )}

              {!digestLoading && digest && (
                <div className="space-y-6">
                  {/* Period Information */}
                  <div className="bg-gray-50 rounded-lg p-4 mb-6">
                    <div className="flex items-center justify-between">
                      <div>
                        <h4 className="font-medium text-gray-900">Digest Period</h4>
                        <p className="text-sm text-gray-600">
                          {new Date(digest.date_from).toLocaleDateString('en-US', {
                            year: 'numeric',
                            month: 'long',
                            day: 'numeric'
                          })} - {new Date(digest.date_to).toLocaleDateString('en-US', {
                            year: 'numeric',
                            month: 'long',
                            day: 'numeric'
                          })}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="text-sm font-medium text-gray-900">{digest.news_count} news items</p>
                        <p className="text-xs text-gray-500 capitalize">{digest.format} format</p>
                        {digest.companies_count && (
                          <p className="text-xs text-gray-500">{digest.companies_count} companies</p>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Отображение по компаниям */}
                  {digest.format === 'by_company' && digest.companies && (
                    <div className="space-y-6">
                      {Object.entries(digest.companies).map(([companyId, companyData]) => (
                        <div key={companyId} className="bg-white border border-gray-200 rounded-lg p-6">
                          <div className="flex items-center justify-between mb-4">
                            <div className="flex items-center">
                              {companyData.company.logo_url && (
                                <img
                                  src={companyData.company.logo_url}
                                  alt={companyData.company.name}
                                  className="w-10 h-10 rounded-lg mr-3"
                                />
                              )}
                              <div>
                                <h4 className="font-semibold text-gray-900">{companyData.company.name}</h4>
                                <p className="text-sm text-gray-600">{companyData.stats.total} news items</p>
                              </div>
                            </div>
                            <div className="text-right">
                              <div className="text-sm text-gray-500">Categories</div>
                              <div className="text-lg font-semibold text-primary-600">
                                {Object.keys(companyData.stats.by_category).length}
                              </div>
                            </div>
                          </div>
                          
                          {/* Группировка по категориям */}
                          {Object.entries(companyData.stats.by_category).map(([category, count]) => (
                            <div key={category} className="mb-3">
                              <div className="flex items-center justify-between mb-2">
                                <span className="text-sm font-medium text-gray-700">
                                  {categoryLabels[category] || category}
                                </span>
                                <span className="text-sm text-gray-500">{count} items</span>
                              </div>
                              {/* Новости этой категории */}
                              <div className="space-y-2">
                                {companyData.news
                                  .filter(news => (news.category || 'other') === category)
                                  .map((news: any) => (
                                    <div key={news.id} className="border-l-2 border-primary-200 pl-3">
                                      <a
                                        href={news.source_url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="text-sm text-gray-900 hover:text-primary-600"
                                      >
                                        {news.title}
                                      </a>
                                      <div className="text-xs text-gray-500 mt-1">
                                        {formatDate(news.published_at)}
                                      </div>
                                    </div>
                                  ))}
                              </div>
                            </div>
                          ))}
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Fallback для старого формата по категориям (если вдруг придет) */}
                  {digest.format === 'by_category' && digest.categories && Object.entries(digest.categories).map(([category, items]) => (
                    <div key={category}>
                      <h4 className="font-semibold text-gray-900 mb-3 flex items-center">
                        <span className="px-2 py-1 text-sm rounded bg-primary-100 text-primary-700 mr-2">
                          {categoryLabels[category] || category}
                        </span>
                        <span className="text-sm text-gray-500">({items.length})</span>
                      </h4>
                      <div className="space-y-4">
                        {items.map((item: any) => (
                          <div key={item.id} className="border-b border-gray-100 pb-4 last:border-0">
                            <div className="flex items-start justify-between">
                              <div className="flex-1">
                                <a 
                                  href={item.source_url} 
                                  target="_blank" 
                                  rel="noopener noreferrer"
                                  className="text-base font-medium text-gray-900 hover:text-primary-600"
                                >
                                  {item.title}
                                </a>
                                {item.summary && <p className="text-sm text-gray-600 mt-1">{item.summary}</p>}
                                <div className="flex items-center space-x-3 mt-2">
                                  {item.company && (
                                    <span className="px-2 py-1 text-xs rounded-full bg-blue-100 text-blue-700">
                                      {item.company.name}
                                    </span>
                                  )}
                                  <span className="text-xs text-gray-500">
                                    {formatDate(item.published_at)}
                                  </span>
                                </div>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                  
                  {(!digest.companies || Object.keys(digest.companies).length === 0) &&
                   (!digest.categories || Object.keys(digest.categories).length === 0) && (
                    <p className="text-center text-gray-500 py-4">
                      No news items found for this period
                    </p>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Delete Confirmation Modal */}
      <ConfirmDeleteModal
        isOpen={deleteModal.isOpen}
        onClose={() => setDeleteModal({ isOpen: false, report: null })}
        onConfirm={async () => {
          if (!deleteModal.report) return
          
          setIsDeleting(true)
          try {
            const report = deleteModal.report
            
            // Остановить polling, если он был
            if (pollingIntervals[report.id]) {
              clearInterval(pollingIntervals[report.id])
              setPollingIntervals(prev => {
                const next = { ...prev }
                delete next[report.id]
                return next
              })
            }
            
            await ApiService.deleteReport(report.id)
            
            // Удалить из списка
            setReports(prev => prev.filter(r => r.id !== report.id))
            setReportData(prev => {
              const next = { ...prev }
              delete next[report.id]
              return next
            })
            setExpandedReports(prev => {
              const next = new Set(prev)
              next.delete(report.id)
              return next
            })
            setReportTabs(prev => {
              const next = { ...prev }
              delete next[report.id]
              return next
            })
            
            toast.success('Report deleted successfully')
            setDeleteModal({ isOpen: false, report: null })
          } catch (error: any) {
            const errorMessage = error?.response?.data?.detail || 'Failed to delete report'
            toast.error(errorMessage)
            console.error('Failed to delete report:', error)
          } finally {
            setIsDeleting(false)
          }
        }}
        title="Delete Report"
        message={`Are you sure you want to delete the report for "${deleteModal.report?.query}"? This action cannot be undone.`}
        confirmText="Delete Report"
        cancelText="Cancel"
        isLoading={isDeleting}
      />

      {/* Add Competitors to Tracked Modal */}
      <AddCompetitorsModal
        isOpen={addCompetitorsModal.isOpen}
        onClose={() => setAddCompetitorsModal({ isOpen: false, report: null })}
        competitors={addCompetitorsModal.report?.competitors || []}
        subscribedCompanyIds={userPreferences?.subscribed_companies || []}
        onSuccess={async () => {
          console.log('AddCompetitorsModal onSuccess called - refreshing preferences')
          try {
            // Инвалидировать кэш
            queryClient.invalidateQueries({ queryKey: ['user-preferences'] })
            // Принудительно обновить данные
            await queryClient.refetchQueries({ queryKey: ['user-preferences'], exact: true })
            console.log('AddCompetitorsModal - Preferences refetched')
            // Обновить дашборд с небольшой задержкой чтобы preferences успели обновиться
            setTimeout(() => {
              fetchDashboardData()
            }, 300)
          } catch (error) {
            console.error('AddCompetitorsModal - Error refreshing preferences:', error)
          }
        }}
      />

      {/* Add Competitor Modal */}
      <AddCompetitorModal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
        onSuccess={() => {
          // Обновить список компаний
          fetchCompanies()
          // Обновить дашборд
          fetchDashboardData()
        }}
      />

      {/* Company Search Modal */}
      <CompanySearchModal
        isOpen={showSearchModal}
        onClose={() => setShowSearchModal(false)}
        onSuccess={() => {
          // Обновить список компаний
          fetchCompanies()
          // Обновить дашборд
          fetchDashboardData()
          // Переключиться на вкладку competitors
          handleTabChange('competitors')
        }}
      />

      {/* Onboarding Modal */}
      {showOnboarding && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg max-w-2xl w-full p-6 shadow-xl">
            <div className="flex justify-between items-start mb-4">
              <h3 className="text-2xl font-bold text-gray-900">Welcome to Dashboard!</h3>
              <button
                onClick={() => {
                  setShowOnboarding(false)
                  localStorage.setItem('has-seen-dashboard-onboarding', 'true')
                }}
                className="text-gray-400 hover:text-gray-600 text-2xl leading-none"
              >
                ×
              </button>
            </div>
            
            <div className="space-y-4 mb-6">
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center flex-shrink-0">
                  <span className="text-primary-600 font-bold">1</span>
                </div>
                <div>
                  <h4 className="font-semibold text-gray-900 mb-1">Search for Companies</h4>
                  <p className="text-sm text-gray-600">
                    Use the search bar above to find companies by name or website URL
                  </p>
                </div>
              </div>
              
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center flex-shrink-0">
                  <span className="text-primary-600 font-bold">2</span>
                </div>
                <div>
                  <h4 className="font-semibold text-gray-900 mb-1">Track Companies</h4>
                  <p className="text-sm text-gray-600">
                    Add companies to your list to get personalized news updates
                  </p>
                </div>
              </div>
              
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center flex-shrink-0">
                  <span className="text-primary-600 font-bold">3</span>
                </div>
                <div>
                  <h4 className="font-semibold text-gray-900 mb-1">View Insights</h4>
                  <p className="text-sm text-gray-600">
                    Check the Overview tab for statistics and recent news from your tracked companies
                  </p>
                </div>
              </div>
            </div>
            
            <button
              onClick={() => {
                setShowOnboarding(false)
                localStorage.setItem('has-seen-dashboard-onboarding', 'true')
                setShowSearchModal(true)
              }}
              className="btn btn-primary w-full"
            >
              Start Searching
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
