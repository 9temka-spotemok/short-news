import type { Company, MonitoringStatus } from '@/types'
import { formatDistanceToNow } from 'date-fns'
import { ru } from 'date-fns/locale'
import { Activity, CheckCircle2, Clock, ExternalLink, TrendingUp, XCircle } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

interface CompanyMonitoringCardProps {
  company: Company
  status: MonitoringStatus
  onViewDetails?: () => void
}

export default function CompanyMonitoringCard({ company, status, onViewDetails }: CompanyMonitoringCardProps) {
  const navigate = useNavigate()

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

  const handleViewDetails = () => {
    if (onViewDetails) {
      onViewDetails()
    } else {
      navigate(`/competitor-analysis?company_id=${status.company_id}`)
    }
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6 hover:shadow-lg transition-shadow">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-start gap-3">
          {company.logo_url ? (
            <img
              src={company.logo_url}
              alt={company.name}
              className="w-12 h-12 rounded-lg object-cover"
              onError={(e) => {
                e.currentTarget.style.display = 'none'
              }}
            />
          ) : (
            <div className="w-12 h-12 rounded-lg bg-gray-200 flex items-center justify-center">
              <Activity className="w-6 h-6 text-gray-400" />
            </div>
          )}
          <div>
            <h3 className="font-semibold text-gray-900">{company.name}</h3>
            {company.category && (
              <span className="text-xs text-gray-500 mt-1">{company.category}</span>
            )}
          </div>
        </div>
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

      {/* Stats Grid */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="bg-gray-50 rounded-lg p-3">
          <div className="flex items-center gap-2 mb-1">
            <Activity className="w-4 h-4 text-gray-400" />
            <span className="text-xs text-gray-600">Источников</span>
          </div>
          <div className="text-xl font-bold text-gray-900">{totalSources}</div>
        </div>
        <div className="bg-gray-50 rounded-lg p-3">
          <div className="flex items-center gap-2 mb-1">
            <TrendingUp className="w-4 h-4 text-gray-400" />
            <span className="text-xs text-gray-600">Последнее обновление</span>
          </div>
          <div className="text-sm font-medium text-gray-900">
            {formatDate(status.last_updated)}
          </div>
        </div>
      </div>

      {/* Sources Breakdown */}
      <div className="mb-4">
        <div className="text-xs font-medium text-gray-700 mb-2">Источники:</div>
        <div className="flex flex-wrap gap-2">
          {status.sources_count.social_media > 0 && (
            <span className="text-xs px-2 py-1 bg-blue-100 text-blue-700 rounded-full">
              Соцсети: {status.sources_count.social_media}
            </span>
          )}
          {status.sources_count.website_pages > 0 && (
            <span className="text-xs px-2 py-1 bg-green-100 text-green-700 rounded-full">
              Страницы: {status.sources_count.website_pages}
            </span>
          )}
          {status.sources_count.news_sources > 0 && (
            <span className="text-xs px-2 py-1 bg-purple-100 text-purple-700 rounded-full">
              Новости: {status.sources_count.news_sources}
            </span>
          )}
          {status.sources_count.marketing_sources > 0 && (
            <span className="text-xs px-2 py-1 bg-orange-100 text-orange-700 rounded-full">
              Маркетинг: {status.sources_count.marketing_sources}
            </span>
          )}
          {status.sources_count.seo_signals > 0 && (
            <span className="text-xs px-2 py-1 bg-indigo-100 text-indigo-700 rounded-full">
              SEO: {status.sources_count.seo_signals}
            </span>
          )}
        </div>
      </div>

      {/* Last Checks */}
      <div className="pt-3 border-t border-gray-100 mb-4">
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
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center justify-between pt-3 border-t border-gray-100">
        {company.website && (
          <a
            href={company.website}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-blue-600 hover:text-blue-700 flex items-center gap-1"
          >
            <ExternalLink className="w-3 h-3" />
            Сайт
          </a>
        )}
        <button
          onClick={handleViewDetails}
          className="text-sm font-medium text-blue-600 hover:text-blue-700"
        >
          Детали →
        </button>
      </div>
    </div>
  )
}




