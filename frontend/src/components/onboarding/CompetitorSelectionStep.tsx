import { useAuthStore } from '@/store/authStore'
import type { OnboardingCompetitor } from '@/types'
import { Check, Loader2, RefreshCw, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import toast from 'react-hot-toast'
import OnboardingRegisterModal from './OnboardingRegisterModal'

interface CompetitorSelectionStepProps {
  sessionToken: string
  onSelectCompetitors: (competitorIds: string[], competitorData?: OnboardingCompetitor[]) => Promise<void>
  onReplaceCompetitor: (competitorId: string) => Promise<OnboardingCompetitor>
  onLoadMore: () => Promise<void>
  onCompleteOnboarding?: (userId: string) => Promise<void> // Callback to complete onboarding after registration
  isLoading?: boolean
}

export default function CompetitorSelectionStep({
  sessionToken,
  onSelectCompetitors,
  onReplaceCompetitor,
  onLoadMore,
  onCompleteOnboarding,
  isLoading = false
}: CompetitorSelectionStepProps) {
  const { isAuthenticated } = useAuthStore()
  const [competitors, setCompetitors] = useState<OnboardingCompetitor[]>([])
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [replacingId, setReplacingId] = useState<string | null>(null)
  const [showRegisterModal, setShowRegisterModal] = useState(false)
  const [isLoadingCompetitors, setIsLoadingCompetitors] = useState(false)
  const isLoadingRef = useRef(false)

  // Load competitors on mount
  useEffect(() => {
    if (sessionToken && !isLoadingRef.current) {
      loadCompetitors()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionToken])

  const loadCompetitors = async () => {
    // Prevent duplicate calls using ref (more reliable than state check)
    if (isLoadingRef.current) {
      return
    }
    
    isLoadingRef.current = true
    setIsLoadingCompetitors(true)
    
    try {
      const { ApiService } = await import('@/services/api')
      const response = await ApiService.suggestCompetitorsForOnboarding(sessionToken, 10)
      
      if (!response || !response.competitors) {
        throw new Error('Invalid response format from server')
      }
      
      // Validate and map competitors with fallbacks
      const mappedCompetitors = response.competitors
        .filter(c => c && c.company && c.company.name)  // Filter out invalid entries
        .map(c => {
          const company = c.company
          return {
            id: company.id || `temp-${Date.now()}-${Math.random()}`,  // Ensure ID is always present
            name: company.name || 'Unknown Company',
            website: company.website || '',
            logo_url: company.logo_url || null,
            category: company.category || null,
            description: company.description || null,
            ai_description: company.ai_description || company.description || undefined,  // Fallback to description
            similarity_score: c.similarity_score,
            common_categories: c.common_categories || [],
            reason: c.reason || ''
          }
        })
      
      setCompetitors(mappedCompetitors)
    } catch (err: any) {
      // Ignore network errors that might be from duplicate requests or cancelled requests
      const isNetworkError = !err.response && (err.code === 'ECONNABORTED' || err.message === 'Network Error' || err.name === 'AbortError' || err.code === 'ERR_CANCELED')
      
      if (!isNetworkError) {
        const errorMessage = err.response?.data?.detail || 
                            err.response?.data?.message || 
                            err.message || 
                            'Error loading competitors. Please try again.'
        toast.error(errorMessage)
      }
      
      // Only log non-network errors to avoid console spam
      if (!isNetworkError) {
        console.error('Error loading competitors:', err)
      }
    } finally {
      isLoadingRef.current = false
      setIsLoadingCompetitors(false)
    }
  }

  const handleToggleCompetitor = (competitorId: string) => {
    const newSelected = new Set(selectedIds)
    if (newSelected.has(competitorId)) {
      newSelected.delete(competitorId)
    } else {
      newSelected.add(competitorId)
    }
    setSelectedIds(newSelected)
  }

  const handleReplace = async (competitorId: string) => {
    setReplacingId(competitorId)
    try {
      const newCompetitor = await onReplaceCompetitor(competitorId)
      setCompetitors(prev => prev.map((c, idx) => {
        const cId = c.id || c.website || `temp-${idx}`
        return cId === competitorId ? newCompetitor : c
      }))
      // Remove from selection if was selected
      if (selectedIds.has(competitorId)) {
        const newSelected = new Set(selectedIds)
        newSelected.delete(competitorId)
        if (newCompetitor.id) {
          newSelected.add(newCompetitor.id)
        }
        setSelectedIds(newSelected)
      }
      toast.success('Competitor replaced')
    } catch (err: any) {
      toast.error(err.message || 'Error replacing competitor')
    } finally {
      setReplacingId(null)
    }
  }

  const handleContinue = async () => {
    if (selectedIds.size === 0) {
      toast.error('Select at least one competitor')
      return
    }

    // Check if user is authenticated
    if (!isAuthenticated) {
      setShowRegisterModal(true)
      return
    }

    // Continue with selection - pass full competitor data
    try {
      const selectedCompetitors = competitors.filter((c, idx) => {
        const competitorId = c.id || c.website || `temp-${idx}`
        return selectedIds.has(competitorId)
      })
      await onSelectCompetitors(Array.from(selectedIds), selectedCompetitors)
    } catch (err: any) {
      toast.error(err.message || 'Error saving selection')
    }
  }

  const handleRegisterSuccess = async (userId?: string) => {
    setShowRegisterModal(false)
    // After registration, save competitors and complete onboarding
    if (!userId) {
      toast.error('User ID is required')
      return
    }
    
    try {
      if (selectedIds.size > 0) {
        const selectedCompetitors = competitors.filter(c => {
          const competitorId = c.id || c.website || `temp-${competitors.indexOf(c)}`
          return selectedIds.has(competitorId)
        })
        await onSelectCompetitors(Array.from(selectedIds), selectedCompetitors)
      }
      
      // Complete onboarding and redirect to dashboard
      if (onCompleteOnboarding) {
        await onCompleteOnboarding(userId)
      }
    } catch (err: any) {
      toast.error(err.message || 'Error completing onboarding')
    }
  }

  return (
    <div className="max-w-6xl mx-auto">
      <div className="text-center mb-8">
        <h2 className="text-3xl font-bold text-gray-900 mb-2">
          Select competitors to monitor
        </h2>
        <p className="text-gray-600">
          Select companies you want to track. You can select from 1 to 50+ competitors.
        </p>
      </div>

      {isLoadingCompetitors ? (
        <div className="flex justify-center items-center py-12">
          <Loader2 className="w-8 h-8 text-primary-600 animate-spin" />
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
            {competitors.map((competitor, index) => {
              // Generate unique key: use id if available, otherwise use website or index
              const competitorKey = competitor.id || competitor.website || `competitor-${index}`
              const competitorId = competitor.id || competitor.website || `temp-${index}`
              
              return (
              <div
                key={competitorKey}
                className="bg-white rounded-lg border-2 p-4 hover:border-primary-300 transition-colors relative"
                style={{
                  borderColor: selectedIds.has(competitorId) ? '#3b82f6' : '#e5e7eb'
                }}
              >
                {/* Replace button */}
                {competitor.id && (
                  <button
                    onClick={() => handleReplace(competitor.id!)}
                    disabled={replacingId === competitor.id}
                    className="absolute top-2 right-2 p-1 text-gray-400 hover:text-red-600 transition-colors"
                    title="Replace competitor"
                  >
                    {replacingId === competitor.id ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <X className="w-4 h-4" />
                    )}
                  </button>
                )}

                {/* Checkbox */}
                <div className="flex items-start gap-3 mb-3">
                  <button
                    onClick={() => handleToggleCompetitor(competitorId)}
                    className={`mt-1 w-5 h-5 rounded border-2 flex items-center justify-center transition-colors ${
                      selectedIds.has(competitorId)
                        ? 'bg-primary-600 border-primary-600'
                        : 'border-gray-300'
                    }`}
                  >
                    {selectedIds.has(competitorId) && (
                      <Check className="w-3 h-3 text-white" />
                    )}
                  </button>

                  {/* Logo */}
                  {competitor.logo_url ? (
                    <img
                      src={competitor.logo_url}
                      alt={competitor.name}
                      className="w-12 h-12 rounded-lg object-contain"
                      onError={(e) => {
                        (e.target as HTMLImageElement).style.display = 'none'
                      }}
                    />
                  ) : (
                    <div className="w-12 h-12 rounded-lg bg-gray-100 flex items-center justify-center">
                      <span className="text-gray-400 text-xs font-medium">
                        {competitor.name.charAt(0).toUpperCase()}
                      </span>
                    </div>
                  )}
                </div>

                {/* Company info */}
                <div>
                  <h3 className="font-semibold text-gray-900 mb-1">{competitor.name}</h3>
                  {competitor.website && (
                    <a
                      href={competitor.website}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm text-primary-600 hover:text-primary-700 mb-2 block truncate"
                    >
                      {competitor.website}
                    </a>
                  )}
                  
                  {/* AI Description or Description */}
                  {(competitor.ai_description || competitor.description) && (
                    <p className="text-sm text-gray-600 line-clamp-3 mb-2">
                      {competitor.ai_description || competitor.description}
                    </p>
                  )}

                  {competitor.category && (
                    <span className="inline-block px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs">
                      {competitor.category}
                    </span>
                  )}
                </div>
              </div>
              )
            })}
          </div>

          <div className="flex items-center justify-between">
            <button
              onClick={onLoadMore}
              className="text-primary-600 hover:text-primary-700 flex items-center gap-2"
            >
              <RefreshCw className="w-4 h-4" />
              Show 10 more
            </button>

            <div className="flex items-center gap-4">
              <span className="text-sm text-gray-600">
                Selected: {selectedIds.size}
              </span>
              <button
                onClick={handleContinue}
                disabled={selectedIds.size === 0 || isLoading}
                className="bg-primary-600 text-white px-6 py-3 rounded-lg hover:bg-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-medium"
              >
                {isLoading ? 'Saving...' : 'Continue'}
              </button>
            </div>
          </div>
        </>
      )}

      {/* Register Modal */}
      {showRegisterModal && (
        <OnboardingRegisterModal
          isOpen={showRegisterModal}
          onClose={() => setShowRegisterModal(false)}
          onSuccess={handleRegisterSuccess}
        />
      )}
    </div>
  )
}

