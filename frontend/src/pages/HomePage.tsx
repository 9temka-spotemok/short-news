import AuthModal from '@/components/onboarding/AuthModal'
import CompanyCardStep from '@/components/onboarding/CompanyCardStep'
import CompanyInputStep from '@/components/onboarding/CompanyInputStep'
import CompetitorSelectionStep from '@/components/onboarding/CompetitorSelectionStep'
import ObservationSetupStep from '@/components/onboarding/ObservationSetupStep'
import OnboardingCompleteStep from '@/components/onboarding/OnboardingCompleteStep'
import { ApiService } from '@/services/api'
import { useAuthStore } from '@/store/authStore'
import type {
  OnboardingCompanyData,
  OnboardingCompetitor,
  OnboardingStep
} from '@/types'
import { useQueryClient } from '@tanstack/react-query'
import { ArrowRight, Bell, Filter, Loader2, TrendingUp, Zap } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import toast from 'react-hot-toast'
import { Link, useNavigate } from 'react-router-dom'

// Используем sessionStorage вместо localStorage для безопасности:
// - Автоматически очищается при закрытии вкладки
// - Меньше окно для XSS атак
// - Подходит для временных сессий онбординга
const ONBOARDING_SESSION_KEY = 'onboarding_session_token'

export default function HomePage() {
  const navigate = useNavigate()
  const { isAuthenticated } = useAuthStore()
  const queryClient = useQueryClient()
  const initRef = useRef(false)
  
  // Onboarding states
  const [sessionToken, setSessionToken] = useState<string | null>(null)
  const [currentStep, setCurrentStep] = useState<OnboardingStep>('company_input')
  const [company, setCompany] = useState<OnboardingCompanyData | null>(null)
  const [competitors, setCompetitors] = useState<OnboardingCompetitor[]>([])
  const [observationTaskId, setObservationTaskId] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isProcessing, setIsProcessing] = useState(false)
  const [showAuthModal, setShowAuthModal] = useState(false)

  // Clear onboarding session when user authenticates or logs out
  useEffect(() => {
    if (isAuthenticated) {
      // Очистить сессию онбординга при авторизации
      sessionStorage.removeItem(ONBOARDING_SESSION_KEY)
      setSessionToken(null)
      setCurrentStep('company_input')
      setCompany(null)
      setCompetitors([])
      setObservationTaskId(null)
      setIsLoading(false)
    } else {
      // Очистить сессию онбординга при выходе из системы
      // Это важно, чтобы прогресс-бар не оставался видимым
      const existingToken = sessionStorage.getItem(ONBOARDING_SESSION_KEY)
      if (existingToken) {
        sessionStorage.removeItem(ONBOARDING_SESSION_KEY)
        setSessionToken(null)
        setCurrentStep('company_input')
        setCompany(null)
        setCompetitors([])
        setObservationTaskId(null)
      }
    }
  }, [isAuthenticated])

  // Initialize onboarding session (only if not authenticated)
  useEffect(() => {
    if (isAuthenticated) {
      return
    }

    // Prevent double initialization (React.StrictMode in dev)
    if (initRef.current) {
      return
    }
    initRef.current = true

    const initSession = async () => {
      try {
        // Check if we have an existing session token in sessionStorage
        // Используем sessionStorage для безопасности (автоматически очищается при закрытии вкладки)
        const existingToken = sessionStorage.getItem(ONBOARDING_SESSION_KEY)
        
        if (existingToken) {
          // Try to load existing session
          try {
            const response = await ApiService.getOnboardingCompany(existingToken)
            setSessionToken(existingToken)
            setCurrentStep(response.current_step as OnboardingStep)
            setCompany(response.company)
            setIsLoading(false)
            return
          } catch (err) {
            // Session expired or invalid, create new one
            sessionStorage.removeItem(ONBOARDING_SESSION_KEY)
          }
        }

        // Create new session
        const response = await ApiService.startOnboarding()
        setSessionToken(response.session_token)
        setCurrentStep(response.current_step as OnboardingStep)
        
        // Save session token to sessionStorage (безопаснее, чем localStorage)
        sessionStorage.setItem(ONBOARDING_SESSION_KEY, response.session_token)
        
        // If we're past company_input, load company data
        if (response.current_step !== 'company_input') {
          await loadCompanyData(response.session_token)
        }
      } catch (err: any) {
        toast.error(err.message || 'Ошибка при инициализации онбординга')
      } finally {
        setIsLoading(false)
      }
    }

    initSession()
  }, [isAuthenticated])

  const loadCompanyData = async (token: string) => {
    try {
      const response = await ApiService.getOnboardingCompany(token)
      setCompany(response.company)
    } catch (err: any) {
      console.error('Error loading company data:', err)
    }
  }

  const handleAnalyzeCompany = async (websiteUrl: string) => {
    if (!sessionToken) {
      toast.error('Сессия не инициализирована')
      return
    }

    setIsProcessing(true)
    try {
      const response = await ApiService.analyzeCompanyForOnboarding(websiteUrl, sessionToken)
      setCompany(response.company)
      setCurrentStep(response.current_step as OnboardingStep)
    } catch (err: any) {
      toast.error(err.message || 'Ошибка при анализе компании')
      throw err
    } finally {
      setIsProcessing(false)
    }
  }

  const handleCompanyCardContinue = () => {
    setCurrentStep('competitor_selection')
  }

  const handleSelectCompetitors = async (competitorIds: string[], competitorData?: any[]) => {
    if (!sessionToken) {
      toast.error('Сессия не инициализирована')
      return
    }

    setIsProcessing(true)
    try {
      // If competitor data is not provided, try to load it from suggestions
      let competitorDataToSend = competitorData
      if (!competitorDataToSend) {
        const suggestResponse = await ApiService.suggestCompetitorsForOnboarding(sessionToken, 50)
        competitorDataToSend = suggestResponse.competitors
          .filter(c => competitorIds.includes(c.company.id))
          .map(c => c)
      }
      
      await ApiService.selectCompetitorsInOnboarding(sessionToken, competitorIds, competitorDataToSend)
      
      // Load selected competitors for display
      const suggestResponse = await ApiService.suggestCompetitorsForOnboarding(sessionToken, 50)
      const selected = suggestResponse.competitors
        .map(c => c.company)
        .filter(c => competitorIds.includes(c.id))
      setCompetitors(selected)
      
      // Move to observation setup
      await handleObservationSetup()
    } catch (err: any) {
      toast.error(err.message || 'Ошибка при сохранении выбора конкурентов')
      throw err
    } finally {
      setIsProcessing(false)
    }
  }

  const handleReplaceCompetitor = async (competitorId: string): Promise<OnboardingCompetitor> => {
    if (!sessionToken) {
      throw new Error('Сессия не инициализирована')
    }

    const response = await ApiService.replaceCompetitorInOnboarding(sessionToken, competitorId)
    return {
      id: response.company.id || `temp-${Date.now()}-${Math.random()}`,
      name: response.company.name || 'Unknown Company',
      website: response.company.website || '',
      logo_url: response.company.logo_url || null,
      category: response.company.category || null,
      description: response.company.description || null,
      ai_description: response.company.ai_description || response.company.description || undefined,
      similarity_score: response.similarity_score,
      common_categories: response.common_categories || [],
      reason: response.reason || ''
    }
  }

  const handleLoadMoreCompetitors = async () => {
    if (!sessionToken) return

    try {
      // This will be handled by CompetitorSelectionStep internally
      // We can extend the API to support pagination if needed
    } catch (err: any) {
      toast.error(err.message || 'Ошибка при загрузке конкурентов')
    }
  }

  const handleObservationSetup = async () => {
    if (!sessionToken) {
      toast.error('Сессия не инициализирована')
      return
    }

    setIsProcessing(true)
    try {
      const response = await ApiService.setupObservation(sessionToken)
      setObservationTaskId(response.task_id)
      setCurrentStep('observation_setup')
    } catch (err: any) {
      toast.error(err.message || 'Ошибка при настройке наблюдения')
    } finally {
      setIsProcessing(false)
    }
  }

  const handleObservationComplete = () => {
    setCurrentStep('completed')
  }

  const handleAuthRequired = () => {
    setShowAuthModal(true)
  }

  const handleAuthSuccess = async (userId: string) => {
    if (!sessionToken) {
      toast.error('Сессия онбординга не найдена')
      return
    }

    setIsProcessing(true)
    try {
      await ApiService.completeOnboarding(sessionToken, userId)
      toast.success('Онбординг завершен! Перенаправляем на платформу...')
      
      // Очистить session token из sessionStorage
      sessionStorage.removeItem(ONBOARDING_SESSION_KEY)
      
      // Обновить кэш preferences, чтобы новые компании отобразились на dashboard
      await queryClient.invalidateQueries({ queryKey: ['user-preferences'] })
      
      // TODO: Автоматическое создание отчётов после онбординга
      // В будущем можно реализовать автоматическое создание отчётов для всех компаний
      // из онбординга (родительская компания + конкуренты).
      // Сейчас компании автоматически добавляются в subscribed_companies на бэкенде,
      // и новости будут парситься автоматически без создания отчётов.
      //
      // const response = await ApiService.completeOnboarding(sessionToken, userId)
      // const companiesToReport = response.companies || []
      // if (companiesToReport.length > 0) {
      //   const reportPromises = companiesToReport.map(async (comp: any) => {
      //     try {
      //       const query = comp.website || comp.name
      //       if (query) {
      //         await ApiService.createReport(query)
      //       }
      //     } catch (err) {
      //       console.error(`Failed to create report for ${comp.name}:`, err)
      //     }
      //   })
      //   await Promise.allSettled(reportPromises)
      //   toast.success('Отчёты созданы! Перенаправляем на платформу...')
      // }
      
      navigate('/dashboard')
    } catch (err: any) {
      toast.error(err.message || 'Ошибка при завершении онбординга')
    } finally {
      setIsProcessing(false)
    }
  }

  // If loading, show loader
  if (isLoading || (!isAuthenticated && !sessionToken)) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <Loader2 className="w-8 h-8 text-primary-600 animate-spin" />
      </div>
    )
  }

  return (
    <div className="bg-white">
      {/* Hero Section - Always visible */}
      <div className="relative overflow-hidden">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
          <div className="text-center">
            <h1 className="text-4xl md:text-6xl font-bold text-gray-900 mb-6">
              AI-based
              <span className="text-primary-600"> Competitor Analysis Center</span>
            </h1>
            <p className="text-xl text-gray-600 mb-8 max-w-3xl mx-auto">
              An intelligent platform for monitoring your competitors. 
              Get the latest news from them and keep up to date with all important events.
            </p>
            {isAuthenticated ? (
              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <Link to="/dashboard" className="btn btn-primary btn-lg">
                  Go to Dashboard
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Link>
                <Link to="/news" className="btn btn-outline btn-lg">
                  View News
                </Link>
              </div>
            ) : null}
          </div>
        </div>
      </div>

      {/* Onboarding Section - Only for non-authenticated users */}
      {!isAuthenticated && (
        <div className="py-12 px-4 bg-gray-50">
          <div className="max-w-7xl mx-auto">
            {/* Progress indicator - Show only after company_input */}
            {currentStep !== 'company_input' && (
              <div className="mb-8">
                <div className="flex items-center justify-center gap-2 mb-4">
                  {['company_input', 'company_card', 'competitor_selection', 'observation_setup', 'completed'].map((step, idx) => {
                    const stepIndex = ['company_input', 'company_card', 'competitor_selection', 'observation_setup', 'completed'].indexOf(currentStep)
                    const isActive = idx <= stepIndex
                    
                    return (
                      <div key={step} className="flex items-center">
                        <div
                          className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                            isActive
                              ? 'bg-primary-600 text-white'
                              : 'bg-gray-200 text-gray-500'
                          }`}
                        >
                          {idx + 1}
                        </div>
                        {idx < 4 && (
                          <div
                            className={`w-16 h-1 mx-1 ${
                              isActive ? 'bg-primary-600' : 'bg-gray-200'
                            }`}
                          />
                        )}
                      </div>
                    )
                  })}
                </div>
              </div>
            )}

            {/* Step content */}
            {currentStep === 'company_input' && (
              <CompanyInputStep
                onAnalyze={handleAnalyzeCompany}
                isLoading={isProcessing}
              />
            )}

            {currentStep === 'company_card' && company && (
              <CompanyCardStep
                company={company}
                onContinue={handleCompanyCardContinue}
              />
            )}

            {currentStep === 'competitor_selection' && sessionToken && (
              <CompetitorSelectionStep
                sessionToken={sessionToken}
                onSelectCompetitors={handleSelectCompetitors}
                onReplaceCompetitor={handleReplaceCompetitor}
                onLoadMore={handleLoadMoreCompetitors}
                onCompleteOnboarding={handleAuthSuccess}
                isLoading={isProcessing}
              />
            )}

            {currentStep === 'observation_setup' && observationTaskId && (
              <ObservationSetupStep
                taskId={observationTaskId}
                onComplete={handleObservationComplete}
              />
            )}

            {currentStep === 'completed' && company && competitors.length > 0 && (
              <OnboardingCompleteStep
                company={company}
                competitors={competitors}
                onAuthRequired={handleAuthRequired}
              />
            )}
          </div>
        </div>
      )}

      {/* Features Section */}
      <div className="py-24 bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-gray-900 mb-4">
              Why Choose shot-news?
            </h2>
            <p className="text-xl text-gray-600 max-w-2xl mx-auto">
              We use modern AI technologies to provide the most 
              relevant information about industry developments.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            <div className="text-center">
              <div className="w-16 h-16 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <TrendingUp className="h-8 w-8 text-primary-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Trend Analysis
              </h3>
              <p className="text-gray-600">
                Track key trends and changes in the industry
              </p>
            </div>

            <div className="text-center">
              <div className="w-16 h-16 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Filter className="h-8 w-8 text-primary-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Smart Filtering
              </h3>
              <p className="text-gray-600">
                AI algorithms select only news relevant to you
              </p>
            </div>

            <div className="text-center">
              <div className="w-16 h-16 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Bell className="h-8 w-8 text-primary-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Personalization
              </h3>
              <p className="text-gray-600">
                Receive digests tailored to your interests
              </p>
            </div>

            <div className="text-center">
              <div className="w-16 h-16 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Zap className="h-8 w-8 text-primary-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Fast and Accurate
              </h3>
              <p className="text-gray-600">
                Real-time updates with high accuracy
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Stats Section */}
      <div className="py-24 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 text-center">
            <div>
              <div className="text-4xl font-bold text-primary-600 mb-2">50+</div>
              <div className="text-gray-600">Tracked Companies</div>
            </div>
            <div>
              <div className="text-4xl font-bold text-primary-600 mb-2">1000+</div>
              <div className="text-gray-600">News per Day</div>
            </div>
            <div>
              <div className="text-4xl font-bold text-primary-600 mb-2">99.5%</div>
              <div className="text-gray-600">Classification Accuracy</div>
            </div>
          </div>
        </div>
      </div>

      {/* CTA Section */}
      <div className="py-24 bg-primary-600">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl font-bold text-white mb-4">
            Ready to Get Started?
          </h2>
          <p className="text-xl text-primary-100 mb-8 max-w-2xl mx-auto">
            Join the community of your industry professionals 
            and get the latest information first.
          </p>
        </div>
      </div>

      {/* Auth Modal */}
      <AuthModal
        isOpen={showAuthModal}
        onClose={() => setShowAuthModal(false)}
        onSuccess={handleAuthSuccess}
      />
    </div>
  )
}
