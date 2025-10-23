import { useState } from 'react'
import { Company } from '../types'
import { ManualCompetitorSelector } from './ManualCompetitorSelector'

interface CompetitorSuggestionsProps {
  suggestions: Array<{
    company: Company
    similarity_score: number
    common_categories: string[]
    reason: string
  }>
  selectedCompetitors: string[]
  onToggleCompetitor: (companyId: string) => void
  onAddManual: (company: Company) => void
}

export default function CompetitorSuggestions({
  suggestions,
  selectedCompetitors,
  onToggleCompetitor,
  onAddManual
}: CompetitorSuggestionsProps) {
  const [isManualSelectorOpen, setIsManualSelectorOpen] = useState(false)

  const handleAddManual = (company: Company) => {
    onAddManual(company)
    setIsManualSelectorOpen(false)
  }
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900">
          🤖 AI Suggested Competitors
        </h3>
        <button
          onClick={() => setIsManualSelectorOpen(true)}
          className="text-sm text-primary-600 hover:text-primary-700 font-medium"
        >
          + Add manually
        </button>
      </div>
      
      <div className="space-y-3">
        {suggestions.map(suggestion => (
          <div
            key={suggestion.company.id}
            className={`border rounded-lg p-4 transition-colors ${
              selectedCompetitors.includes(suggestion.company.id)
                ? 'border-primary-200 bg-primary-50'
                : 'border-gray-200 hover:border-gray-300'
            }`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <input
                  type="checkbox"
                  checked={selectedCompetitors.includes(suggestion.company.id)}
                  onChange={() => onToggleCompetitor(suggestion.company.id)}
                  className="mr-3 h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                />
                
                {suggestion.company.logo_url && (
                  <img
                    src={suggestion.company.logo_url}
                    alt={suggestion.company.name}
                    className="w-10 h-10 rounded-lg mr-3 object-cover"
                  />
                )}
                
                <div>
                  <h4 className="font-medium text-gray-900">{suggestion.company.name}</h4>
                  <p className="text-sm text-gray-600">{suggestion.reason}</p>
                </div>
              </div>
              
              <div className="text-right">
                <div className="text-lg font-semibold text-primary-600">
                  {Math.round(suggestion.similarity_score * 100)}%
                </div>
                <div className="text-xs text-gray-500">similarity</div>
              </div>
            </div>
            
            {/* Common categories */}
            {suggestion.common_categories.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-1">
                {suggestion.common_categories.map(category => (
                  <span
                    key={category}
                    className="px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded-full"
                  >
                    {category.replace(/_/g, ' ')}
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
      
      {suggestions.length === 0 && (
        <div className="text-center py-8 text-gray-500">
          <p>No competitors found for this company.</p>
          <p className="text-sm mt-1">Try adding competitors manually.</p>
        </div>
      )}
      
      <ManualCompetitorSelector
        isOpen={isManualSelectorOpen}
        onClose={() => setIsManualSelectorOpen(false)}
        onAddCompetitor={handleAddManual}
        selectedCompanyIds={[]} // Основная компания не передается сюда
        excludedCompanyIds={selectedCompetitors}
      />
    </div>
  )
}
