import { useState } from 'react'
import { Company } from '../types'

interface ThemeAnalysisProps {
  themesData: {
    themes: Record<string, {
      total_mentions: number
      by_company: Record<string, number>
      example_titles: string[]
    }>
    unique_themes: Record<string, string[]>
  }
  companies: Company[]
}

export default function ThemeAnalysis({ themesData, companies }: ThemeAnalysisProps) {
  const [selectedTheme, setSelectedTheme] = useState<string | null>(null)
  
  // Топ-10 тем по упоминаниям
  const topThemes = Object.entries(themesData.themes)
    .sort(([,a], [,b]) => b.total_mentions - a.total_mentions)
    .slice(0, 10)
  
  return (
    <div className="space-y-6">
      {/* Common themes */}
      <div>
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Common Themes</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {topThemes.map(([theme, data]) => (
            <div
              key={theme}
              onClick={() => setSelectedTheme(theme)}
              className={`p-4 border rounded-lg cursor-pointer transition-colors ${
                selectedTheme === theme ? 'border-primary-200 bg-primary-50' : 'border-gray-200 hover:border-gray-300'
              }`}
            >
              <div className="flex justify-between items-center mb-2">
                <h4 className="font-medium text-gray-900 capitalize">{theme}</h4>
                <span className="text-sm text-gray-600">{data.total_mentions} mentions</span>
              </div>
              
              {/* Distribution by company */}
              <div className="space-y-1">
                {Object.entries(data.by_company).map(([companyId, count]) => {
                  const company = companies.find(c => c.id === companyId)
                  if (!company) return null
                  
                  const percentage = Math.round((count / data.total_mentions) * 100)
                  return (
                    <div key={companyId} className="flex justify-between text-sm">
                      <span className="text-gray-600">{company.name}</span>
                      <span className="text-gray-900">{count} ({percentage}%)</span>
                    </div>
                  )
                })}
              </div>
            </div>
          ))}
        </div>
      </div>
      
      {/* Unique themes */}
      <div>
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Unique Themes</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Object.entries(themesData.unique_themes).map(([companyId, themes]) => {
            const company = companies.find(c => c.id === companyId)
            if (!company || themes.length === 0) return null
            
            return (
              <div key={companyId} className="bg-white border border-gray-200 rounded-lg p-4">
                <h4 className="font-medium text-gray-900 mb-3">{company.name}</h4>
                <div className="flex flex-wrap gap-1">
                  {themes.slice(0, 8).map(theme => (
                    <span
                      key={theme}
                      className="px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded-full"
                    >
                      {theme}
                    </span>
                  ))}
                  {themes.length > 8 && (
                    <span className="px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded-full">
                      +{themes.length - 8} more
                    </span>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </div>
      
      {/* Theme details modal */}
      {selectedTheme && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-2xl w-full mx-4 max-h-96 overflow-y-auto">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold text-gray-900 capitalize">{selectedTheme}</h3>
              <button
                onClick={() => setSelectedTheme(null)}
                className="text-gray-400 hover:text-gray-600"
              >
                ✕
              </button>
            </div>
            
            <div className="space-y-4">
              <div>
                <h4 className="font-medium text-gray-900 mb-2">Example Titles</h4>
                <ul className="space-y-1">
                  {themesData.themes[selectedTheme].example_titles.map((title, index) => (
                    <li key={index} className="text-sm text-gray-600">• {title}</li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
