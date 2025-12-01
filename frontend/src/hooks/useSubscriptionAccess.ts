import { ApiService } from '@/services/api'
import type { SubscriptionAccessResponse } from '@/types'
import { useEffect, useState } from 'react'

export function useSubscriptionAccess() {
  const [hasAccess, setHasAccess] = useState<boolean | null>(null)
  const [reason, setReason] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [daysRemaining, setDaysRemaining] = useState<number | null>(null)
  const [status, setStatus] = useState<string | null>(null)

  useEffect(() => {
    checkAccess()
  }, [])

  const checkAccess = async () => {
    try {
      setLoading(true)
      const response: SubscriptionAccessResponse = await ApiService.checkSubscriptionAccess()
      setHasAccess(response.has_access)
      setReason(response.reason || null)
      setDaysRemaining(response.days_remaining || null)
      setStatus(response.status || null)
    } catch (err: any) {
      console.error('Error checking subscription access:', err)
      setHasAccess(false)
      setReason('Ошибка при проверке доступа')
    } finally {
      setLoading(false)
    }
  }

  return {
    hasAccess,
    reason,
    loading,
    daysRemaining,
    status,
    refetch: checkAccess
  }
}

