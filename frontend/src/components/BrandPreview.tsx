

interface BrandPreviewProps {
  company: {
    id: string
    name: string
    website?: string
    description?: string
    logo_url?: string
    category?: string
  }
  stats: {
    total_news: number
    categories_breakdown: { category: string; count: number }[]
    activity_score: number
    avg_priority: number
  }
}

function MetricCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="bg-gray-50 rounded-lg p-3 text-center">
      <div className="text-2xl font-bold text-primary-600">{value}</div>
      <div className="text-xs text-gray-600 mt-1">{label}</div>
    </div>
  )
}

function calculateActiveDays(stats: BrandPreviewProps['stats']): number {
  // Simple calculation based on activity score
  // In a real implementation, this would be calculated from actual daily activity data
  return Math.min(Math.round(stats.activity_score / 10), 30)
}

export default function BrandPreview({ company, stats }: BrandPreviewProps) {
  const totalNews = stats.total_news
  const topCategories = stats.categories_breakdown.slice(0, 5)

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      {/* Header с логотипом и названием */}
      <div className="flex items-center mb-4">
        {company.logo_url && (
          <img 
            src={company.logo_url} 
            alt={company.name} 
            className="w-16 h-16 rounded-lg mr-4 object-cover" 
          />
        )}
        <div>
          <h2 className="text-2xl font-bold text-gray-900">{company.name}</h2>
          <p className="text-sm text-gray-600">{company.category}</p>
          {company.website && (
            <a 
              href={company.website} 
              target="_blank" 
              rel="noopener noreferrer"
              className="text-sm text-primary-600 hover:underline"
            >
              {company.website}
            </a>
          )}
        </div>
      </div>
      
      {/* Description */}
      {company.description && (
        <p className="text-gray-700 mb-6">{company.description}</p>
      )}
      
      {/* Metrics Grid */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <MetricCard label="Total News" value={stats.total_news} />
        <MetricCard label="Activity Score" value={stats.activity_score.toFixed(1)} />
        <MetricCard label="Avg Priority" value={stats.avg_priority.toFixed(2)} />
        <MetricCard label="Active Days" value={calculateActiveDays(stats)} />
      </div>
      
      {/* Top Categories */}
      <div>
        <h3 className="font-semibold text-gray-900 mb-3">Top Categories</h3>
        <div className="space-y-2">
          {topCategories.map(cat => {
            const percentage = totalNews > 0 ? Math.round((cat.count / totalNews) * 100) : 0
            return (
              <div key={cat.category} className="flex justify-between py-2">
                <span className="text-gray-700 capitalize">
                  {cat.category.replace(/_/g, ' ')}
                </span>
                <span className="text-gray-600 font-medium">
                  {cat.count} ({percentage}%)
                </span>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
