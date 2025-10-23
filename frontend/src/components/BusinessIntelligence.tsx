import { Building, DollarSign, Handshake, Target, TrendingUp } from 'lucide-react'
import React from 'react'

interface BusinessIntelligenceProps {
  company: {
    id: string
    name: string
    category?: string
    website?: string
    description?: string
  }
  metrics: {
    funding_news?: number
    partnership?: number
    acquisition?: number
    strategic_announcement?: number
    integration?: number
  }
  activityScore: number
  competitorCount: number
}

export const BusinessIntelligence: React.FC<BusinessIntelligenceProps> = ({
  company,
  metrics,
  activityScore,
  competitorCount
}) => {
  const businessMetrics = [
    {
      label: 'Funding News',
      value: metrics.funding_news || 0,
      icon: DollarSign,
      color: 'text-green-600',
      bgColor: 'bg-green-50',
      description: 'Mentions of funding, investments, rounds'
    },
    {
      label: 'Partnerships',
      value: metrics.partnership || 0,
      icon: Handshake,
      color: 'text-blue-600',
      bgColor: 'bg-blue-50',
      description: 'Strategic partnerships and collaborations'
    },
    {
      label: 'Acquisitions',
      value: metrics.acquisition || 0,
      icon: Building,
      color: 'text-purple-600',
      bgColor: 'bg-purple-50',
      description: 'M&A activity and acquisitions'
    },
    {
      label: 'Strategic Announcements',
      value: metrics.strategic_announcement || 0,
      icon: Target,
      color: 'text-orange-600',
      bgColor: 'bg-orange-50',
      description: 'Important strategic decisions'
    },
    {
      label: 'Integrations',
      value: metrics.integration || 0,
      icon: TrendingUp,
      color: 'text-indigo-600',
      bgColor: 'bg-indigo-50',
      description: 'Technical integrations and APIs'
    }
  ]

  const totalBusinessActivity = businessMetrics.reduce((sum, metric) => sum + metric.value, 0)

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-blue-100 rounded-lg">
            <TrendingUp className="w-6 h-6 text-blue-600" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Business Intelligence</h3>
            <p className="text-sm text-gray-500">Analysis of business activity and growth</p>
          </div>
        </div>
        <div className="text-right">
          <div className="text-2xl font-bold text-gray-900">{totalBusinessActivity}</div>
          <div className="text-sm text-gray-500">total activity</div>
        </div>
      </div>

      {/* Main metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
        {businessMetrics.map((metric, index) => {
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

      {/* Additional information */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Company information */}
        <div className="space-y-4">
          <h4 className="font-medium text-gray-900 flex items-center">
            <Building className="w-4 h-4 mr-2 text-gray-500" />
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
              <span className="text-gray-600">Activity:</span>
              <span className="font-medium text-gray-900">{activityScore.toFixed(1)}/10</span>
            </div>
          </div>
        </div>

        {/* Market position */}
        <div className="space-y-4">
          <h4 className="font-medium text-gray-900 flex items-center">
            <Target className="w-4 h-4 mr-2 text-gray-500" />
            Market Position
          </h4>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-600">Competitors:</span>
              <span className="font-medium text-gray-900">{competitorCount}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Total activity:</span>
              <span className="font-medium text-gray-900">{totalBusinessActivity}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Status:</span>
              <span className={`font-medium ${totalBusinessActivity > 10 ? 'text-green-600' : totalBusinessActivity > 5 ? 'text-yellow-600' : 'text-red-600'}`}>
                {totalBusinessActivity > 10 ? 'High activity' : totalBusinessActivity > 5 ? 'Medium activity' : 'Low activity'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Company description */}
      {company.description && (
        <div className="mt-6 pt-6 border-t border-gray-200">
          <h4 className="font-medium text-gray-900 mb-2">Company Description</h4>
          <p className="text-sm text-gray-600 leading-relaxed">{company.description}</p>
        </div>
      )}
    </div>
  )
}
