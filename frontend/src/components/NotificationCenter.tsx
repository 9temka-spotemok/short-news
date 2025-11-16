import { Bell, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import api from '../services/api'
import { Notification } from '../types'

export default function NotificationCenter() {
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [unreadCount, setUnreadCount] = useState(0)
  const [isOpen, setIsOpen] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [lastSeenLatestPublishedAt, setLastSeenLatestPublishedAt] = useState<string | null>(null)

  useEffect(() => {
    // Initialize last seen from localStorage to avoid missing first toast
    const stored = localStorage.getItem('lastSeenNewsTs')
    if (stored) {
      setLastSeenLatestPublishedAt(stored)
    }

    fetchUnreadNotifications()
    checkLatestNews()
    
    // Poll for unread notifications and latest news
    const notifInterval = setInterval(fetchUnreadNotifications, 30000)
    const newsInterval = setInterval(checkLatestNews, 90000)
    return () => {
      clearInterval(notifInterval)
      clearInterval(newsInterval)
    }
  }, [])

  const fetchUnreadNotifications = async () => {
    try {
      const response = await api.get('/notifications/unread')
      setNotifications(response.data.notifications)
      setUnreadCount((prev: number) => {
        const base = response.data.unread_count as number
        // preserve any extra badge from latest news detection until user opens panel
        const extra = Math.max(0, prev - base)
        return base + extra
      })
    } catch (error: any) {
      // Only log non-timeout errors to avoid console spam
      if (error?.code !== 'ECONNABORTED') {
        console.error('Error fetching notifications:', error)
      }
    }
  }

  // Lightweight latest news polling integrated into the bell
  const checkLatestNews = async () => {
    try {
      const res = await api.get('/news/', { params: { limit: 5 } })
      const items = res?.data?.items || []
      if (!items.length) return
      const latest = items[0]
      const latestTs: string | undefined = latest.published_at || latest.created_at
      if (!latestTs) return

      // If first run and no stored lastSeen, initialize without toasting
      if (!lastSeenLatestPublishedAt && !localStorage.getItem('lastSeenNewsTs')) {
        setLastSeenLatestPublishedAt(latestTs)
        localStorage.setItem('lastSeenNewsTs', latestTs)
        return
      }

      if (lastSeenLatestPublishedAt && new Date(latestTs) > new Date(lastSeenLatestPublishedAt)) {
        const newerCount = items.filter((n: any) => {
          const ts = n.published_at || n.created_at
          return ts && new Date(ts) > new Date(lastSeenLatestPublishedAt)
        }).length
        if (newerCount > 0) setUnreadCount((c) => c + newerCount)

        toast((t) => (
          <div className="text-sm">
            Появились новые новости.
            <button
              className="ml-3 text-primary-600 font-medium"
              onClick={() => {
                window.dispatchEvent(new CustomEvent('app:refresh-news'))
                // Mark latest as seen on refresh
                setLastSeenLatestPublishedAt(latestTs)
                localStorage.setItem('lastSeenNewsTs', latestTs)
                toast.dismiss(t.id)
              }}
            >
              Обновить
            </button>
          </div>
        ))
      }
      setLastSeenLatestPublishedAt(latestTs)
      localStorage.setItem('lastSeenNewsTs', latestTs)
    } catch (err) {
      // ignore
    }
  }

  const markAsRead = async (notificationId: string) => {
    try {
      await api.put(`/notifications/${notificationId}/read`)
      
      // Update local state
      setNotifications(prev => prev.filter(n => n.id !== notificationId))
      setUnreadCount(prev => Math.max(0, prev - 1))
    } catch (error) {
      console.error('Error marking notification as read:', error)
    }
  }

  const markAllAsRead = async () => {
    try {
      setIsLoading(true)
      await api.put('/notifications/mark-all-read')
      setNotifications([])
      setUnreadCount(0)
    } catch (error) {
      console.error('Error marking all as read:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const getNotificationIcon = (type: string) => {
    const icons: Record<string, string> = {
      new_news: '📰',
      company_active: '🔥',
      pricing_change: '💰',
      funding_announcement: '💵',
      product_launch: '🚀',
      category_trend: '📈',
      keyword_match: '🔍',
      competitor_milestone: '🎯'
    }
    return icons[type] || '📌'
  }

  const getPriorityColor = (priority: string) => {
    const colors: Record<string, string> = {
      high: 'bg-red-100 border-red-300',
      medium: 'bg-yellow-100 border-yellow-300',
      low: 'bg-blue-100 border-blue-300'
    }
    return colors[priority] || 'bg-gray-100 border-gray-300'
  }

  return (
    <div className="relative">
      {/* Notification Bell Icon */}
      {/* <button
        onClick={() => {
          const next = !isOpen
          setIsOpen(next)
          // When opening, mark current latest as seen to reset extra badge
          if (next && lastSeenLatestPublishedAt) {
            localStorage.setItem('lastSeenNewsTs', lastSeenLatestPublishedAt)
          }
          // Refresh server unread count
          fetchUnreadNotifications()
        }}
        className="relative p-2 hover:bg-gray-100 rounded-full transition-colors"
      >
        <Bell className="w-6 h-6 text-gray-700" />
        {unreadCount > 0 && (
          <span className="absolute top-0 right-0 bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center animate-pulse">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button> */}
      {/* TODO: Add notification center */}

      {/* Dropdown */}
      {isOpen && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-40"
            onClick={() => setIsOpen(false)}
          />

          {/* Dropdown Panel */}
          <div className="absolute right-0 mt-2 w-96 bg-white rounded-lg shadow-xl z-50 border border-gray-200">
            {/* Header */}
            <div className="p-4 border-b border-gray-200 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900">
                Notifications
              </h3>
              {unreadCount > 0 && (
                <button
                  onClick={markAllAsRead}
                  disabled={isLoading}
                  className="text-sm text-blue-600 hover:text-blue-800 disabled:opacity-50"
                >
                  Mark all as read
                </button>
              )}
            </div>

            {/* Notifications List */}
            <div className="max-h-96 overflow-y-auto">
              {notifications.length === 0 ? (
                <div className="p-8 text-center text-gray-500">
                  <Bell className="w-12 h-12 mx-auto mb-3 text-gray-300" />
                  <p>No new notifications</p>
                </div>
              ) : (
                <div className="divide-y divide-gray-200">
                  {notifications.map((notification) => (
                    <div
                      key={notification.id}
                      className={`p-4 hover:bg-gray-50 transition-colors border-l-4 ${getPriorityColor(notification.priority)}`}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex items-start flex-1">
                          <span className="text-2xl mr-3">
                            {getNotificationIcon(notification.type)}
                          </span>
                          <div className="flex-1">
                            <p className="font-medium text-gray-900 text-sm">
                              {notification.title}
                            </p>
                            <p className="text-sm text-gray-600 mt-1">
                              {notification.message}
                            </p>
                            <p className="text-xs text-gray-400 mt-2">
                              {new Date(notification.created_at).toLocaleString()}
                            </p>
                          </div>
                        </div>
                        <button
                          onClick={() => markAsRead(notification.id)}
                          className="ml-2 p-1 hover:bg-gray-200 rounded transition-colors"
                          title="Mark as read"
                        >
                          <X className="w-4 h-4 text-gray-500" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Footer */}
            {notifications.length > 0 && (
              <div className="p-3 border-t border-gray-200 text-center">
                <a
                  href="/notifications"
                  className="text-sm text-blue-600 hover:text-blue-800"
                  onClick={() => setIsOpen(false)}
                >
                  View all notifications
                </a>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}



