import { Loader2 } from 'lucide-react'
import type { ReactNode } from 'react'

type LoadingOverlayProps = {
  label?: string
  description?: string
  overlay?: boolean
  spinnerSize?: 'sm' | 'md' | 'lg'
  className?: string
  children?: ReactNode
}

const spinnerSizeStyles: Record<NonNullable<LoadingOverlayProps['spinnerSize']>, string> = {
  sm: 'h-4 w-4',
  md: 'h-6 w-6',
  lg: 'h-10 w-10'
}

export function LoadingOverlay({
  label = 'Loading…',
  description,
  overlay = false,
  spinnerSize = 'md',
  className = '',
  children
}: LoadingOverlayProps) {
  const baseClass = overlay
    ? 'absolute inset-0 z-10 flex items-center justify-center bg-white/80 backdrop-blur-sm'
    : 'flex w-full items-center justify-center'

  return (
    <div className={`${baseClass} ${className}`} role="status" aria-live="polite">
      <div className="flex flex-col items-center text-center">
        <Loader2
          className={`${spinnerSizeStyles[spinnerSize]} animate-spin text-blue-600`}
          aria-hidden
        />
        {label ? <p className="mt-2 text-sm font-medium text-gray-700">{label}</p> : null}
        {description ? <p className="mt-1 max-w-xs text-xs text-gray-500">{description}</p> : null}
        {children}
      </div>
    </div>
  )
}




