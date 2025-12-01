import type { MonitoringMatrix } from '@/types'
import { Briefcase, FileText, Globe, Newspaper, Search, ShoppingBag } from 'lucide-react'
import SocialMediaIcons from './SocialMediaIcons'

interface MonitoringSourcesCardProps {
  matrix: MonitoringMatrix
  className?: string
}

const pageTypeLabels: Record<string, string> = {
  pricing: 'Цены',
  features: 'Функции',
  about: 'О компании',
  blog: 'Блог',
  news: 'Новости',
  careers: 'Карьера'
}

export default function MonitoringSourcesCard({ matrix, className = '' }: MonitoringSourcesCardProps) {
  const websiteSources = matrix.website_sources
  const keyPages = websiteSources.current_snapshot?.key_pages || []
  const foundPages = keyPages.filter(page => page.found)

  const socialMediaCount = Object.values(matrix.social_media_sources).filter(
    source => source && source.url
  ).length

  return (
    <div className={`bg-white rounded-lg border border-gray-200 p-4 ${className}`}>
      <h3 className="font-semibold text-gray-900 mb-4">Источники мониторинга</h3>

      <div className="space-y-4">
        {/* Социальные сети */}
        {socialMediaCount > 0 && (
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Globe className="w-4 h-4 text-gray-400" />
              <span className="text-sm font-medium text-gray-700">Социальные сети</span>
              <span className="text-xs text-gray-500">({socialMediaCount})</span>
            </div>
            <SocialMediaIcons sources={matrix.social_media_sources} />
          </div>
        )}

        {/* Ключевые страницы сайта */}
        {foundPages.length > 0 && (
          <div>
            <div className="flex items-center gap-2 mb-2">
              <FileText className="w-4 h-4 text-gray-400" />
              <span className="text-sm font-medium text-gray-700">Основные страницы</span>
              <span className="text-xs text-gray-500">({foundPages.length})</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {foundPages.map((page) => (
                <a
                  key={page.type}
                  href={page.url || '#'}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium bg-blue-50 text-blue-700 hover:bg-blue-100 transition-colors"
                >
                  {pageTypeLabels[page.type] || page.type}
                  <span className="text-blue-500">→</span>
                </a>
              ))}
            </div>
          </div>
        )}

        {/* Пресс-релизы */}
        {matrix.news_sources.press_release_url && (
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Newspaper className="w-4 h-4 text-gray-400" />
              <span className="text-sm font-medium text-gray-700">Пресс-релизы</span>
            </div>
            <a
              href={matrix.news_sources.press_release_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-blue-600 hover:text-blue-700"
            >
              {matrix.news_sources.press_release_url}
            </a>
            {matrix.news_sources.press_releases_count > 0 && (
              <span className="ml-2 text-xs text-gray-500">
                ({matrix.news_sources.press_releases_count} найдено)
              </span>
            )}
          </div>
        )}

        {/* Маркетинговые источники */}
        {(matrix.marketing_sources.pricing || 
          matrix.marketing_sources.products || 
          matrix.marketing_sources.job_postings) && (
          <div>
            <div className="flex items-center gap-2 mb-2">
              <ShoppingBag className="w-4 h-4 text-gray-400" />
              <span className="text-sm font-medium text-gray-700">Маркетинг</span>
            </div>
            <div className="space-y-1 text-xs text-gray-600">
              {matrix.marketing_sources.pricing && (
                <div>Цены: {matrix.marketing_sources.pricing.count} планов</div>
              )}
              {matrix.marketing_sources.products && (
                <div>Продукты: {matrix.marketing_sources.products.count} найдено</div>
              )}
              {matrix.marketing_sources.job_postings && (
                <div className="flex items-center gap-1">
                  <Briefcase className="w-3 h-3" />
                  Вакансии: {matrix.marketing_sources.job_postings.count} позиций
                </div>
              )}
            </div>
          </div>
        )}

        {/* SEO сигналы */}
        {matrix.seo_signals.current_signals && (
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Search className="w-4 h-4 text-gray-400" />
              <span className="text-sm font-medium text-gray-700">SEO сигналы</span>
            </div>
            <div className="space-y-1 text-xs text-gray-600">
              {matrix.seo_signals.meta_tags_count > 0 && (
                <div>Meta теги: {matrix.seo_signals.meta_tags_count}</div>
              )}
              {matrix.seo_signals.structured_data_count > 0 && (
                <div>Structured data: {matrix.seo_signals.structured_data_count}</div>
              )}
              {matrix.seo_signals.robots_txt_exists && (
                <div>robots.txt: ✓</div>
              )}
              {matrix.seo_signals.sitemap_exists && (
                <div>sitemap.xml: ✓</div>
              )}
            </div>
          </div>
        )}

        {/* Пустое состояние */}
        {socialMediaCount === 0 && foundPages.length === 0 && 
         !matrix.news_sources.press_release_url && 
         !matrix.marketing_sources.pricing && 
         !matrix.seo_signals.current_signals && (
          <div className="text-sm text-gray-500 text-center py-4">
            Источники мониторинга еще не найдены
          </div>
        )}
      </div>
    </div>
  )
}




