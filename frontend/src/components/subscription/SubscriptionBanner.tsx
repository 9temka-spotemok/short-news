import { useSubscriptionAccess } from '@/hooks/useSubscriptionAccess'
import { AlertCircle, X } from 'lucide-react'
import { useState } from 'react'

export default function SubscriptionBanner() {
  const { hasAccess, reason, loading } = useSubscriptionAccess()
  const [dismissed, setDismissed] = useState(false)

  if (loading || hasAccess || dismissed) {
    return null
  }

  return (
    <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4 mb-4">
      <div className="flex items-start">
        <AlertCircle className="w-5 h-5 text-yellow-400 mr-3 flex-shrink-0 mt-0.5" />
        <div className="flex-1">
          <h3 className="text-sm font-medium text-yellow-800">
            Требуется подписка
          </h3>
          <p className="text-sm text-yellow-700 mt-1">
            {reason || 'Для доступа к функциям требуется активная подписка'}
          </p>
        </div>
        <button
          onClick={() => setDismissed(true)}
          className="ml-4 text-yellow-400 hover:text-yellow-600 transition-colors"
          aria-label="Закрыть баннер"
        >
          <X className="w-5 h-5" />
        </button>
      </div>
    </div>
  )
}

