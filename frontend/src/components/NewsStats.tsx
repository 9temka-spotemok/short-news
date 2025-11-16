import type { NewsStats } from '@/types'
import { Activity, Clock, FileText, TrendingUp } from 'lucide-react'

interface NewsStatsProps {
  stats: NewsStats
  className?: string
}

export default function NewsStats({ stats, className = '' }: NewsStatsProps) {
  const statsCards = [
    {
      icon: <FileText className="h-5 w-5" />,
      label: 'Total News',
      value: stats.total_count,
      color: 'blue',
      bgColor: 'bg-blue-50',
      textColor: 'text-blue-600',
      borderColor: 'border-blue-200'
    },
    {
      icon: <Clock className="h-5 w-5" />,
      label: 'Recent (24h)',
      value: stats.recent_count,
      color: 'green',
      bgColor: 'bg-green-50',
      textColor: 'text-green-600',
      borderColor: 'border-green-200'
    },
    // {
    //   icon: <Star className="h-5 w-5" />,
    //   label: 'High Priority',
    //   value: stats.high_priority_count,
    //   color: 'red',
    //   bgColor: 'bg-red-50',
    //   textColor: 'text-red-600',
    //   borderColor: 'border-red-200'
    // }
    // TODO: Add high priority stat
  ]

  return (
    <div className={`grid grid-cols-1 md:grid-cols-3 gap-4 ${className}`}>
      {statsCards.map((stat, index) => (
        <div
          key={index}
          className={`${stat.bgColor} ${stat.borderColor} border rounded-lg p-4`}
        >
          <div className="flex items-center justify-between">
            <div>
              <p className={`text-sm font-medium ${stat.textColor} mb-1`}>
                {stat.label}
              </p>
              <p className={`text-2xl font-bold ${stat.textColor}`}>
                {stat.value.toLocaleString()}
              </p>
            </div>
            <div className={`${stat.textColor}`}>
              {stat.icon}
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

// Category breakdown component
interface CategoryBreakdownProps {
  categoryCounts: Record<string, number>
  className?: string
}

export function CategoryBreakdown({ categoryCounts, className = '' }: CategoryBreakdownProps) {
  const sortedCategories = Object.entries(categoryCounts)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 5) // Top 5 categories

  return (
    <div className={`bg-white rounded-lg border border-gray-200 p-6 ${className}`}>
      <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
        <TrendingUp className="h-5 w-5 mr-2 text-primary-600" />
        Top Categories
      </h3>
      
      <div className="space-y-3">
        {sortedCategories.map(([category, count]) => {
          const percentage = (count / Object.values(categoryCounts).reduce((a, b) => a + b, 0)) * 100
          
          return (
            <div key={category} className="flex items-center justify-between">
              <div className="flex-1">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium text-gray-700 capitalize">
                    {category.replace('_', ' ')}
                  </span>
                  <span className="text-sm text-gray-500">
                    {count}
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-primary-600 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${Math.min(percentage, 100)}%` }}
                  ></div>
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// Source type breakdown component
interface SourceBreakdownProps {
  sourceTypeCounts: Record<string, number>
  sourceTypeDescriptions?: Array<{ value: string; description: string }>
  className?: string
}

// Mapping for source type display names (fallback)
const SOURCE_TYPE_LABELS: Record<string, string> = {
  blog: 'Blog',
  news_site: 'News Site',
  press_release: 'Press Release',
  twitter: 'Twitter/X',
  github: 'GitHub',
  reddit: 'Reddit',
}

// Helper function to format source type name
function formatSourceTypeName(
  source: string,
  sourceTypeDescriptions?: Array<{ value: string; description: string }>
): string {
  // First check if we have description from API
  if (sourceTypeDescriptions) {
    const sourceInfo = sourceTypeDescriptions.find(s => s.value === source)
    if (sourceInfo) {
      // Use short version from labels if available, otherwise use API description
      return SOURCE_TYPE_LABELS[source] || sourceInfo.description
    }
  }
  
  // Fallback to predefined labels
  if (SOURCE_TYPE_LABELS[source]) {
    return SOURCE_TYPE_LABELS[source]
  }
  
  // Final fallback: replace underscores with spaces and capitalize each word
  return source
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ')
}

export function SourceBreakdown({ 
  sourceTypeCounts, 
  sourceTypeDescriptions,
  className = '' 
}: SourceBreakdownProps) {
  const sortedSources = Object.entries(sourceTypeCounts)
    .sort(([, a], [, b]) => b - a)

  const totalCount = Object.values(sourceTypeCounts).reduce((a, b) => a + b, 0)

  return (
    <div className={`bg-white rounded-lg border border-gray-200 p-6 ${className}`}>
      <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
        <Activity className="h-5 w-5 mr-2 text-primary-600" />
        Sources Distribution
      </h3>
      
      {sortedSources.length === 0 ? (
        <p className="text-sm text-gray-500 text-center py-4">No sources available</p>
      ) : (
        <div className="space-y-3">
          {sortedSources.map(([source, count]) => {
            const percentage = totalCount > 0 ? (count / totalCount) * 100 : 0
            
            return (
              <div key={source} className="flex items-center justify-between">
                <div className="flex-1">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-gray-700">
                      {formatSourceTypeName(source, sourceTypeDescriptions)}
                    </span>
                    <span className="text-sm text-gray-500">
                      {count}
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-primary-600 h-2 rounded-full transition-all duration-300"
                      style={{ width: `${Math.min(percentage, 100)}%` }}
                    ></div>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
