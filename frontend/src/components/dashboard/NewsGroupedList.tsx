import { formatDistance } from 'date-fns'
import { enUS } from 'date-fns/locale'
import { ExternalLink } from 'lucide-react'
import { useState } from 'react'

interface NewsItem {
  id: string
  title: string
  summary?: string
  source_url: string
  published_at: string
  created_at: string
  category?: string
  company?: {
    id: string
    name: string
  }
}

type DateFilter = 'all' | 'today' | 'yesterday' | 'this_week'

interface NewsGroupedListProps {
  news: NewsItem[]
  categoryLabels?: Record<string, string>
  maxItemsPerGroup?: number
  maxHeight?: string
}

export default function NewsGroupedList({ 
  news, 
  categoryLabels = {},
  maxItemsPerGroup = 5,
  maxHeight = '600px'
}: NewsGroupedListProps) {
  const [dateFilter, setDateFilter] = useState<DateFilter>('all')
  const formatDate = (dateString: string) => {
    try {
      const date = new Date(dateString)
      return formatDistance(date, new Date(), { addSuffix: true, locale: enUS })
    } catch {
      return 'Recently'
    }
  }

  const groupNewsByDate = () => {
    const now = new Date()
    // Используем UTC для корректного сравнения дат независимо от часового пояса
    const today = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()))
    const yesterday = new Date(today)
    yesterday.setUTCDate(yesterday.getUTCDate() - 1)
    const weekAgo = new Date(today)
    weekAgo.setUTCDate(weekAgo.getUTCDate() - 7)

    const groups: {
      label: string
      items: NewsItem[]
    }[] = [
      { label: 'Today', items: [] },
      { label: 'Yesterday', items: [] },
      { label: 'This Week', items: [] },
      { label: 'Older', items: [] }
    ]

    news.forEach((item) => {
      try {
        const itemDate = new Date(item.published_at || item.created_at)
        // Нормализуем дату к UTC для корректного сравнения
        const itemDateOnly = new Date(Date.UTC(
          itemDate.getUTCFullYear(), 
          itemDate.getUTCMonth(), 
          itemDate.getUTCDate()
        ))

        if (itemDateOnly.getTime() === today.getTime()) {
          groups[0].items.push(item)
        } else if (itemDateOnly.getTime() === yesterday.getTime()) {
          groups[1].items.push(item)
        } else if (itemDateOnly >= weekAgo) {
          groups[2].items.push(item)
        } else {
          groups[3].items.push(item)
        }
      } catch (error) {
        // Если не удалось распарсить дату, добавляем в "Older"
        console.warn('Failed to parse date for item:', item.id, error)
        groups[3].items.push(item)
      }
    })

    return groups.filter(group => group.items.length > 0)
  }

  const allGroupedNews = groupNewsByDate()

  // Filter groups based on selected date filter
  const getFilteredGroups = () => {
    if (dateFilter === 'all') {
      return allGroupedNews
    }
    
    const filterMap: Record<DateFilter, string[]> = {
      all: ['Today', 'Yesterday', 'This Week', 'Older'],
      today: ['Today'],
      yesterday: ['Yesterday'],
      this_week: ['Today', 'Yesterday', 'This Week']
    }

    return allGroupedNews.filter(group => filterMap[dateFilter].includes(group.label))
  }

  const groupedNews = getFilteredGroups()

  return (
    <div className="flex flex-col h-full">
      {/* Date Filter Buttons - Always visible */}
      <div className="flex gap-2 mb-4 flex-shrink-0">
        <button
          onClick={() => setDateFilter('today')}
          className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
            dateFilter === 'today'
              ? 'bg-primary-600 text-white'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          Today
        </button>
        <button
          onClick={() => setDateFilter('yesterday')}
          className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
            dateFilter === 'yesterday'
              ? 'bg-primary-600 text-white'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          Yesterday
        </button>
        <button
          onClick={() => setDateFilter('this_week')}
          className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
            dateFilter === 'this_week'
              ? 'bg-primary-600 text-white'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          This Week
        </button>
        <button
          onClick={() => setDateFilter('all')}
          className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
            dateFilter === 'all'
              ? 'bg-primary-600 text-white'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          All
        </button>
      </div>

      {/* Scrollable News List */}
      <div 
        className="flex-1 overflow-y-auto space-y-6 pr-2"
        style={{ maxHeight }}
      >
        {groupedNews.length === 0 ? (
          <div className="text-center py-8">
            <p className="text-gray-500">No news available for selected period</p>
          </div>
        ) : (
          groupedNews.map((group) => (
        <div key={group.label}>
          {/* Group Header */}
          <div className="flex items-center gap-3 mb-4">
            <div className="flex-1 border-t border-gray-200"></div>
            <h3 className="text-sm font-semibold text-gray-700 px-3">
              {group.label}
            </h3>
            <div className="flex-1 border-t border-gray-200"></div>
          </div>

          {/* News Items */}
          <div className="space-y-3">
            {group.items.slice(0, maxItemsPerGroup).map((item) => (
              <div key={item.id} className="card p-4 hover:shadow-md transition-shadow">
                <div className="flex items-start gap-3">
                  <div className="w-2 h-2 bg-primary-600 rounded-full mt-2 flex-shrink-0"></div>
                  <div className="flex-1 min-w-0">
                    <a
                      href={item.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm font-medium text-gray-900 hover:text-primary-600 line-clamp-2 block mb-1"
                    >
                      {item.title}
                    </a>
                    {item.summary && (
                      <p className="text-xs text-gray-600 line-clamp-2 mb-2">
                        {item.summary}
                      </p>
                    )}
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-xs text-gray-500">
                        {formatDate(item.published_at || item.created_at)}
                      </span>
                      {item.category && (
                        <>
                          <span className="text-xs text-gray-400">•</span>
                          <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">
                            {categoryLabels[item.category] || item.category}
                          </span>
                        </>
                      )}
                      {item.company && (
                        <>
                          <span className="text-xs text-gray-400">•</span>
                          <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">
                            {item.company.name}
                          </span>
                        </>
                      )}
                      <a
                        href={item.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="ml-auto text-xs text-primary-600 hover:text-primary-700 inline-flex items-center gap-1"
                      >
                        Read <ExternalLink className="h-3 w-3" />
                      </a>
                    </div>
                  </div>
                </div>
              </div>
            ))}
            {group.items.length > maxItemsPerGroup && (
              <p className="text-xs text-gray-500 text-center py-2">
                +{group.items.length - maxItemsPerGroup} more items
              </p>
            )}
          </div>
        </div>
        ))
        )}
      </div>
    </div>
  )
}

