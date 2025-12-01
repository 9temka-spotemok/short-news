import { ApiService } from '@/services/api'
import { Subscription, SubscriptionStatus } from '@/types'
import { AlertCircle, Calendar, CreditCard } from 'lucide-react'
import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'

export default function SubscriptionStatusCard() {
  const [subscription, setSubscription] = useState<Subscription | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadSubscription()
  }, [])

  const loadSubscription = async () => {
    try {
      const response = await ApiService.getCurrentSubscription()
      setSubscription(response.subscription)
    } catch (err: any) {
      toast.error(err.message || 'Ошибка при загрузке подписки')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return <div className="animate-pulse bg-gray-200 h-24 rounded-lg" />
  }

  if (!subscription) {
    return (
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <div className="flex items-center gap-2 text-yellow-800">
          <AlertCircle className="w-5 h-5" />
          <span className="font-medium">Подписка не найдена</span>
        </div>
        <p className="text-sm text-yellow-700 mt-2">
          Завершите онбординг, чтобы начать триал на 3 дня
        </p>
      </div>
    )
  }

  const getStatusColor = () => {
    switch (subscription.status) {
      case SubscriptionStatus.TRIAL:
        return 'bg-blue-50 border-blue-200 text-blue-800'
      case SubscriptionStatus.ACTIVE:
        return 'bg-green-50 border-green-200 text-green-800'
      case SubscriptionStatus.EXPIRED:
        return 'bg-red-50 border-red-200 text-red-800'
      case SubscriptionStatus.CANCELLED:
        return 'bg-gray-50 border-gray-200 text-gray-800'
      default:
        return 'bg-gray-50 border-gray-200 text-gray-800'
    }
  }

  const getStatusText = () => {
    switch (subscription.status) {
      case SubscriptionStatus.TRIAL:
        return 'Триал активен'
      case SubscriptionStatus.ACTIVE:
        return 'Подписка активна'
      case SubscriptionStatus.EXPIRED:
        return 'Подписка истекла'
      case SubscriptionStatus.CANCELLED:
        return 'Подписка отменена'
      default:
        return 'Неизвестный статус'
    }
  }

  return (
    <div className={`border rounded-lg p-4 ${getStatusColor()}`}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <CreditCard className="w-5 h-5" />
          <span className="font-semibold">{getStatusText()}</span>
        </div>
        {subscription.is_active && (
          <span className="text-sm font-medium">
            ${subscription.price}/{subscription.plan_type === 'monthly' ? 'мес' : 'год'}
          </span>
        )}
      </div>

      {subscription.is_active && subscription.days_remaining > 0 && subscription.days_remaining < 9999 && (
        <div className="flex items-center gap-2 text-sm mt-2">
          <Calendar className="w-4 h-4" />
          <span>
            {subscription.days_remaining === 1
              ? 'Остался 1 день'
              : subscription.days_remaining > 1
              ? `Осталось ${subscription.days_remaining} дней`
              : 'Неограниченный доступ (dev)'}
          </span>
        </div>
      )}

      {subscription.days_remaining >= 9999 && (
        <div className="flex items-center gap-2 text-sm mt-2 text-green-700">
          <Calendar className="w-4 h-4" />
          <span>Неограниченный доступ (dev режим)</span>
        </div>
      )}

      {subscription.status === SubscriptionStatus.TRIAL && subscription.days_remaining <= 1 && subscription.days_remaining < 9999 && (
        <button
          onClick={() => {
            // TODO: Открыть модальное окно оплаты
            toast('Интеграция с платежной системой в разработке')
          }}
          className="mt-3 w-full bg-primary-600 text-white py-2 px-4 rounded-lg hover:bg-primary-700 transition-colors font-medium"
        >
          Оформить подписку
        </button>
      )}

      {subscription.status === SubscriptionStatus.EXPIRED && (
        <button
          onClick={() => {
            // TODO: Открыть модальное окно оплаты
            toast('Интеграция с платежной системой в разработке')
          }}
          className="mt-3 w-full bg-primary-600 text-white py-2 px-4 rounded-lg hover:bg-primary-700 transition-colors font-medium"
        >
          Продлить подписку
        </button>
      )}
    </div>
  )
}

