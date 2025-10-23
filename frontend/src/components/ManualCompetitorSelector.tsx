import { Building2, Plus, Search, X } from 'lucide-react'
import React, { useEffect, useState } from 'react'
import { ApiService } from '../services/api'
import { Company } from '../types'

interface ManualCompetitorSelectorProps {
  isOpen: boolean
  onClose: () => void
  onAddCompetitor: (company: Company) => void
  selectedCompanyIds: string[]
  excludedCompanyIds: string[] // Компании, которые уже выбраны как конкуренты
}

export const ManualCompetitorSelector: React.FC<ManualCompetitorSelectorProps> = ({
  isOpen,
  onClose,
  onAddCompetitor,
  selectedCompanyIds,
  excludedCompanyIds
}) => {
  const [searchQuery, setSearchQuery] = useState('')
  const [companies, setCompanies] = useState<Company[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Загружаем компании при открытии модального окна
  useEffect(() => {
    if (isOpen) {
      loadCompanies()
    }
  }, [isOpen])

  const loadCompanies = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await ApiService.getCompanies(
        searchQuery || undefined,
        100,
        0
      )
      setCompanies(response.items || [])
    } catch (err) {
      setError('Failed to load companies')
      console.error('Error loading companies:', err)
    } finally {
      setLoading(false)
    }
  }

  // Перезагружаем компании при изменении поискового запроса
  useEffect(() => {
    if (isOpen) {
      const timeoutId = setTimeout(() => {
        loadCompanies()
      }, 300) // Debounce search
      return () => clearTimeout(timeoutId)
    }
  }, [searchQuery, isOpen])

  // Фильтруем компании (исключаем уже выбранные и основную компанию)
  const availableCompanies = companies.filter(company => 
    !excludedCompanyIds.includes(company.id) && 
    !selectedCompanyIds.includes(company.id)
  )

  const handleAddCompetitor = (company: Company) => {
    onAddCompetitor(company)
    onClose()
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">Add Competitor Manually</h2>
            <p className="text-sm text-gray-600 mt-1">Search and select companies to add as competitors</p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Search */}
        <div className="p-6 border-b border-gray-200">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
            <input
              type="text"
              placeholder="Search companies..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {error && (
            <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-lg border border-red-200 text-sm">
              {error}
            </div>
          )}

          {loading ? (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              <span className="ml-2 text-gray-600">Loading companies...</span>
            </div>
          ) : availableCompanies.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <Building2 className="w-12 h-12 mx-auto mb-2 text-gray-300" />
              <p>No companies found</p>
              <p className="text-sm mt-1">
                {searchQuery ? 'Try a different search term' : 'No companies available to add'}
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {availableCompanies.map(company => (
                <div
                  key={company.id}
                  className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:border-gray-300 transition-colors"
                >
                  <div className="flex items-center space-x-3">
                    {company.logo_url ? (
                      <img
                        src={company.logo_url}
                        alt={company.name}
                        className="w-10 h-10 rounded-lg object-cover"
                      />
                    ) : (
                      <div className="w-10 h-10 bg-gray-100 rounded-lg flex items-center justify-center">
                        <Building2 className="w-5 h-5 text-gray-400" />
                      </div>
                    )}
                    
                    <div>
                      <h3 className="font-medium text-gray-900">{company.name}</h3>
                      <p className="text-sm text-gray-600">
                        {company.category && (
                          <span className="capitalize">{company.category.replace('_', ' ')}</span>
                        )}
                        {company.website && (
                          <span className="ml-2 text-blue-600">{company.website}</span>
                        )}
                      </p>
                    </div>
                  </div>
                  
                  <button
                    onClick={() => handleAddCompetitor(company)}
                    className="flex items-center space-x-2 px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    <Plus className="w-4 h-4" />
                    <span>Add</span>
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-gray-200">
          <div className="flex justify-end">
            <button
              onClick={onClose}
              className="px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
