import { AlertCircle } from 'lucide-react'
import type { ReactNode } from 'react'

type ErrorBannerProps = {
  title?: string
  message: string
  details?: ReactNode
  onRetry?: () => void
  retryLabel?: string
  actions?: ReactNode
  className?: string
  compact?: boolean
}

export function ErrorBanner({
  title,
  message,
  details,
  onRetry,
  retryLabel = 'Retry',
  actions,
  className = '',
  compact = false
}: ErrorBannerProps) {
  return (
    <div
      className={`rounded-md border border-red-200 bg-red-50 text-red-700 ${
        compact ? 'px-3 py-2 text-xs' : 'p-4 text-sm'
      } ${className}`}
      role="alert"
      aria-live="assertive"
    >
      <div className="flex items-start gap-3">
        <AlertCircle className="mt-0.5 h-5 w-5 flex-shrink-0 text-red-600" aria-hidden />
        <div className="flex-1 space-y-2">
          {title ? <p className="font-medium text-red-800">{title}</p> : null}
          <p className="leading-snug">{message}</p>
          {details ? <div className="text-xs text-red-600">{details}</div> : null}
          {onRetry || actions ? (
            <div className="flex flex-wrap gap-2 pt-1">
              {onRetry ? (
                <button
                  type="button"
                  onClick={onRetry}
                  className="inline-flex items-center rounded-md border border-red-200 bg-white px-3 py-1 text-xs font-medium text-red-700 transition-colors hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-red-400 focus:ring-offset-1"
                >
                  {retryLabel}
                </button>
              ) : null}
              {actions}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  )
}




