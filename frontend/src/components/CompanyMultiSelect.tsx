import api from '@/services/api'
import { Check, ChevronDown, Search, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'

interface Company {
  id: string
  name: string
  logo_url?: string
  category?: string
}

interface CompanyMultiSelectProps {
  selectedCompanies: string[]
  onSelectionChange: (companies: string[]) => void
  placeholder?: string
}

export default function CompanyMultiSelect({
  selectedCompanies,
  onSelectionChange,
  placeholder = 'Select companies...'
}: CompanyMultiSelectProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [companies, setCompanies] = useState<Company[]>([])
  const [loading, setLoading] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  // Fetch companies from API
  useEffect(() => {
    fetchCompanies()
  }, [])

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [])

  const fetchCompanies = async () => {
    try {
      setLoading(true)
      const response = await api.get('/companies/', {
        params: { limit: 200 }
      })
      setCompanies(response.data.items)
    } catch (error) {
      console.error('Failed to fetch companies:', error)
    } finally {
      setLoading(false)
    }
  }

  const filteredCompanies = companies.filter((company) =>
    company.name.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const toggleCompany = (companyId: string) => {
    if (selectedCompanies.includes(companyId)) {
      onSelectionChange(selectedCompanies.filter((id) => id !== companyId))
    } else {
      onSelectionChange([...selectedCompanies, companyId])
    }
  }

  const clearSelection = () => {
    onSelectionChange([])
  }

  const getSelectedCompaniesNames = () => {
    return companies
      .filter((company) => selectedCompanies.includes(company.id))
      .map((company) => company.name)
  }

  const selectedNames = getSelectedCompaniesNames()

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full input pl-3 pr-10 text-left flex items-center justify-between"
      >
        <span className="block truncate">
          {selectedNames.length > 0 ? (
            <span className="flex flex-wrap gap-1">
              {selectedNames.slice(0, 2).map((name, index) => (
                <span
                  key={index}
                  className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-primary-100 text-primary-700"
                >
                  {name}
                </span>
              ))}
              {selectedNames.length > 2 && (
                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-700">
                  +{selectedNames.length - 2}
                </span>
              )}
            </span>
          ) : (
            <span className="text-gray-500">{placeholder}</span>
          )}
        </span>
        <div className="flex items-center space-x-1">
          {selectedNames.length > 0 && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation()
                clearSelection()
              }}
              className="p-1 hover:bg-gray-100 rounded"
            >
              <X className="h-4 w-4 text-gray-400" />
            </button>
          )}
          <ChevronDown
            className={`h-5 w-5 text-gray-400 transition-transform ${
              isOpen ? 'transform rotate-180' : ''
            }`}
          />
        </div>
      </button>

      {isOpen && (
        <div className="absolute z-10 mt-1 w-full bg-white shadow-lg rounded-md border border-gray-200 max-h-60 overflow-auto">
          {/* Search Input */}
          <div className="sticky top-0 bg-white border-b border-gray-200 p-2">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                type="text"
                className="w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent text-sm"
                placeholder="Search companies..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onClick={(e) => e.stopPropagation()}
              />
            </div>
          </div>

          {/* Companies List */}
          <div className="py-1">
            {loading ? (
              <div className="px-3 py-2 text-sm text-gray-500">Loading...</div>
            ) : filteredCompanies.length === 0 ? (
              <div className="px-3 py-2 text-sm text-gray-500">No companies found</div>
            ) : (
              filteredCompanies.map((company) => {
                const isSelected = selectedCompanies.includes(company.id)
                return (
                  <button
                    key={company.id}
                    type="button"
                    onClick={() => toggleCompany(company.id)}
                    className={`w-full text-left px-3 py-2 text-sm flex items-center space-x-2 hover:bg-gray-100 ${
                      isSelected ? 'bg-primary-50' : ''
                    }`}
                  >
                    <div className="flex items-center justify-center w-4 h-4">
                      <div
                        className={`w-4 h-4 rounded border ${
                          isSelected
                            ? 'bg-primary-600 border-primary-600'
                            : 'border-gray-300'
                        } flex items-center justify-center`}
                      >
                        {isSelected && <Check className="h-3 w-3 text-white" />}
                      </div>
                    </div>
                    <span className={isSelected ? 'font-medium text-primary-700' : 'text-gray-900'}>
                      {company.name}
                    </span>
                    {company.category && (
                      <span className="text-xs text-gray-500 ml-auto">{company.category}</span>
                    )}
                  </button>
                )
              })
            )}
          </div>
        </div>
      )}
    </div>
  )
}



