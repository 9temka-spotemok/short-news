import type { MonitoringStatus } from '@/types'
import { formatDistanceToNow } from 'date-fns'
import { ru } from 'date-fns/locale'
import { Activity, CheckCircle2, Clock, XCircle } from 'lucide-react'

interface MonitoringStatusCardProps {
  status: MonitoringStatus
  onViewDetails?: () => void
}

export default function MonitoringStatusCard({ status, onViewDetails }: MonitoringStatusCardProps) {
  const totalSources = 
    status.sources_count.social_media +
    status.sources_count.website_pages +
    status.sources_count.news_sources +
    status.sources_count.marketing_sources +
    status.sources_count.seo_signals

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'Никогда'
    try {
      return formatDistanceToNow(new Date(dateString), {
        addSuffix: true,
        locale: ru
      })
    } catch {
      return 'Неизвестно'
    }
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <h3 className="font-semibold text-gray-900">{status.company_name}</h3>
          {status.is_active ? (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
              <CheckCircle2 className="w-3 h-3" />
              Активен
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
              <XCircle className="w-3 h-3" />
              Неактивен
            </span>
          )}
        </div>
        {onViewDetails && (
          <button
            onClick={onViewDetails}
            className="text-sm text-blue-600 hover:text-blue-700 font-medium"
          >
            Детали →
          </button>
        )}
      </div>

      <div className="space-y-3">
        {/* Статистика источников */}
        <div className="flex items-center gap-4 text-sm">
          <div className="flex items-center gap-1.5">
            <Activity className="w-4 h-4 text-gray-400" />
            <span className="text-gray-600">Источников:</span>
            <span className="font-semibold text-gray-900">{totalSources}</span>
          </div>
        </div>

        {/* Детали источников */}
        <div className="grid grid-cols-2 gap-2 text-xs">
          {status.sources_count.social_media > 0 && (
            <div className="text-gray-600">
              Соцсети: <span className="font-medium text-gray-900">{status.sources_count.social_media}</span>
            </div>
          )}
          {status.sources_count.website_pages > 0 && (
            <div className="text-gray-600">
              Страницы: <span className="font-medium text-gray-900">{status.sources_count.website_pages}</span>
            </div>
          )}
          {status.sources_count.news_sources > 0 && (
            <div className="text-gray-600">
              Новости: <span className="font-medium text-gray-900">{status.sources_count.news_sources}</span>
            </div>
          )}
          {status.sources_count.marketing_sources > 0 && (
            <div className="text-gray-600">
              Маркетинг: <span className="font-medium text-gray-900">{status.sources_count.marketing_sources}</span>
            </div>
          )}
          {status.sources_count.seo_signals > 0 && (
            <div className="text-gray-600">
              SEO: <span className="font-medium text-gray-900">{status.sources_count.seo_signals}</span>
            </div>
          )}
        </div>

        {/* Последние проверки */}
        <div className="pt-2 border-t border-gray-100">
          <div className="flex items-center gap-1.5 mb-2">
            <Clock className="w-3.5 h-3.5 text-gray-400" />
            <span className="text-xs font-medium text-gray-600">Последние проверки:</span>
          </div>
          <div className="space-y-1 text-xs text-gray-500">
            {status.last_checks.website_structure && (
              <div>Структура: {formatDate(status.last_checks.website_structure)}</div>
            )}
            {status.last_checks.marketing_changes && (
              <div>Маркетинг: {formatDate(status.last_checks.marketing_changes)}</div>
            )}
            {status.last_checks.seo_signals && (
              <div>SEO: {formatDate(status.last_checks.seo_signals)}</div>
            )}
            {status.last_updated && (
              <div className="text-gray-400">Обновлено: {formatDate(status.last_updated)}</div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}




