import { Link } from 'react-router-dom'
import { Lightbulb, ArrowRight } from 'lucide-react'

interface Recommendation {
  id: string
  type: 'action' | 'info' | 'warning'
  title: string
  message: string
  actionLabel?: string
  actionLink?: string
  onAction?: () => void
}

interface RecommendationsProps {
  recommendations: Recommendation[]
  className?: string
}

export default function Recommendations({ recommendations, className = '' }: RecommendationsProps) {
  if (recommendations.length === 0) return null

  const getTypeStyles = (type: Recommendation['type']) => {
    switch (type) {
      case 'action':
        return 'bg-blue-50 border-blue-200 text-blue-900'
      case 'warning':
        return 'bg-yellow-50 border-yellow-200 text-yellow-900'
      case 'info':
      default:
        return 'bg-gray-50 border-gray-200 text-gray-900'
    }
  }

  return (
    <div className={`space-y-3 ${className}`}>
      {recommendations.map((rec) => (
        <div
          key={rec.id}
          className={`card p-4 border-2 ${getTypeStyles(rec.type)}`}
        >
          <div className="flex items-start gap-3">
            <Lightbulb className="h-5 w-5 flex-shrink-0 mt-0.5" />
            <div className="flex-1 min-w-0">
              <h4 className="font-semibold mb-1">{rec.title}</h4>
              <p className="text-sm mb-2">{rec.message}</p>
              {rec.actionLabel && (
                <div className="mt-2">
                  {rec.actionLink ? (
                    <Link
                      to={rec.actionLink}
                      className="inline-flex items-center gap-1 text-sm font-medium hover:underline"
                    >
                      {rec.actionLabel}
                      <ArrowRight className="h-4 w-4" />
                    </Link>
                  ) : rec.onAction ? (
                    <button
                      onClick={rec.onAction}
                      className="inline-flex items-center gap-1 text-sm font-medium hover:underline"
                    >
                      {rec.actionLabel}
                      <ArrowRight className="h-4 w-4" />
                    </button>
                  ) : null}
                </div>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}


