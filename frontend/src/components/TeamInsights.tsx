import { Award, Calendar, Heart, MessageSquare, Users } from 'lucide-react'
import React from 'react'

interface TeamInsightsProps {
  company: {
    id: string
    name: string
    description?: string
  }
  metrics: {
    community_event?: number
    strategic_announcement?: number
    research_paper?: number
  }
  totalNews: number
  activityScore: number
}

export const TeamInsights: React.FC<TeamInsightsProps> = ({
  metrics,
  totalNews,
  activityScore
}) => {
  const teamMetrics = [
    {
      label: 'Community',
      value: metrics.community_event || 0,
      icon: Users,
      color: 'text-blue-600',
      bgColor: 'bg-blue-50',
      description: 'Community events and activities'
    },
    {
      label: 'Strategic Decisions',
      value: metrics.strategic_announcement || 0,
      icon: Award,
      color: 'text-purple-600',
      bgColor: 'bg-purple-50',
      description: 'Important management decisions'
    },
    {
      label: 'Research',
      value: metrics.research_paper || 0,
      icon: MessageSquare,
      color: 'text-green-600',
      bgColor: 'bg-green-50',
      description: 'Team scientific publications'
    }
  ]

  const totalTeamActivity = teamMetrics.reduce((sum, metric) => sum + metric.value, 0)
  const teamEngagementScore = totalNews > 0 ? (totalTeamActivity / totalNews) * 100 : 0

  // Determine company culture based on activity
  const getCompanyCulture = () => {
    if (teamEngagementScore > 25) return { type: 'High engagement', color: 'text-green-600', bg: 'bg-green-50' }
    if (teamEngagementScore > 10) return { type: 'Medium engagement', color: 'text-yellow-600', bg: 'bg-yellow-50' }
    return { type: 'Low engagement', color: 'text-red-600', bg: 'bg-red-50' }
  }

  const culture = getCompanyCulture()

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-green-100 rounded-lg">
            <Users className="w-6 h-6 text-green-600" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Team & Culture</h3>
            <p className="text-sm text-gray-500">Analysis of team and corporate culture</p>
          </div>
        </div>
        <div className="text-right">
          <div className="text-2xl font-bold text-gray-900">{totalTeamActivity}</div>
          <div className="text-sm text-gray-500">team activity</div>
        </div>
      </div>

      {/* Main metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        {teamMetrics.map((metric, index) => {
          const IconComponent = metric.icon
          return (
            <div key={index} className={`${metric.bgColor} rounded-lg p-4 border border-gray-100`}>
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center space-x-2">
                  <IconComponent className={`w-5 h-5 ${metric.color}`} />
                  <span className="text-sm font-medium text-gray-700">{metric.label}</span>
                </div>
                <span className={`text-lg font-bold ${metric.color}`}>{metric.value}</span>
              </div>
              <p className="text-xs text-gray-600">{metric.description}</p>
            </div>
          )
        })}
      </div>

      {/* Team engagement indicator */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-gray-700">Team Engagement Level</span>
          <span className="text-sm font-bold text-gray-900">{teamEngagementScore.toFixed(1)}%</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div 
            className={`h-2 rounded-full transition-all duration-300 ${
              teamEngagementScore > 25 ? 'bg-green-500' : 
              teamEngagementScore > 10 ? 'bg-yellow-500' : 'bg-red-500'
            }`}
            style={{ width: `${Math.min(teamEngagementScore, 100)}%` }}
          ></div>
        </div>
        <p className="text-xs text-gray-500 mt-1">
          {teamEngagementScore > 25 ? 'High team engagement' : 
           teamEngagementScore > 10 ? 'Medium team engagement' : 'Low team engagement'}
        </p>
      </div>

      {/* Culture analysis */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Corporate culture */}
        <div className="space-y-4">
          <h4 className="font-medium text-gray-900 flex items-center">
            <Heart className="w-4 h-4 mr-2 text-gray-500" />
            Corporate Culture
          </h4>
          <div className={`${culture.bg} rounded-lg p-4 border border-gray-100`}>
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-700">Culture type:</span>
              <span className={`text-sm font-bold ${culture.color}`}>{culture.type}</span>
            </div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-700">Total activity:</span>
              <span className="text-sm font-bold text-gray-900">{activityScore.toFixed(1)}/10</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-700">Team activity:</span>
              <span className="text-sm font-bold text-gray-900">{totalTeamActivity}</span>
            </div>
          </div>
        </div>

        {/* Team initiatives */}
        <div className="space-y-4">
          <h4 className="font-medium text-gray-900 flex items-center">
            <Calendar className="w-4 h-4 mr-2 text-gray-500" />
            Team Initiatives
          </h4>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-600">Community events:</span>
              <span className="font-medium text-gray-900">{metrics.community_event || 0}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Strategic decisions:</span>
              <span className="font-medium text-gray-900">{metrics.strategic_announcement || 0}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Research work:</span>
              <span className="font-medium text-gray-900">{metrics.research_paper || 0}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Culture recommendations */}
      <div className="mt-6 pt-6 border-t border-gray-200">
        <h4 className="font-medium text-gray-900 mb-3">Team Development Recommendations</h4>
        <div className="space-y-2">
          {teamEngagementScore < 10 && (
            <div className="flex items-start space-x-2 text-sm">
              <div className="w-2 h-2 bg-red-500 rounded-full mt-2 flex-shrink-0"></div>
              <p className="text-gray-600">
                <strong>Low activity:</strong> It's recommended to increase community events and improve internal communications.
              </p>
            </div>
          )}
          {teamEngagementScore >= 10 && teamEngagementScore < 25 && (
            <div className="flex items-start space-x-2 text-sm">
              <div className="w-2 h-2 bg-yellow-500 rounded-full mt-2 flex-shrink-0"></div>
              <p className="text-gray-600">
                <strong>Medium activity:</strong> The team shows good results. You can add more research initiatives.
              </p>
            </div>
          )}
          {teamEngagementScore >= 25 && (
            <div className="flex items-start space-x-2 text-sm">
              <div className="w-2 h-2 bg-green-500 rounded-full mt-2 flex-shrink-0"></div>
              <p className="text-gray-600">
                <strong>High activity:</strong> Excellent corporate culture! The team actively participates in company development.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
