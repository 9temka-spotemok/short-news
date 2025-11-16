import { Award, BarChart3, Globe, Target, TrendingUp, Users } from 'lucide-react'
import React from 'react'

type SuggestedCompetitor = {
  company?: {
    id: string
    name: string
  }
  similarity_score?: number
  id?: string
  name?: string
  [key: string]: any
}

type NormalizedCompetitor = {
  id: string
  name: string
  similarity_score: number
}

interface MarketPositionProps {
  company: {
    id: string
    name: string
    category?: string
    website?: string
  }
  metrics: {
    news_volume: number
    activity_score: number
    category_distribution: Record<string, number>
  }
  competitors: Array<SuggestedCompetitor | NormalizedCompetitor>
  totalNews: number
}

export const MarketPosition: React.FC<MarketPositionProps> = ({
  company,
  metrics,
  competitors,
  totalNews
}) => {
  const normalizedCompetitors: NormalizedCompetitor[] = competitors.map((competitor, index) => {
    if ('company' in competitor && competitor.company) {
      return {
        id: competitor.company.id ?? `suggestion-${index}`,
        name: competitor.company.name ?? `Suggested competitor #${index + 1}`,
        similarity_score: typeof competitor.similarity_score === 'number' ? competitor.similarity_score : 0
      }
    }

    return {
      id: competitor.id ?? `competitor-${index}`,
      name: competitor.name ?? `Competitor #${index + 1}`,
      similarity_score: typeof competitor.similarity_score === 'number' ? competitor.similarity_score : 0
    }
  })

  // Market position analysis
  const marketAnalysis = {
    totalCompetitors: normalizedCompetitors.length,
    avgSimilarity: normalizedCompetitors.length > 0
      ? normalizedCompetitors.reduce((sum, c) => sum + c.similarity_score, 0) / normalizedCompetitors.length
      : 0,
    marketShare: totalNews > 0 ? (metrics.news_volume / totalNews) * 100 : 0,
    activityLevel: metrics.activity_score
  }

  // Determine market position
  const getMarketPosition = () => {
    if (marketAnalysis.activityLevel > 7 && marketAnalysis.marketShare > 20) {
      return { type: 'Market Leader', color: 'text-green-600', bg: 'bg-green-50', icon: Award }
    }
    if (marketAnalysis.activityLevel > 5 && marketAnalysis.marketShare > 10) {
      return { type: 'Strong Player', color: 'text-blue-600', bg: 'bg-blue-50', icon: TrendingUp }
    }
    if (marketAnalysis.activityLevel > 3) {
      return { type: 'Emerging', color: 'text-yellow-600', bg: 'bg-yellow-50', icon: BarChart3 }
    }
    return { type: 'Newcomer', color: 'text-gray-600', bg: 'bg-gray-50', icon: Target }
  }

  const position = getMarketPosition()
  const PositionIcon = position.icon

  // Top categories by activity
  const topCategoryEntries = Object.entries(metrics.category_distribution)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 5)
  const topCategories = topCategoryEntries.map(([category, count]) => ({ category, count }))
  const maxCategoryCount = topCategories.reduce((max, item) => Math.max(max, item.count), 0)

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-orange-100 rounded-lg">
            <Target className="w-6 h-6 text-orange-600" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Market Position</h3>
            <p className="text-sm text-gray-500">Analysis of market position and competitors</p>
          </div>
        </div>
        <div className="text-right">
          <div className="text-2xl font-bold text-gray-900">{marketAnalysis.totalCompetitors}</div>
          <div className="text-sm text-gray-500">competitors</div>
        </div>
      </div>

      {/* Market position */}
      <div className={`${position.bg} rounded-lg p-4 border border-gray-100 mb-6`}>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center space-x-2">
            <PositionIcon className={`w-5 h-5 ${position.color}`} />
            <span className="font-medium text-gray-900">Market Position</span>
          </div>
          <span className={`text-lg font-bold ${position.color}`}>{position.type}</span>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <span className="text-gray-600">Activity:</span>
            <div className="font-bold text-gray-900">{marketAnalysis.activityLevel.toFixed(1)}/10</div>
          </div>
          <div>
            <span className="text-gray-600">News share:</span>
            <div className="font-bold text-gray-900">{marketAnalysis.marketShare.toFixed(1)}%</div>
          </div>
          <div>
            <span className="text-gray-600">Competitors:</span>
            <div className="font-bold text-gray-900">{marketAnalysis.totalCompetitors}</div>
          </div>
          <div>
            <span className="text-gray-600">Avg similarity:</span>
            <div className="font-bold text-gray-900">{(marketAnalysis.avgSimilarity * 100).toFixed(1)}%</div>
          </div>
        </div>
      </div>

      {/* Main metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        {/* Category and website */}
        <div className="space-y-4">
          <h4 className="font-medium text-gray-900 flex items-center">
            <Globe className="w-4 h-4 mr-2 text-gray-500" />
            Company Information
          </h4>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-600">Category:</span>
              <span className="font-medium text-gray-900">{company.category || 'Not specified'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Website:</span>
              <span className="font-medium text-gray-900">
                {company.website ? (
                  <a href={company.website} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                    {company.website}
                  </a>
                ) : 'Not specified'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">News volume:</span>
              <span className="font-medium text-gray-900">{metrics.news_volume}</span>
            </div>
          </div>
        </div>

        {/* Top categories */}
        <div className="space-y-4">
          <h4 className="font-medium text-gray-900 flex items-center">
            <BarChart3 className="w-4 h-4 mr-2 text-gray-500" />
            Top Categories
          </h4>
          <div className="space-y-2">
            {topCategories.map((item, index) => {
              const normalizedKey = item.category?.length ? item.category : `unknown-${index}`
              return (
                <div key={normalizedKey} className="flex items-center justify-between text-sm">
                <span className="text-gray-600 capitalize">{item.category.replace(/_/g, ' ')}</span>
                <div className="flex items-center space-x-2">
                  <div className="w-16 bg-gray-200 rounded-full h-2">
                    <div 
                      className="bg-blue-500 h-2 rounded-full"
                      style={{ width: `${maxCategoryCount ? (item.count / maxCategoryCount) * 100 : 0}%` }}
                    ></div>
                  </div>
                  <span className="font-medium text-gray-900 w-8 text-right">{item.count}</span>
                </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>

      {/* Competitors */}
      <div className="space-y-4">
        <h4 className="font-medium text-gray-900 flex items-center">
          <Users className="w-4 h-4 mr-2 text-gray-500" />
          Main Competitors
        </h4>
        {normalizedCompetitors.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {normalizedCompetitors.slice(0, 6).map((competitor, index) => (
              <div key={competitor.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg border border-gray-100">
                <div className="flex items-center space-x-3">
                  <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                    <span className="text-xs font-bold text-blue-600">{index + 1}</span>
                  </div>
                  <div>
                    <div className="font-medium text-gray-900 text-sm">{competitor.name}</div>
                    <div className="text-xs text-gray-500">Similarity: {(competitor.similarity_score * 100).toFixed(1)}%</div>
                  </div>
                </div>
                <div className={`px-2 py-1 rounded-full text-xs font-medium ${
                  competitor.similarity_score > 0.7 ? 'bg-red-100 text-red-600' :
                  competitor.similarity_score > 0.5 ? 'bg-yellow-100 text-yellow-600' :
                  'bg-green-100 text-green-600'
                }`}>
                  {competitor.similarity_score > 0.7 ? 'High' :
                   competitor.similarity_score > 0.5 ? 'Medium' : 'Low'}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-gray-500">
            <Users className="w-12 h-12 mx-auto mb-2 text-gray-300" />
            <p>No competitors found</p>
          </div>
        )}
      </div>

      {/* Recommendations */}
      <div className="mt-6 pt-6 border-t border-gray-200">
        <h4 className="font-medium text-gray-900 mb-3">Development Recommendations</h4>
        <div className="space-y-2">
          {marketAnalysis.activityLevel < 5 && (
            <div className="flex items-start space-x-2 text-sm">
              <div className="w-2 h-2 bg-yellow-500 rounded-full mt-2 flex-shrink-0"></div>
              <p className="text-gray-600">
                <strong>Low activity:</strong> It's recommended to increase public activity and communications.
              </p>
            </div>
          )}
          {marketAnalysis.totalCompetitors > 10 && (
            <div className="flex items-start space-x-2 text-sm">
              <div className="w-2 h-2 bg-blue-500 rounded-full mt-2 flex-shrink-0"></div>
              <p className="text-gray-600">
                <strong>High competition:</strong> It's necessary to stand out with unique offerings and innovations.
              </p>
            </div>
          )}
          {marketAnalysis.marketShare < 10 && (
            <div className="flex items-start space-x-2 text-sm">
              <div className="w-2 h-2 bg-purple-500 rounded-full mt-2 flex-shrink-0"></div>
              <p className="text-gray-600">
                <strong>Small market share:</strong> Focus on niche solutions and target audience.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
