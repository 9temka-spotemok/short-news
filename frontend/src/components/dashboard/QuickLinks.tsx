import { Activity, BarChart3, Bell, TrendingUp } from 'lucide-react'
import { Link } from 'react-router-dom'

interface QuickLink {
  to: string
  icon: React.ComponentType<{ className?: string }>
  title: string
  description: string
}

const quickLinks: QuickLink[] = [
  {
    to: '/competitor-analysis',
    icon: BarChart3,
    title: 'Competitor Analysis',
    description: 'Deep dive into competitor insights and comparisons'
  },
  {
    to: '/monitoring',
    icon: Activity,
    title: 'Monitoring',
    description: 'Track competitor changes and updates'
  },
  {
    to: '/news-analytics',
    icon: TrendingUp,
    title: 'News Analytics',
    description: 'View trends, statistics, and detailed analytics'
  },
  // {
  //   to: '/settings',
  //   icon: Settings,
  //   title: 'Settings',
  //   description: 'Manage your preferences and account settings'
  // },
  {
    to: '/notifications',
    icon: Bell,
    title: 'Notifications',
    description: 'Configure alerts and notification preferences'
  }
]

export default function QuickLinks() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {quickLinks.map((link) => {
        const Icon = link.icon
        return (
          <Link
            key={link.to}
            to={link.to}
            className="card p-6 hover:shadow-lg transition-all hover:border-primary-300 group"
          >
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 bg-primary-100 rounded-lg flex items-center justify-center group-hover:bg-primary-200 transition-colors">
                <Icon className="h-6 w-6 text-primary-600" />
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="font-semibold text-gray-900 mb-1 group-hover:text-primary-600 transition-colors">
                  {link.title}
                </h3>
                <p className="text-sm text-gray-600 line-clamp-2">
                  {link.description}
                </p>
              </div>
            </div>
            <div className="mt-4 text-sm text-primary-600 font-medium group-hover:text-primary-700">
              View Details →
            </div>
          </Link>
        )
      })}
    </div>
  )
}


