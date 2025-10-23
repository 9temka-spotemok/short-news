import { BookOpen, Code, Cpu, GitBranch, Shield, Twitter, Zap } from 'lucide-react'
import React from 'react'

interface InnovationMetricsProps {
  company: {
    id: string
    name: string
    github_org?: string
    twitter_handle?: string
  }
  metrics: {
    technical_update?: number
    api_update?: number
    research_paper?: number
    model_release?: number
    performance_improvement?: number
    security_update?: number
  }
  totalNews: number
}

export const InnovationMetrics: React.FC<InnovationMetricsProps> = ({
  company,
  metrics,
  totalNews
}) => {
  const innovationMetrics = [
    {
      label: 'Technical Updates',
      value: metrics.technical_update || 0,
      icon: Code,
      color: 'text-blue-600',
      bgColor: 'bg-blue-50',
      description: 'Technology and infrastructure updates'
    },
    {
      label: 'API Updates',
      value: metrics.api_update || 0,
      icon: Cpu,
      color: 'text-green-600',
      bgColor: 'bg-green-50',
      description: 'API and interface changes'
    },
    {
      label: 'Research',
      value: metrics.research_paper || 0,
      icon: BookOpen,
      color: 'text-purple-600',
      bgColor: 'bg-purple-50',
      description: 'Scientific publications and research'
    },
    {
      label: 'Model Releases',
      value: metrics.model_release || 0,
      icon: Zap,
      color: 'text-yellow-600',
      bgColor: 'bg-yellow-50',
      description: 'New models and algorithms'
    },
    {
      label: 'Performance Improvements',
      value: metrics.performance_improvement || 0,
      icon: Zap,
      color: 'text-orange-600',
      bgColor: 'bg-orange-50',
      description: 'Optimization and improvements'
    },
    {
      label: 'Security Updates',
      value: metrics.security_update || 0,
      icon: Shield,
      color: 'text-red-600',
      bgColor: 'bg-red-50',
      description: 'Security patches and protection'
    }
  ]

  const totalInnovationActivity = innovationMetrics.reduce((sum, metric) => sum + metric.value, 0)
  const innovationScore = totalNews > 0 ? (totalInnovationActivity / totalNews) * 100 : 0

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-purple-100 rounded-lg">
            <Code className="w-6 h-6 text-purple-600" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Innovation & Technology</h3>
            <p className="text-sm text-gray-500">Analysis of technological innovations</p>
          </div>
        </div>
        <div className="text-right">
          <div className="text-2xl font-bold text-gray-900">{totalInnovationActivity}</div>
          <div className="text-sm text-gray-500">technical activity</div>
        </div>
      </div>

      {/* Main metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
        {innovationMetrics.map((metric, index) => {
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

      {/* Innovation indicator */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-gray-700">Innovation Index</span>
          <span className="text-sm font-bold text-gray-900">{innovationScore.toFixed(1)}%</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div 
            className={`h-2 rounded-full transition-all duration-300 ${
              innovationScore > 30 ? 'bg-green-500' : 
              innovationScore > 15 ? 'bg-yellow-500' : 'bg-red-500'
            }`}
            style={{ width: `${Math.min(innovationScore, 100)}%` }}
          ></div>
        </div>
        <p className="text-xs text-gray-500 mt-1">
          {innovationScore > 30 ? 'High innovation level' : 
           innovationScore > 15 ? 'Medium innovation level' : 'Low innovation level'}
        </p>
      </div>

      {/* Social networks and development */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* GitHub activity */}
        <div className="space-y-4">
          <h4 className="font-medium text-gray-900 flex items-center">
            <GitBranch className="w-4 h-4 mr-2 text-gray-500" />
            Development
          </h4>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-600">GitHub organization:</span>
              <span className="font-medium text-gray-900">
                {company.github_org ? (
                  <a 
                    href={`https://github.com/${company.github_org}`} 
                    target="_blank" 
                    rel="noopener noreferrer" 
                    className="text-blue-600 hover:underline"
                  >
                    @{company.github_org}
                  </a>
                ) : 'Not specified'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Status:</span>
              <span className={`font-medium ${company.github_org ? 'text-green-600' : 'text-gray-400'}`}>
                {company.github_org ? 'Active' : 'Not specified'}
              </span>
            </div>
          </div>
        </div>

        {/* Twitter activity */}
        <div className="space-y-4">
          <h4 className="font-medium text-gray-900 flex items-center">
            <Twitter className="w-4 h-4 mr-2 text-gray-500" />
            Social Networks
          </h4>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-600">Twitter:</span>
              <span className="font-medium text-gray-900">
                {company.twitter_handle ? (
                  <a 
                    href={`https://twitter.com/${company.twitter_handle}`} 
                    target="_blank" 
                    rel="noopener noreferrer" 
                    className="text-blue-600 hover:underline"
                  >
                    @{company.twitter_handle}
                  </a>
                ) : 'Not specified'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Status:</span>
              <span className={`font-medium ${company.twitter_handle ? 'text-green-600' : 'text-gray-400'}`}>
                {company.twitter_handle ? 'Active' : 'Not specified'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Technology stack */}
      <div className="mt-6 pt-6 border-t border-gray-200">
        <h4 className="font-medium text-gray-900 mb-3">Technology Priorities</h4>
        <div className="flex flex-wrap gap-2">
          {innovationMetrics
            .filter(metric => metric.value > 0)
            .sort((a, b) => b.value - a.value)
            .slice(0, 4)
            .map((metric, index) => (
              <span 
                key={index}
                className={`px-3 py-1 rounded-full text-xs font-medium ${metric.bgColor} ${metric.color} border`}
              >
                {metric.label} ({metric.value})
              </span>
            ))}
        </div>
        {innovationMetrics.filter(metric => metric.value > 0).length === 0 && (
          <p className="text-sm text-gray-500 italic">No technology data found</p>
        )}
      </div>
    </div>
  )
}
