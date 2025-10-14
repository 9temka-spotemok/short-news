import { BarChart3, Calendar, TrendingUp } from 'lucide-react'
import { useState } from 'react'
import CompanyMultiSelect from '../components/CompanyMultiSelect'
import api from '../services/api'
import { CompetitorComparison } from '../types'

export default function CompetitorAnalysisPage() {
  const [selectedCompanies, setSelectedCompanies] = useState<string[]>([])
  const [dateFrom, setDateFrom] = useState(() => {
    const date = new Date()
    date.setDate(date.getDate() - 30)
    return date.toISOString().split('T')[0]
  })
  const [dateTo, setDateTo] = useState(() => new Date().toISOString().split('T')[0])
  const [comparison, setComparison] = useState<CompetitorComparison | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const runComparison = async () => {
    if (selectedCompanies.length < 2) {
      setError('Please select at least 2 companies to compare')
      return
    }

    try {
      setIsLoading(true)
      setError(null)

      const response = await api.post('/competitors/compare', {
        company_ids: selectedCompanies,
        date_from: dateFrom,
        date_to: dateTo
      })

      setComparison(response.data)
    } catch (err: any) {
      console.error('Error comparing companies:', err)
      setError(err.response?.data?.detail || 'Failed to compare companies')
    } finally {
      setIsLoading(false)
    }
  }

  const getCompanyColor = (index: number) => {
    const colors = [
      'bg-blue-500',
      'bg-green-500',
      'bg-purple-500',
      'bg-orange-500',
      'bg-pink-500'
    ]
    return colors[index % colors.length]
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto py-8 px-4">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900 flex items-center">
            <BarChart3 className="w-8 h-8 mr-3" />
            Competitor Analysis
          </h1>
          <p className="text-gray-600 mt-2">
            Compare companies by news volume, categories, and activity
          </p>
        </div>

        {/* Selection Panel */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Select Companies & Date Range
          </h2>

          <div className="space-y-4">
            {/* Company Selection */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Companies (select 2-5)
              </label>
              <CompanyMultiSelect
                selectedCompanies={selectedCompanies}
                onSelectionChange={setSelectedCompanies}
              />
            </div>

            {/* Date Range */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  <Calendar className="w-4 h-4 inline mr-1" />
                  From
                </label>
                <input
                  type="date"
                  value={dateFrom}
                  onChange={(e) => setDateFrom(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  <Calendar className="w-4 h-4 inline mr-1" />
                  To
                </label>
                <input
                  type="date"
                  value={dateTo}
                  onChange={(e) => setDateTo(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
            </div>

            {/* Error Message */}
            {error && (
              <div className="p-3 bg-red-50 text-red-700 rounded-lg border border-red-200 text-sm">
                {error}
              </div>
            )}

            {/* Compare Button */}
            <button
              onClick={runComparison}
              disabled={isLoading || selectedCompanies.length < 2}
              className="w-full bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
            >
              <TrendingUp className="w-5 h-5 mr-2" />
              {isLoading ? 'Analyzing...' : 'Compare Companies'}
            </button>
          </div>
        </div>

        {/* Results */}
        {comparison && (
          <div className="space-y-6">
            {/* News Volume Comparison */}
            <div className="bg-white rounded-lg shadow-md p-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">
                News Volume
              </h2>
              <div className="space-y-3">
                {comparison.companies.map((company, index) => {
                  const volume = comparison.metrics.news_volume[company.id] || 0
                  const maxVolume = Math.max(...Object.values(comparison.metrics.news_volume))
                  const percentage = maxVolume > 0 ? (volume / maxVolume) * 100 : 0

                  return (
                    <div key={company.id}>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm font-medium text-gray-700">
                          {company.name}
                        </span>
                        <span className="text-sm text-gray-600">{volume} news</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-3">
                        <div
                          className={`h-3 rounded-full ${getCompanyColor(index)}`}
                          style={{ width: `${percentage}%` }}
                        />
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Activity Score */}
            <div className="bg-white rounded-lg shadow-md p-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">
                Activity Score
              </h2>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                {comparison.companies.map((company) => {
                  const score = comparison.metrics.activity_score[company.id] || 0

                  return (
                    <div
                      key={company.id}
                      className="p-4 border border-gray-200 rounded-lg"
                    >
                      <div className="flex items-center mb-2">
                        {company.logo_url && (
                          <img
                            src={company.logo_url}
                            alt={company.name}
                            className="w-8 h-8 rounded mr-2"
                          />
                        )}
                        <span className="text-sm font-medium text-gray-700">
                          {company.name}
                        </span>
                      </div>
                      <div className="text-3xl font-bold text-blue-600">
                        {score.toFixed(1)}
                      </div>
                      <div className="text-xs text-gray-500 mt-1">
                        out of 100
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Category Distribution */}
            <div className="bg-white rounded-lg shadow-md p-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">
                Category Distribution
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {comparison.companies.map((company) => {
                  const distribution = comparison.metrics.category_distribution[company.id] || {}
                  const total = Object.values(distribution).reduce((sum: number, count) => sum + (count as number), 0)

                  return (
                    <div key={company.id} className="border border-gray-200 rounded-lg p-4">
                      <h3 className="font-medium text-gray-900 mb-3">{company.name}</h3>
                      <div className="space-y-2">
                        {Object.entries(distribution)
                          .sort(([, a], [, b]) => (b as number) - (a as number))
                          .slice(0, 5)
                          .map(([category, count]) => (
                            <div key={category} className="flex items-center justify-between text-sm">
                              <span className="text-gray-600 capitalize">
                                {category.replace(/_/g, ' ')}
                              </span>
                              <span className="font-medium text-gray-900">
                                {count as number} ({total > 0 ? Math.round(((count as number) / total) * 100) : 0}%)
                              </span>
                            </div>
                          ))}
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Comparison Table */}
            <div className="bg-white rounded-lg shadow-md p-6 overflow-x-auto">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">
                Comparison Table
              </h2>
              <table className="w-full">
                <thead>
                  <tr className="border-b">
                    <th className="text-left py-3 px-4 text-sm font-semibold text-gray-700">
                      Company
                    </th>
                    <th className="text-center py-3 px-4 text-sm font-semibold text-gray-700">
                      News Volume
                    </th>
                    <th className="text-center py-3 px-4 text-sm font-semibold text-gray-700">
                      Activity Score
                    </th>
                    <th className="text-center py-3 px-4 text-sm font-semibold text-gray-700">
                      Categories
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {comparison.companies.map((company) => {
                    const volume = comparison.metrics.news_volume[company.id] || 0
                    const score = comparison.metrics.activity_score[company.id] || 0
                    const categories = Object.keys(comparison.metrics.category_distribution[company.id] || {}).length

                    return (
                      <tr key={company.id} className="border-b hover:bg-gray-50">
                        <td className="py-3 px-4">
                          <div className="flex items-center">
                            {company.logo_url && (
                              <img
                                src={company.logo_url}
                                alt={company.name}
                                className="w-6 h-6 rounded mr-2"
                              />
                            )}
                            <span className="font-medium text-gray-900">
                              {company.name}
                            </span>
                          </div>
                        </td>
                        <td className="text-center py-3 px-4 text-gray-700">
                          {volume}
                        </td>
                        <td className="text-center py-3 px-4">
                          <span className="text-blue-600 font-semibold">
                            {score.toFixed(1)}
                          </span>
                        </td>
                        <td className="text-center py-3 px-4 text-gray-700">
                          {categories}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

