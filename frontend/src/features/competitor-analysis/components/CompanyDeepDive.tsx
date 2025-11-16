import { Gauge, PieChart, Smile } from 'lucide-react'

import BrandPreview from '@/components/BrandPreview'
import { BusinessIntelligence } from '@/components/BusinessIntelligence'
import { InnovationMetrics } from '@/components/InnovationMetrics'
import { MarketPosition } from '@/components/MarketPosition'
import { TeamInsights } from '@/components/TeamInsights'
import type { Company } from '@/types'

import { formatLabel } from '../utils/formatters'

type CompanyDeepDiveProps = {
  company: Company
  analysisData: any
  suggestedCompetitors: any[]
}

const sentimentColors: Record<string, string> = {
  positive: 'bg-green-500',
  neutral: 'bg-gray-400',
  negative: 'bg-red-500',
  mixed: 'bg-purple-500'
}

export const CompanyDeepDive = ({ company, analysisData, suggestedCompetitors }: CompanyDeepDiveProps) => {
  if (!analysisData?.metrics) {
    return null
  }

  const companyId = company.id
  const metrics = analysisData.metrics
  const topicDistribution: Record<string, number> = metrics.topic_distribution?.[companyId] ?? {}
  const sentimentDistribution: Record<string, number> = metrics.sentiment_distribution?.[companyId] ?? {}
  const avgPriority = metrics.avg_priority?.[companyId]
  const newsVolume = metrics.news_volume?.[companyId] ?? 0
  const activityScore = metrics.activity_score?.[companyId] ?? 0
  const totalNews = Object.values(metrics.news_volume ?? {}).reduce((sum: number, value: unknown) => sum + Number(value), 0)

  const sortedTopics = Object.entries(topicDistribution)
    .sort(([, a], [, b]) => Number(b) - Number(a))
    .slice(0, 5)

  const sentimentEntries = Object.entries(sentimentDistribution)
  const sentimentTotal = sentimentEntries.reduce((sum, [, value]) => sum + Number(value), 0)

  return (
    <div className="space-y-6">
      <BrandPreview
        company={company}
        stats={{
          total_news: newsVolume,
          categories_breakdown: Object.entries(metrics.category_distribution?.[companyId] ?? {}).map(([category, count]) => ({
            category,
            count: Number(count)
          })),
          activity_score: activityScore,
          avg_priority: avgPriority ?? 0.5
        }}
      />

      <BusinessIntelligence
        company={company}
        metrics={metrics.category_distribution?.[companyId] ?? {}}
        activityScore={activityScore}
        competitorCount={suggestedCompetitors.length}
      />

      <InnovationMetrics
        company={company}
        metrics={metrics.category_distribution?.[companyId] ?? {}}
        totalNews={newsVolume}
      />

      <TeamInsights
        company={company}
        metrics={metrics.category_distribution?.[companyId] ?? {}}
        totalNews={newsVolume}
        activityScore={activityScore}
      />

      <MarketPosition
        company={company}
        metrics={{
          news_volume: newsVolume,
          activity_score: activityScore,
          category_distribution: metrics.category_distribution?.[companyId] ?? {}
        }}
        competitors={suggestedCompetitors}
        totalNews={totalNews}
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center space-x-3 mb-4">
            <div className="p-2 bg-indigo-100 rounded-lg">
              <PieChart className="w-5 h-5 text-indigo-600" />
            </div>
            <div>
              <h4 className="text-sm font-semibold text-gray-900">Top Topics</h4>
              <p className="text-xs text-gray-500">Themes driving conversation</p>
            </div>
          </div>
          <div className="space-y-3">
            {sortedTopics.map(([topic, count]) => {
              const total = sortedTopics.reduce((sum, [, value]) => sum + Number(value), 0) || 1
              const percentage = Math.round((Number(count) / total) * 100)
              return (
                <div key={topic}>
                  <div className="flex justify-between text-xs text-gray-600 mb-1">
                    <span>{formatLabel(topic)}</span>
                    <span className="text-gray-900 font-medium">
                      {Number(count)} ({percentage}%)
                    </span>
                  </div>
                  <div className="h-2 w-full bg-gray-100 rounded-full">
                    <div className="h-2 bg-indigo-500 rounded-full" style={{ width: `${percentage}%` }} />
                  </div>
                </div>
              )
            })}
            {!sortedTopics.length && <p className="text-xs text-gray-500">Run analysis to populate topic distribution.</p>}
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center space-x-3 mb-4">
            <div className="p-2 bg-rose-100 rounded-lg">
              <Smile className="w-5 h-5 text-rose-600" />
            </div>
            <div>
              <h4 className="text-sm font-semibold text-gray-900">Sentiment Overview</h4>
              <p className="text-xs text-gray-500">Tone of recent coverage</p>
            </div>
          </div>
          <div className="space-y-3">
            {sentimentEntries.map(([sentiment, count]) => {
              const percentage = sentimentTotal ? Math.round((Number(count) / sentimentTotal) * 100) : 0
              const barColor = sentimentColors[sentiment] || 'bg-gray-400'
              return (
                <div key={sentiment}>
                  <div className="flex justify-between text-xs text-gray-600 mb-1">
                    <span>{formatLabel(sentiment)}</span>
                    <span className="text-gray-900 font-medium">
                      {Number(count)} ({percentage}%)
                    </span>
                  </div>
                  <div className="h-2 w-full bg-gray-100 rounded-full">
                    <div className={`h-2 rounded-full ${barColor}`} style={{ width: `${percentage}%` }} />
                  </div>
                </div>
              )
            })}
            {!sentimentEntries.length && <p className="text-xs text-gray-500">No sentiment data available yet.</p>}
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center space-x-3 mb-4">
            <div className="p-2 bg-emerald-100 rounded-lg">
              <Gauge className="w-5 h-5 text-emerald-600" />
            </div>
            <div>
              <h4 className="text-sm font-semibold text-gray-900">Average Priority</h4>
              <p className="text-xs text-gray-500">Weighted priority score</p>
            </div>
          </div>
          <div className="space-y-3">
            <div className="flex items-end justify-between">
              <div>
                <p className="text-xs text-gray-500 uppercase">Priority Score</p>
                <p className="text-2xl font-semibold text-gray-900">{avgPriority !== undefined && avgPriority !== null ? Number(avgPriority).toFixed(2) : '0.00'}</p>
              </div>
              <span className="text-sm font-medium text-emerald-600">
                {avgPriority !== undefined && avgPriority !== null
                  ? `${Math.round(Number(avgPriority) * 100)}%`
                  : 'n/a'}
              </span>
            </div>
            <div className="h-2 w-full bg-gray-100 rounded-full overflow-hidden">
              <div
                className="h-2 bg-emerald-500"
                style={{ width: `${avgPriority !== undefined && avgPriority !== null ? Math.round(Number(avgPriority) * 100) : 0}%` }}
              />
            </div>
            <p className="text-xs text-gray-500">
              Higher score indicates more impactful or time-sensitive updates.
            </p>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold text-gray-900">News Volume Comparison</h3>
        </div>
        <div className="space-y-3">
          {(analysisData.companies ?? []).map((item: Company, index: number) => {
            const volume = metrics.news_volume?.[item.id] ?? 0
            const maxVolume = Math.max(...Object.values(metrics.news_volume ?? {}).map(value => Number(value)), 0)
            const percentage = maxVolume > 0 ? (volume / maxVolume) * 100 : 0
            const colors = ['bg-blue-500', 'bg-green-500', 'bg-purple-500', 'bg-orange-500', 'bg-pink-500']

            return (
              <div key={item.id}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium text-gray-700">{item.name}</span>
                  <span className="text-sm text-gray-600">{volume} news</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-3">
                  <div
                    className={`h-3 rounded-full ${colors[index % colors.length]}`}
                    style={{ width: `${percentage}%` }}
                  />
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}











