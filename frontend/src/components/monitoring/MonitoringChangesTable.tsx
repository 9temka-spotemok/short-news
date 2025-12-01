import type { Company, MonitoringChangeEvent } from '@/types'
import { formatDistanceToNow } from 'date-fns'
import { ru } from 'date-fns/locale'
import { Briefcase, Clock, ExternalLink, FileText, Globe, Layout, Search, ShoppingBag, Tag } from 'lucide-react'

interface MonitoringChangesTableProps {
  events: MonitoringChangeEvent[]
  companies?: Company[]
  loading?: boolean
  onEventClick?: (event: MonitoringChangeEvent) => void
}

const changeTypeIcons: Record<string, typeof Globe> = {
  website_structure: Layout,
  marketing_banner: Tag,
  marketing_landing: FileText,
  marketing_product: ShoppingBag,
  marketing_jobs: Briefcase,
  seo_meta: Search,
  seo_structure: Search,
  pricing: ShoppingBag,
  other: Globe
}

const changeTypeLabels: Record<string, string> = {
  website_structure: 'Структура сайта',
  marketing_banner: 'Баннер',
  marketing_landing: 'Лендинг',
  marketing_product: 'Продукт',
  marketing_jobs: 'Вакансии',
  seo_meta: 'SEO Meta',
  seo_structure: 'SEO Структура',
  pricing: 'Цены',
  other: 'Другое'
}

export default function MonitoringChangesTable({ 
  events, 
  companies = [],
  loading = false,
  onEventClick 
}: MonitoringChangesTableProps) {
  const getCompanyName = (companyId: string) => {
    const company = companies.find(c => c.id === companyId)
    return company?.name || companyId
  }

  const formatDate = (dateString: string) => {
    try {
      return formatDistanceToNow(new Date(dateString), {
        addSuffix: true,
        locale: ru
      })
    } catch {
      return 'Неизвестно'
    }
  }

  if (loading) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <div className="animate-pulse space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 bg-gray-200 rounded"></div>
          ))}
        </div>
      </div>
    )
  }

  if (events.length === 0) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-8 text-center">
        <Clock className="w-12 h-12 text-gray-400 mx-auto mb-3" />
        <p className="text-sm text-gray-500">Изменения еще не обнаружены</p>
        <p className="text-xs text-gray-400 mt-1">
          Изменения будут отображаться здесь по мере их обнаружения
        </p>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Компания
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Тип изменения
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Описание
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Дата
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Действия
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {events.map((event) => {
              const Icon = changeTypeIcons[event.change_type] || Globe
              const label = changeTypeLabels[event.change_type] || event.change_type
              
              return (
                <tr
                  key={event.id}
                  className="hover:bg-gray-50 transition-colors cursor-pointer"
                  onClick={() => onEventClick?.(event)}
                >
                  <td className="px-4 py-3 whitespace-nowrap">
                    <div className="text-sm font-medium text-gray-900">
                      {getCompanyName(event.company_id)}
                    </div>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <div className="flex items-center gap-2">
                      <Icon className="w-4 h-4 text-gray-500" />
                      <span className="text-sm text-gray-700">{label}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="text-sm text-gray-700 max-w-md truncate">
                      {event.change_summary}
                    </div>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <div className="flex items-center gap-1 text-xs text-gray-500">
                      <Clock className="w-3 h-3" />
                      {formatDate(event.detected_at)}
                    </div>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        onEventClick?.(event)
                      }}
                      className="text-xs text-blue-600 hover:text-blue-700 flex items-center gap-1"
                    >
                      <ExternalLink className="w-3 h-3" />
                      Детали
                    </button>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}




