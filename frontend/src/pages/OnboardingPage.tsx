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
import { Loader2 } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import toast from 'react-hot-toast'
import { useNavigate } from 'react-router-dom'

// Используем sessionStorage вместо localStorage для безопасности:
// - Автоматически очищается при закрытии вкладки
// - Меньше окно для XSS атак
// - Подходит для временных сессий онбординга
const ONBOARDING_SESSION_KEY = 'onboarding_session_token'

export default function OnboardingPage() {
  const navigate = useNavigate()
  const { user } = useAuthStore()
  const queryClient = useQueryClient()
  const initRef = useRef(false)
  const [sessionToken, setSessionToken] = useState<string | null>(null)
  const [currentStep, setCurrentStep] = useState<OnboardingStep>('company_input')
  const [company, setCompany] = useState<OnboardingCompanyData | null>(null)
  const [competitors, setCompetitors] = useState<OnboardingCompetitor[]>([])
  const [observationTaskId, setObservationTaskId] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isProcessing, setIsProcessing] = useState(false)
  const [showAuthModal, setShowAuthModal] = useState(false)

  // Initialize onboarding session
  useEffect(() => {
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
        navigate('/')
      } finally {
        setIsLoading(false)
      }
    }

    initSession()
  }, [])

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

  const handleSelectCompetitors = async (competitorIds: string[]) => {
    if (!sessionToken) {
      toast.error('Сессия не инициализирована')
      return
    }

    setIsProcessing(true)
    try {
      await ApiService.selectCompetitorsInOnboarding(sessionToken, competitorIds)
      
      // Load selected competitors
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
      toast('Загрузка дополнительных конкурентов...', { icon: 'ℹ️' })
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

  // TODO: Функция для создания отчёта по компании
  // Закомментирована, так как сейчас не требуется автоматическое создание отчётов
  // после онбординга. Компании автоматически добавляются в subscribed_companies,
  // и новости будут парситься автоматически.
  // 
  // const createCompanyReport = async (companyData: OnboardingCompanyData) => {
  //   const query = companyData.website || companyData.name
  //   
  //   if (!query) {
  //     console.warn('Нет данных для создания отчёта по компании')
  //     return
  //   }
  //
  //   const toastId = toast.loading('Создаём отчёт по компании...')
  //   try {
  //     const { status } = await ApiService.createReport(query)
  //
  //     if (status === 'ready') {
  //       toast.success('Отчёт готов!', { id: toastId })
  //     } else {
  //       toast.success('Отчёт формируется. Мы сообщим, когда будет готов.', { id: toastId })
  //     }
  //   } catch (error: any) {
  //     toast.error(error?.response?.data?.detail || 'Не удалось создать отчёт', { id: toastId })
  //     console.error('Ошибка создания отчёта после онбординга:', error)
  //   }
  // }

  const handleObservationComplete = async () => {
    if (!sessionToken) {
      toast.error('Сессия не инициализирована')
      return
    }

    setIsProcessing(true)
    try {
      await ApiService.completeOnboarding(sessionToken, user?.id)
      setCurrentStep('completed')
      toast.success('Онбординг завершен успешно!')
      
      // Очистить session token из sessionStorage
      sessionStorage.removeItem(ONBOARDING_SESSION_KEY)
      
      // Обновить кэш preferences, чтобы новые компании отобразились
      if (user?.id) {
        await queryClient.invalidateQueries({ queryKey: ['user-preferences'] })
      }

      // TODO: Автоматическое создание отчётов после завершения наблюдения
      // В будущем можно реализовать автоматическое создание отчётов для всех компаний
      // из онбординга (родительская компания + конкуренты).
      // Сейчас компании автоматически добавляются в subscribed_companies на бэкенде,
      // и новости будут парситься автоматически без создания отчётов.
      //
      // const response = await ApiService.completeOnboarding(sessionToken, user?.id)
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
      //   toast.success('Отчёты созданы для всех компаний!')
      // } else if (company) {
      //   await createCompanyReport(company)
      // }
    } catch (err: any) {
      toast.error(err.message || 'Ошибка при завершении онбординга')
    } finally {
      setIsProcessing(false)
    }
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
      setCurrentStep('completed')
      toast.success('Онбординг завершен! Перенаправляем на платформу...')
      
      // Обновить кэш preferences, чтобы новые компании отобразились на dashboard
      await queryClient.invalidateQueries({ queryKey: ['user-preferences'] })
      
      // TODO: Автоматическое создание отчётов после авторизации в онбординге
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

  if (isLoading || !sessionToken) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-primary-600 animate-spin" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4">
      <div className="max-w-7xl mx-auto">
        {/* Progress indicator */}
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

        {currentStep === 'competitor_selection' && (
          <CompetitorSelectionStep
            sessionToken={sessionToken}
            onSelectCompetitors={handleSelectCompetitors}
            onReplaceCompetitor={handleReplaceCompetitor}
            onLoadMore={handleLoadMoreCompetitors}
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

      {/* Auth Modal */}
      <AuthModal
        isOpen={showAuthModal}
        onClose={() => setShowAuthModal(false)}
        onSuccess={handleAuthSuccess}
      />
    </div>
  )
}

