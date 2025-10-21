import CompanyMultiSelect from '@/components/CompanyMultiSelect'
import { ApiService } from '@/services/api'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Edit3, Plus, Trash2, X } from 'lucide-react'
import { useState } from 'react'
import toast from 'react-hot-toast'

interface TrackedCompaniesManagerProps {
  className?: string
}

export default function TrackedCompaniesManager({ className = '' }: TrackedCompaniesManagerProps) {
  const [isManaging, setIsManaging] = useState(false)
  const queryClient = useQueryClient()

  // Get user preferences
  const { data: preferences, isLoading: preferencesLoading } = useQuery({
    queryKey: ['user-preferences'],
    queryFn: ApiService.getUserPreferences,
    staleTime: 1000 * 60 * 5, // 5 minutes
  })

  // Get tracked companies details
  const { data: trackedCompanies = [], isLoading: companiesLoading } = useQuery({
    queryKey: ['tracked-companies', preferences?.subscribed_companies],
    queryFn: () => ApiService.getCompaniesByIds(preferences?.subscribed_companies || []),
    enabled: !!preferences?.subscribed_companies?.length,
    staleTime: 1000 * 60 * 5, // 5 minutes
  })

  // Update preferences mutation
  const updatePreferencesMutation = useMutation({
    mutationFn: ApiService.updateUserPreferences,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['user-preferences'] })
      queryClient.invalidateQueries({ queryKey: ['tracked-companies'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard-data'] })
      toast.success('Preferences updated successfully')
      setIsManaging(false)
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to update preferences')
    },
  })

  const handleUpdatePreferences = (selectedCompanies: string[]) => {
    updatePreferencesMutation.mutate({
      subscribed_companies: selectedCompanies,
    })
  }

  const handleUnsubscribe = (companyId: string) => {
    console.log('Unsubscribing from company:', companyId)
    
    // Простое локальное удаление, как в CompanyMultiSelect
    const updatedCompanies = preferences?.subscribed_companies?.filter(id => id !== companyId) || []
    handleUpdatePreferences(updatedCompanies)
  }

  const isLoading = preferencesLoading || companiesLoading
  const isUpdating = updatePreferencesMutation.isPending

  if (isLoading) {
    return (
      <div className={`card p-6 ${className}`}>
        <div className="flex items-center justify-center py-8">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
          <p className="ml-3 text-gray-600">Loading tracked companies...</p>
        </div>
      </div>
    )
  }

  return (
    <div className={`card p-6 ${className}`}>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center">
          <h3 className="text-lg font-semibold text-gray-900">
            Tracked Companies
          </h3>
          <span className="ml-2 px-2 py-1 text-xs font-medium bg-primary-100 text-primary-700 rounded-full">
            {trackedCompanies.length}
          </span>
        </div>
        <button
          onClick={() => setIsManaging(!isManaging)}
          disabled={isUpdating}
          className="btn btn-outline btn-sm flex items-center gap-2"
        >
          {isManaging ? (
            <>
              <X className="h-4 w-4" />
              Done
            </>
          ) : (
            <>
              <Edit3 className="h-4 w-4" />
              Manage
            </>
          )}
        </button>
      </div>

      {isManaging ? (
        <div className="space-y-4">
          <p className="text-sm text-gray-600">
            Select companies you want to track for personalized news and analytics.
          </p>
          <CompanyMultiSelect
            selectedCompanies={preferences?.subscribed_companies || []}
            onSelectionChange={handleUpdatePreferences}
            placeholder="Search and select companies to track..."
          />
          {isUpdating && (
            <div className="flex items-center justify-center py-2">
              <div className="inline-block animate-spin rounded-full h-4 w-4 border-b-2 border-primary-600"></div>
              <p className="ml-2 text-sm text-gray-600">Updating preferences...</p>
            </div>
          )}
        </div>
      ) : (
        <div className="space-y-3">
          {trackedCompanies.length > 0 ? (
            trackedCompanies.map((company) => (
              <div
                key={company.id}
                className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
              >
                <div className="flex items-center space-x-3">
                  {company.logo_url ? (
                    <img
                      src={company.logo_url}
                      alt={`${company.name} logo`}
                      className="w-8 h-8 rounded-full object-cover"
                      onError={(e) => {
                        e.currentTarget.style.display = 'none'
                      }}
                    />
                  ) : (
                    <div className="w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center">
                      <span className="text-sm font-medium text-primary-700">
                        {company.name.charAt(0).toUpperCase()}
                      </span>
                    </div>
                  )}
                  <div>
                    <p className="text-sm font-medium text-gray-900">{company.name}</p>
                    {company.website && (
                      <p className="text-xs text-gray-500">{company.website}</p>
                    )}
                  </div>
                </div>
                <button
                  onClick={() => handleUnsubscribe(company.id)}
                  disabled={isUpdating}
                  className="p-1 text-red-600 hover:text-red-700 hover:bg-red-50 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  title="Remove from tracked companies"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            ))
          ) : (
            <div className="text-center py-8">
              <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Plus className="h-8 w-8 text-gray-400" />
              </div>
              <p className="text-gray-600 mb-2">No companies tracked yet</p>
              <p className="text-sm text-gray-500 mb-4">
                Start tracking companies to get personalized news and analytics
              </p>
              <button
                onClick={() => setIsManaging(true)}
                className="btn btn-primary btn-sm"
              >
                Add Companies
              </button>
            </div>
          )}
        </div>
      )}

      {trackedCompanies.length > 0 && !isManaging && (
        <div className="mt-4 pt-4 border-t border-gray-200">
          <p className="text-xs text-gray-500">
            You're tracking {trackedCompanies.length} companies. 
            News and analytics will be personalized based on these selections.
          </p>
        </div>
      )}
    </div>
  )
}
