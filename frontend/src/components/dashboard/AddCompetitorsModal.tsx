import { ApiService } from '@/services/api'
import type { CompetitorInfo } from '@/types'
import { Check, ExternalLink, Globe, Loader2, UserPlus, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'

interface AddCompetitorsModalProps {
  isOpen: boolean
  onClose: () => void
  competitors: CompetitorInfo[]
  subscribedCompanyIds: string[] // Уже отслеживаемые компании
  onSuccess?: () => void | Promise<void>
}

export default function AddCompetitorsModal({
  isOpen,
  onClose,
  competitors,
  subscribedCompanyIds,
  onSuccess
}: AddCompetitorsModalProps) {
  const [selectedCompanyIds, setSelectedCompanyIds] = useState<Set<string>>(new Set())
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Инициализировать selectedCompanyIds при открытии модалки
  useEffect(() => {
    if (isOpen) {
      // Начальное состояние: все уже отслеживаемые компании выбраны
      const initialSelected = new Set(subscribedCompanyIds)
      console.log('AddCompetitorsModal - Initializing:', {
        isOpen,
        subscribedCompanyIds,
        competitorsCount: competitors.length,
        competitors: competitors.map(c => ({ id: c.company.id, name: c.company.name }))
      })
      setSelectedCompanyIds(initialSelected)
      setError(null)
    } else {
      // Сбрасываем при закрытии
      setSelectedCompanyIds(new Set())
      setError(null)
    }
  }, [isOpen, subscribedCompanyIds])

  const toggleCompetitor = (companyId: string) => {
    // Не позволяем снимать выбор с уже отслеживаемых компаний
    if (subscribedCompanyIds.includes(companyId)) {
      console.log('AddCompetitorsModal - Cannot toggle already tracked company:', companyId)
      return
    }

    setSelectedCompanyIds(prev => {
      const next = new Set(prev)
      const wasSelected = next.has(companyId)
      if (wasSelected) {
        next.delete(companyId)
        console.log('AddCompetitorsModal - Deselected company:', companyId, 'New set:', Array.from(next))
      } else {
        next.add(companyId)
        console.log('AddCompetitorsModal - Selected company:', companyId, 'New set:', Array.from(next))
      }
      return next
    })
  }

  const handleConfirm = async () => {
    console.log('AddCompetitorsModal - handleConfirm called')
    if (selectedCompanyIds.size === 0) {
      setError('Please select at least one competitor to add')
      return
    }

    // Фильтруем только новые компании (не те, что уже отслеживаются)
    const newCompanyIds = Array.from(selectedCompanyIds).filter(
      id => !subscribedCompanyIds.includes(id)
    )

    console.log('AddCompetitorsModal - Selected IDs:', Array.from(selectedCompanyIds))
    console.log('AddCompetitorsModal - Subscribed IDs:', subscribedCompanyIds)
    console.log('AddCompetitorsModal - New IDs to add:', newCompanyIds)

    if (newCompanyIds.length === 0) {
      toast.success('All selected competitors are already being tracked')
      onClose()
      return
    }

    setIsLoading(true)
    setError(null)

    try {
      console.log('AddCompetitorsModal - Starting to add competitors:', {
        selectedCount: selectedCompanyIds.size,
        newCount: newCompanyIds.length,
        newCompanyIds,
        subscribedCompanyIds
      })

      // Выполняем все запросы параллельно
      const results = await Promise.allSettled(
        newCompanyIds.map(async (companyId, index) => {
          console.log(`AddCompetitorsModal - [${index + 1}/${newCompanyIds.length}] Adding company:`, companyId)
          try {
            const result = await ApiService.subscribeToCompany(companyId)
            console.log(`AddCompetitorsModal - [${index + 1}/${newCompanyIds.length}] Successfully added:`, companyId, result)
            return { companyId, result }
          } catch (error: any) {
            console.error(`AddCompetitorsModal - [${index + 1}/${newCompanyIds.length}] Failed to add:`, companyId, {
              error,
              message: error?.message,
              response: error?.response?.data,
              status: error?.response?.status
            })
            // Пробрасываем ошибку с информацией о companyId
            throw { companyId, error, errorMessage: error?.response?.data?.detail || error?.message || 'Unknown error' }
          }
        })
      )

      const successful: Array<{ companyId: string; result: any }> = []
      const failed: Array<{ companyId: string; error: any; errorMessage: string }> = []

      results.forEach((result, index) => {
        const companyId = newCompanyIds[index]
        if (result.status === 'fulfilled') {
          const value = result.value
          console.log('AddCompetitorsModal - Successfully added:', companyId, value)
          successful.push(value)
        } else {
          const reason = result.reason || { companyId, error: 'Unknown error' }
          const errorMessage = reason.errorMessage || reason.error?.response?.data?.detail || reason.error?.message || 'Unknown error'
          console.error('AddCompetitorsModal - Failed to add:', companyId, {
            reason,
            errorMessage,
            fullError: reason.error
          })
          failed.push({ 
            companyId: reason.companyId || companyId, 
            error: reason.error,
            errorMessage 
          })
        }
      })

      console.log('AddCompetitorsModal - Final results:', { 
        successful: successful.length, 
        failed: failed.length,
        successfulIds: successful,
        failedDetails: failed
      })

      if (successful.length > 0) {
        const successfulIds = successful.map(s => s.companyId).join(', ')
        toast.success(
          `Successfully added ${successful.length} competitor${successful.length !== 1 ? 's' : ''} to tracked companies${successful.length <= 3 ? `: ${successfulIds}` : ''}`
        )
        // Обновляем preferences и закрываем модалку
        console.log('AddCompetitorsModal - Calling onSuccess with', successful.length, 'successful additions')
        if (onSuccess) {
          try {
            const result = onSuccess()
            if (result instanceof Promise) {
              await result
            }
            console.log('AddCompetitorsModal - onSuccess completed')
          } catch (error) {
            console.error('AddCompetitorsModal - onSuccess error:', error)
          }
        }
      }

      if (failed.length > 0) {
        const failedIds = failed.map(f => f.companyId).join(', ')
        const errorMessages = failed.map(f => f.errorMessage).filter(Boolean).join('; ')
        
        console.error('AddCompetitorsModal - Failed competitors details:', failed)
        toast.error(`Failed to add ${failed.length} competitor${failed.length !== 1 ? 's' : ''}: ${failedIds}`)
        setError(`Failed to add ${failed.length} competitor${failed.length !== 1 ? 's' : ''}: ${failedIds}${errorMessages ? `. Errors: ${errorMessages}` : ''}`)
      }

      // Закрываем модалку только если хотя бы одна компания была успешно добавлена
      // или если все провалились (чтобы пользователь мог попробовать снова)
      if (successful.length > 0 && failed.length === 0) {
        // Все успешно - закрываем сразу
        onClose()
      } else if (successful.length > 0 && failed.length > 0) {
        // Частичный успех - закрываем через задержку
        setTimeout(() => {
          onClose()
        }, 2000)
      }
      // Если все провалились, не закрываем модалку - пользователь может попробовать снова
    } catch (err: any) {
      console.error('AddCompetitorsModal - Unexpected error:', err)
      setError(err?.response?.data?.detail || 'Failed to add competitors to tracked companies')
      toast.error('Failed to add competitors')
    } finally {
      setIsLoading(false)
    }
  }

  const handleClose = () => {
    if (!isLoading) {
      setSelectedCompanyIds(new Set())
      setError(null)
      onClose()
    }
  }

  if (!isOpen) return null

  // Подсчет статистики
  const alreadyTrackedCount = competitors.filter(c => 
    subscribedCompanyIds.includes(c.company.id)
  ).length
  const newToAddCount = Array.from(selectedCompanyIds).filter(
    id => !subscribedCompanyIds.includes(id)
  ).length

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg max-w-2xl w-full shadow-xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-start justify-between p-6 border-b border-gray-200">
          <div className="flex items-start gap-3">
            <div className="flex-shrink-0 w-10 h-10 rounded-full bg-primary-100 flex items-center justify-center">
              <UserPlus className="h-5 w-5 text-primary-600" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900">Add Competitors to Tracked Companies</h3>
              <p className="text-sm text-gray-500 mt-1">
                Select competitors to add to your tracked companies list
              </p>
            </div>
          </div>
          <button
            onClick={handleClose}
            disabled={isLoading}
            className="text-gray-400 hover:text-gray-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Stats */}
        {competitors.length > 0 && (
          <div className="px-6 py-3 bg-gray-50 border-b border-gray-200 flex items-center gap-4 text-sm">
            <span className="text-gray-600">
              {alreadyTrackedCount > 0 && (
                <span className="text-gray-500">
                  {alreadyTrackedCount} already tracked
                </span>
              )}
            </span>
            {newToAddCount > 0 && (
              <span className="text-primary-600 font-medium">
                {newToAddCount} new to add
              </span>
            )}
          </div>
        )}

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-800">{error}</p>
            </div>
          )}

          {competitors.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-sm text-gray-500">No competitors available</p>
            </div>
          ) : (
            <div className="space-y-3">
              {competitors.map((competitor, idx) => {
                const companyId = competitor.company.id
                const isAlreadyTracked = subscribedCompanyIds.includes(companyId)
                const isSelected = selectedCompanyIds.has(companyId)

                return (
                  <div
                    key={idx}
                    className={`border rounded-lg p-4 transition-all ${
                      isAlreadyTracked
                        ? 'bg-gray-50 border-gray-200 opacity-75'
                        : isSelected
                        ? 'border-primary-300 bg-primary-50'
                        : 'border-gray-200 hover:border-gray-300 hover:shadow-sm'
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      {/* Checkbox */}
                      <div className="flex-shrink-0 mt-1">
                        <label
                          className={`flex items-center justify-center w-5 h-5 border-2 rounded cursor-pointer transition-colors ${
                            isAlreadyTracked
                              ? 'bg-gray-200 border-gray-300 cursor-not-allowed'
                              : isSelected
                              ? 'bg-primary-600 border-primary-600'
                              : 'border-gray-300 hover:border-primary-400'
                          }`}
                        >
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => toggleCompetitor(companyId)}
                            disabled={isAlreadyTracked || isLoading}
                            className="sr-only"
                          />
                          {isSelected && (
                            <Check className="h-3 w-3 text-white" />
                          )}
                        </label>
                      </div>

                      {/* Logo */}
                      <div className="flex-shrink-0">
                        {competitor.company.logo_url ? (
                          <img
                            src={competitor.company.logo_url}
                            alt={competitor.company.name}
                            className="w-12 h-12 rounded-lg object-cover"
                            onError={(e) => {
                              e.currentTarget.style.display = 'none'
                            }}
                          />
                        ) : (
                          <div className="w-12 h-12 rounded-lg bg-gray-200 flex items-center justify-center">
                            <Globe className="h-6 w-6 text-gray-400" />
                          </div>
                        )}
                      </div>

                      {/* Company Info */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between gap-2 mb-1">
                          <div className="flex-1 min-w-0">
                            <h4 className="text-sm font-semibold text-gray-900">
                              {competitor.company.name}
                              {isAlreadyTracked && (
                                <span className="ml-2 text-xs text-gray-500 font-normal">
                                  (already tracked)
                                </span>
                              )}
                            </h4>
                            {competitor.company.website && (
                              <a
                                href={competitor.company.website}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-xs text-primary-600 hover:text-primary-700 break-all inline-flex items-center gap-1 mt-1"
                                onClick={(e) => e.stopPropagation()}
                              >
                                {competitor.company.website}
                                <ExternalLink className="h-3 w-3" />
                              </a>
                            )}
                          </div>
                          <div className="flex-shrink-0 text-right">
                            <span className="text-xs font-medium text-primary-600">
                              {Math.round(competitor.similarity_score * 100)}% match
                            </span>
                          </div>
                        </div>

                        {/* Common Categories */}
                        {competitor.common_categories && competitor.common_categories.length > 0 && (
                          <div className="flex flex-wrap gap-1 mt-2">
                            {competitor.common_categories.slice(0, 3).map((cat, catIdx) => (
                              <span
                                key={catIdx}
                                className="inline-block text-xs bg-gray-100 text-gray-700 px-2 py-0.5 rounded-full"
                              >
                                {cat}
                              </span>
                            ))}
                            {competitor.common_categories.length > 3 && (
                              <span className="text-xs text-gray-500">
                                +{competitor.common_categories.length - 3} more
                              </span>
                            )}
                          </div>
                        )}

                        {/* Reason */}
                        {competitor.reason && (
                          <p className="text-xs text-gray-600 mt-2 italic">
                            {competitor.reason}
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-6 border-t border-gray-200 bg-gray-50">
          <button
            onClick={handleClose}
            disabled={isLoading}
            className="btn btn-outline btn-sm disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            disabled={isLoading || newToAddCount === 0}
            className="btn btn-sm bg-primary-600 hover:bg-primary-700 text-white disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {isLoading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Adding...
              </>
            ) : (
              <>
                <UserPlus className="h-4 w-4" />
                Add {newToAddCount > 0 ? `${newToAddCount} ` : ''}to Tracked
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}

