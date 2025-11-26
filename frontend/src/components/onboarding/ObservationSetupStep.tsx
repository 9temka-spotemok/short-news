import type { OnboardingObservationStatusResponse } from '@/types'
import { CheckCircle2, Loader2, AlertCircle } from 'lucide-react'
import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'

interface ObservationSetupStepProps {
  taskId: string
  onComplete: () => void
}

// Маппинг этапов на понятные названия
const stepLabels: Record<string, string> = {
  'initializing': 'Инициализация...',
  'processing_company': 'Обработка компании',
  'discovering_social_media': 'Поиск соцсетей',
  'capturing_structure': 'Парсинг структуры сайта',
  'scraping_press_releases': 'Сбор пресс-релизов',
  'detecting_marketing': 'Отслеживание маркетинга',
  'collecting_seo': 'Сбор SEO сигналов',
  'building_matrix': 'Формирование матрицы мониторинга',
  'completed': 'Завершено'
}

export default function ObservationSetupStep({ taskId, onComplete }: ObservationSetupStepProps) {
  const [status, setStatus] = useState<OnboardingObservationStatusResponse | null>(null)
  const [isPolling, setIsPolling] = useState(true)
  const [showRetry, setShowRetry] = useState(false)

  useEffect(() => {
    if (!taskId || !isPolling) return

    const pollStatus = async () => {
      try {
        const { ApiService } = await import('@/services/api')
        const response = await ApiService.getObservationStatus(taskId)
        setStatus(response)

        if (response.status === 'completed') {
          setIsPolling(false)
          toast.success('Наблюдение настроено успешно!')
          // Wait a bit before calling onComplete
          setTimeout(() => {
            onComplete()
          }, 1000)
        } else if (response.status === 'failed') {
          setIsPolling(false)
          setShowRetry(true)
          toast.error(response.message || 'Ошибка при настройке наблюдения')
        }
      } catch (err: any) {
        console.error('Error polling observation status:', err)
        // Continue polling even on error
      }
    }

    // Poll immediately
    pollStatus()

    // Then poll every 2 seconds
    const interval = setInterval(pollStatus, 2000)

    return () => clearInterval(interval)
  }, [taskId, isPolling, onComplete])

  const getStatusMessage = () => {
    if (!status) return 'Инициализация...'
    
    // Используем message из ответа, если есть
    if (status.message) {
      return status.message
    }
    
    switch (status.status) {
      case 'pending':
        return 'Ожидание начала обработки...'
      case 'processing':
        return 'Собираем данные о выбранных конкурентах...'
      case 'completed':
        return 'Наблюдение настроено успешно!'
      case 'failed':
        return 'Ошибка при настройке наблюдения'
      default:
        return 'Обработка...'
    }
  }

  const getCurrentStepLabel = () => {
    if (!status) return null
    
    // Пытаемся получить current_step из расширенного ответа
    const extendedStatus = status as any
    const currentStep = extendedStatus.current_step
    
    if (currentStep && stepLabels[currentStep]) {
      return stepLabels[currentStep]
    }
    
    return null
  }

  const getCurrentCompany = () => {
    if (!status) return null
    
    const extendedStatus = status as any
    return extendedStatus.current_company || null
  }

  const getProgressDetails = () => {
    if (!status) return null
    
    const extendedStatus = status as any
    const total = extendedStatus.total
    const completed = extendedStatus.completed
    
    if (total && completed !== undefined) {
      return `${completed} из ${total}`
    }
    
    return null
  }

  const handleRetry = () => {
    setShowRetry(false)
    setIsPolling(true)
    // Перезапуск polling
    const pollStatus = async () => {
      try {
        const { ApiService } = await import('@/services/api')
        const response = await ApiService.getObservationStatus(taskId)
        setStatus(response)
      } catch (err: any) {
        console.error('Error polling observation status:', err)
      }
    }
    pollStatus()
  }

  const getProgress = () => {
    if (!status) return 0
    if (status.progress !== undefined) return status.progress
    // Estimate progress based on status
    switch (status.status) {
      case 'pending':
        return 10
      case 'processing':
        return 50
      case 'completed':
        return 100
      default:
        return 0
    }
  }

  return (
    <div className="max-w-2xl mx-auto">
      <div className="text-center mb-8">
        <h2 className="text-3xl font-bold text-gray-900 mb-2">
          Настраиваем наблюдение за конкурентами
        </h2>
        <p className="text-gray-600">
          Мы собираем данные о выбранных конкурентах. Это займёт 15–60 секунд
        </p>
      </div>

      <div className="bg-white rounded-lg shadow-lg p-8">
        <div className="flex flex-col items-center justify-center py-8">
          {status?.status === 'completed' ? (
            <CheckCircle2 className="w-16 h-16 text-green-500 mb-4" />
          ) : status?.status === 'failed' ? (
            <AlertCircle className="w-16 h-16 text-red-500 mb-4" />
          ) : (
            <Loader2 className="w-16 h-16 text-primary-600 animate-spin mb-4" />
          )}

          <p className="text-lg text-gray-700 mb-2 text-center font-medium">
            {getStatusMessage()}
          </p>

          {/* Детальная информация о текущем этапе */}
          {getCurrentStepLabel() && (
            <p className="text-sm text-gray-600 mb-1 text-center">
              {getCurrentStepLabel()}
              {getCurrentCompany() && ` • ${getCurrentCompany()}`}
            </p>
          )}

          {getProgressDetails() && (
            <p className="text-xs text-gray-500 mb-4 text-center">
              Компаний обработано: {getProgressDetails()}
            </p>
          )}

          {/* Progress bar */}
          <div className="w-full max-w-md mb-4">
            <div className="h-3 bg-gray-200 rounded-full overflow-hidden">
              <div
                className="h-full bg-primary-600 transition-all duration-300"
                style={{ width: `${getProgress()}%` }}
              />
            </div>
            <div className="flex items-center justify-between mt-2">
              <span className="text-sm text-gray-500">
                {getProgress()}%
              </span>
              {getProgressDetails() && (
                <span className="text-xs text-gray-400">
                  {getProgressDetails()}
                </span>
              )}
            </div>
          </div>

          {/* Кнопка повтора при ошибке */}
          {showRetry && status?.status === 'failed' && (
            <button
              onClick={handleRetry}
              className="mt-4 px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors font-medium"
            >
              Повторить
            </button>
          )}

          {/* Список этапов (визуализация прогресса) */}
          {status?.status === 'processing' && (
            <div className="w-full max-w-md mt-6 space-y-2">
              <div className="text-xs font-semibold text-gray-500 mb-2">Этапы обработки:</div>
              {Object.entries(stepLabels).slice(0, 6).map(([stepKey, stepLabel]) => {
                const extendedStatus = status as any
                const currentStep = extendedStatus.current_step
                const isActive = currentStep === stepKey
                const isCompleted = currentStep && 
                  Object.keys(stepLabels).indexOf(currentStep) > Object.keys(stepLabels).indexOf(stepKey)
                
                return (
                  <div key={stepKey} className="flex items-center gap-2 text-sm">
                    {isCompleted ? (
                      <CheckCircle2 className="w-4 h-4 text-green-500 flex-shrink-0" />
                    ) : isActive ? (
                      <Loader2 className="w-4 h-4 text-primary-600 animate-spin flex-shrink-0" />
                    ) : (
                      <div className="w-4 h-4 rounded-full border-2 border-gray-300 flex-shrink-0" />
                    )}
                    <span className={isActive ? 'text-primary-600 font-medium' : isCompleted ? 'text-gray-600' : 'text-gray-400'}>
                      {stepLabel}
                    </span>
                  </div>
                )
              })}
            </div>
          )}

        </div>
      </div>
    </div>
  )
}

