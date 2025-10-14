import { Bell, Check, Filter, Trash2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import api from '../services/api'
import { Notification, NotificationType } from '../types'

export default function NotificationsPage() {
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [total, setTotal] = useState(0)
  const [skip, setSkip] = useState(0)
  const [limit] = useState(20)
  const [filter, setFilter] = useState<'all' | 'unread'>('all')
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    fetchNotifications()
  }, [skip, filter])

  const fetchNotifications = async () => {
    try {
      setIsLoading(true)
      const response = await api.get('/notifications/', {
        params: {
          skip,
          limit,
          unread_only: filter === 'unread'
        }
      })
      setNotifications(response.data.notifications)
      setTotal(response.data.total)
    } catch (error) {
      console.error('Error fetching notifications:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const markAsRead = async (notificationId: string) => {
    try {
      await api.put(`/notifications/${notificationId}/read`)
      fetchNotifications()
    } catch (error) {
      console.error('Error marking notification as read:', error)
    }
  }

  const markAllAsRead = async () => {
    try {
      await api.put('/notifications/mark-all-read')
      fetchNotifications()
    } catch (error) {
      console.error('Error marking all as read:', error)
    }
  }

  const deleteNotification = async (notificationId: string) => {
    try {
      await api.delete(`/notifications/${notificationId}`)
      fetchNotifications()
    } catch (error) {
      console.error('Error deleting notification:', error)
    }
  }

  const getNotificationIcon = (type: NotificationType) => {
    const icons: Record<NotificationType, string> = {
      new_news: '📰',
      company_active: '🔥',
      pricing_change: '💰',
      funding_announcement: '💵',
      product_launch: '🚀',
      category_trend: '📈',
      keyword_match: '🔍',
      competitor_milestone: '🎯'
    }
    return icons[type]
  }

  const getPriorityColor = (priority: string) => {
    const colors: Record<string, string> = {
      high: 'bg-red-50 border-red-200',
      medium: 'bg-yellow-50 border-yellow-200',
      low: 'bg-blue-50 border-blue-200'
    }
    return colors[priority] || 'bg-gray-50 border-gray-200'
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto py-8 px-4">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 flex items-center">
              <Bell className="w-8 h-8 mr-3" />
              Notifications
            </h1>
            <p className="text-gray-600 mt-2">
              Stay updated with important events
            </p>
          </div>
          
          <button
            onClick={markAllAsRead}
            className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center"
          >
            <Check className="w-4 h-4 mr-2" />
            Mark all as read
          </button>
        </div>

        {/* Filter */}
        <div className="mb-6 flex items-center space-x-4">
          <Filter className="w-5 h-5 text-gray-500" />
          <div className="flex space-x-2">
            {(['all', 'unread'] as const).map((f) => (
              <button
                key={f}
                onClick={() => {
                  setFilter(f)
                  setSkip(0)
                }}
                className={`px-4 py-2 rounded-lg transition-all ${
                  filter === f
                    ? 'bg-blue-600 text-white'
                    : 'bg-white text-gray-700 border border-gray-300 hover:border-blue-300'
                }`}
              >
                {f === 'all' ? 'All' : 'Unread'}
              </button>
            ))}
          </div>
        </div>

        {/* Notifications List */}
        <div className="bg-white rounded-lg shadow-md divide-y">
          {isLoading ? (
            <div className="p-8 text-center text-gray-600">Loading...</div>
          ) : notifications.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              <Bell className="w-16 h-16 mx-auto mb-4 text-gray-300" />
              <p>No notifications</p>
            </div>
          ) : (
            <>
              {notifications.map((notification) => (
                <div
                  key={notification.id}
                  className={`p-4 border-l-4 ${getPriorityColor(notification.priority)} ${
                    notification.is_read ? 'opacity-60' : ''
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-start flex-1">
                      <span className="text-3xl mr-4">
                        {getNotificationIcon(notification.type)}
                      </span>
                      <div className="flex-1">
                        <div className="flex items-center space-x-2 mb-1">
                          <h3 className="font-semibold text-gray-900">
                            {notification.title}
                          </h3>
                          {!notification.is_read && (
                            <span className="bg-blue-500 text-white text-xs px-2 py-0.5 rounded-full">
                              New
                            </span>
                          )}
                        </div>
                        <p className="text-gray-700 mb-2">{notification.message}</p>
                        <div className="flex items-center space-x-4 text-xs text-gray-500">
                          <span>
                            {new Date(notification.created_at).toLocaleString()}
                          </span>
                          <span className="capitalize">
                            Priority: {notification.priority}
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center space-x-2 ml-4">
                      {!notification.is_read && (
                        <button
                          onClick={() => markAsRead(notification.id)}
                          className="p-2 hover:bg-gray-200 rounded transition-colors"
                          title="Mark as read"
                        >
                          <Check className="w-4 h-4 text-green-600" />
                        </button>
                      )}
                      <button
                        onClick={() => deleteNotification(notification.id)}
                        className="p-2 hover:bg-gray-200 rounded transition-colors"
                        title="Delete"
                      >
                        <Trash2 className="w-4 h-4 text-red-600" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </>
          )}
        </div>

        {/* Pagination */}
        {total > limit && (
          <div className="mt-6 flex items-center justify-between">
            <button
              onClick={() => setSkip(Math.max(0, skip - limit))}
              disabled={skip === 0}
              className="px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Previous
            </button>
            <span className="text-sm text-gray-600">
              Showing {skip + 1} - {Math.min(skip + limit, total)} of {total}
            </span>
            <button
              onClick={() => setSkip(skip + limit)}
              disabled={skip + limit >= total}
              className="px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Next
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

