import { useState } from 'react'
import { ApiService } from '../services/api'
import { Company } from '../types'

interface CompanySelectorProps {
  onSelect: (company: Company | null) => void
  selectedCompany?: Company | null
}

export default function CompanySelector({ onSelect, selectedCompany }: CompanySelectorProps) {
  const [searchTerm, setSearchTerm] = useState('')
  const [companies, setCompanies] = useState<Company[]>([])
  const [loading, setLoading] = useState(false)
  
  // Поиск компаний
  const searchCompanies = async (term: string) => {
    if (term.length < 2) {
      setCompanies([])
      return
    }
    
    setLoading(true)
    try {
      const response = await ApiService.searchCompanies(term, { limit: 10 })
      setCompanies(response.items)
    } catch (error) {
      console.error('Search failed:', error)
      setCompanies([])
    } finally {
      setLoading(false)
    }
  }
  
  return (
    <div className="space-y-4">
      {/* Search input */}
      <div className="relative">
        <input
          type="text"
          placeholder="Search for a company..."
          value={searchTerm}
          onChange={(e) => {
            setSearchTerm(e.target.value)
            searchCompanies(e.target.value)
          }}
          className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
        />
        {loading && (
          <div className="absolute right-3 top-3">
            <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-primary-600"></div>
          </div>
        )}
      </div>
      
      {/* Selected company */}
      {selectedCompany && (
        <div className="bg-primary-50 border border-primary-200 rounded-lg p-4">
          <div className="flex items-center">
            {selectedCompany.logo_url && (
              <img 
                src={selectedCompany.logo_url} 
                alt={selectedCompany.name} 
                className="w-12 h-12 rounded-lg mr-3 object-cover" 
              />
            )}
            <div className="flex-1">
              <h3 className="font-semibold text-primary-900">{selectedCompany.name}</h3>
              {/* <p className="text-sm text-primary-700">{selectedCompany.category}</p> */}
            </div>
            <button
              onClick={() => onSelect(null)}
              className="ml-auto text-primary-600 hover:text-primary-800 p-1"
            >
              ✕
            </button>
          </div>
        </div>
      )}
      
      {/* Search results */}
      {searchTerm && companies.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-lg shadow-lg max-h-60 overflow-y-auto">
          {companies.map(company => (
            <button
              key={company.id}
              onClick={() => {
                onSelect(company)
                setSearchTerm('')
                setCompanies([])
              }}
              className="w-full flex items-center p-3 hover:bg-gray-50 text-left border-b border-gray-100 last:border-b-0"
            >
              {company.logo_url && (
                <img 
                  src={company.logo_url} 
                  alt={company.name} 
                  className="w-8 h-8 rounded mr-3 object-cover" 
                />
              )}
              <div>
                <div className="font-medium text-gray-900">{company.name}</div>
                {/* <div className="text-sm text-gray-600">{company.category}</div> */}
              </div>
            </button>
          ))}
        </div>
      )}
      
      {/* No results message */}
      {searchTerm && !loading && companies.length === 0 && searchTerm.length >= 2 && (
        <div className="text-center py-4 text-gray-500">
          <p>No companies found for "{searchTerm}"</p>
          <p className="text-sm mt-1">Try a different search term</p>
        </div>
      )}
    </div>
  )
}
