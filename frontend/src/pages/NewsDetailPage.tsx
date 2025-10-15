import { useFavoriteNews, useMarkNewsRead, useNewsItem } from '@/hooks/useNews'
import { formatDistance } from 'date-fns'
import { enUS } from 'date-fns/locale'
import {
    ArrowLeft,
    Building,
    Calendar,
    Clock,
    ExternalLink,
    Eye,
    Heart,
    Star,
    Tag,
    TrendingUp
} from 'lucide-react'
import { useState } from 'react'
import toast from 'react-hot-toast'
import { Link, useParams } from 'react-router-dom'

export default function NewsDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [isFavorited, setIsFavorited] = useState(false)
  const [isRead, setIsRead] = useState(false)

  const { 
    data: newsItem, 
    isLoading, 
    error 
  } = useNewsItem(id || '')

  const markAsReadMutation = useMarkNewsRead()
  const favoriteMutation = useFavoriteNews()

  const handleMarkAsRead = async () => {
    if (!id || isRead) return
    
    try {
      await markAsReadMutation.mutateAsync(id)
      setIsRead(true)
      toast.success('Marked as read')
    } catch (error) {
      toast.error('Failed to mark as read')
    }
  }

  const handleFavorite = async () => {
    if (!id) return
    
    try {
      await favoriteMutation.mutateAsync(id)
      setIsFavorited(!isFavorited)
      toast.success(isFavorited ? 'Removed from favorites' : 'Added to favorites')
    } catch (error) {
      toast.error('Failed to update favorites')
    }
  }

  const formatDate = (dateString: string) => {
    try {
      const date = new Date(dateString)
      return formatDistance(date, new Date(), { addSuffix: true, locale: enUS })
    } catch {
      return 'Recently'
    }
  }

  const getPriorityIcon = (priorityLevel: string) => {
    switch (priorityLevel) {
      case 'High':
        return <Star className="h-5 w-5 text-red-500" />
      case 'Medium':
        return <TrendingUp className="h-5 w-5 text-yellow-500" />
      default:
        return <Clock className="h-5 w-5 text-gray-400" />
    }
  }

  const getPriorityColor = (priorityLevel: string) => {
    switch (priorityLevel) {
      case 'High':
        return 'text-red-600 bg-red-100'
      case 'Medium':
        return 'text-yellow-600 bg-yellow-100'
      default:
        return 'text-gray-600 bg-gray-100'
    }
  }

  if (isLoading) {
    return (
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
          <p className="mt-4 text-gray-600">Loading news article...</p>
        </div>
      </div>
    )
  }

  if (error || !newsItem) {
    return (
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="text-center py-12">
          <p className="text-gray-600 text-lg mb-4">News article not found</p>
          <Link to="/news" className="btn btn-primary">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to News
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Back Button */}
      <div className="mb-6">
        <Link 
          to="/news" 
          className="inline-flex items-center text-primary-600 hover:text-primary-700 font-medium"
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to News
        </Link>
      </div>

      {/* Article Header */}
      <header className="mb-8">
        {/* Category and Priority */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-3">
            {newsItem.category && (
              <span className="badge badge-primary">
                {newsItem.category.replace('_', ' ')}
              </span>
            )}
            <span className={`badge ${getPriorityColor(newsItem.priority_level)} flex items-center`}>
              {getPriorityIcon(newsItem.priority_level)}
              <span className="ml-1">{newsItem.priority_level} Priority</span>
            </span>
            {newsItem.is_recent && (
              <span className="badge badge-success">Recent</span>
            )}
          </div>
          
          <div className="flex items-center space-x-2">
            <button
              onClick={handleMarkAsRead}
              disabled={isRead || markAsReadMutation.isPending}
              className={`btn btn-sm ${isRead ? 'btn-success' : 'btn-outline'}`}
            >
              <Eye className="h-4 w-4 mr-1" />
              {isRead ? 'Read' : 'Mark as Read'}
            </button>
            
            <button
              onClick={handleFavorite}
              disabled={favoriteMutation.isPending}
              className={`btn btn-sm ${isFavorited ? 'btn-error' : 'btn-outline'}`}
            >
              <Heart className={`h-4 w-4 mr-1 ${isFavorited ? 'fill-current' : ''}`} />
              {isFavorited ? 'Favorited' : 'Favorite'}
            </button>
          </div>
        </div>

        {/* Title */}
        <h1 className="text-3xl font-bold text-gray-900 mb-4 leading-tight">
          {newsItem.title}
        </h1>

        {/* Meta Information */}
        <div className="flex flex-wrap items-center gap-4 text-sm text-gray-600 mb-6">
          <div className="flex items-center">
            <Calendar className="h-4 w-4 mr-1" />
            {formatDate(newsItem.published_at)}
          </div>
          
          <div className="flex items-center">
            <Tag className="h-4 w-4 mr-1" />
            <span className="capitalize">{newsItem.source_type}</span>
          </div>
          
          {newsItem.company && (
            <div className="flex items-center">
              <Building className="h-4 w-4 mr-1" />
              {newsItem.company.name}
            </div>
          )}
        </div>
      </header>

      {/* Article Content */}
      <article className="prose prose-lg max-w-none mb-8">
        {newsItem.content ? (
          <div 
            className="text-gray-800 leading-relaxed"
            dangerouslySetInnerHTML={{ __html: newsItem.content }}
          />
        ) : (
          <div className="text-gray-600">
            <p className="text-lg leading-relaxed mb-4">
              {newsItem.summary || 'No content available for this article.'}
            </p>
            <p className="text-sm text-gray-500">
              Visit the source to read the full article.
            </p>
          </div>
        )}
      </article>

      {/* Keywords */}
      {newsItem.keywords && newsItem.keywords.length > 0 && (
        <div className="mb-8">
          <h3 className="text-lg font-semibold text-gray-900 mb-3">Keywords</h3>
          <div className="flex flex-wrap gap-2">
            {newsItem.keywords.map((keyword, index) => (
              <span
                key={index}
                className="bg-gray-100 text-gray-700 px-3 py-1 rounded-full text-sm"
              >
                {keyword.keyword}
                <span className="text-gray-500 ml-1">
                  ({keyword.relevance.toFixed(2)})
                </span>
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Company Information */}
      {newsItem.company && (
        <div className="bg-gray-50 rounded-lg p-6 mb-8">
          <h3 className="text-lg font-semibold text-gray-900 mb-3">About {newsItem.company.name}</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <p className="text-gray-600 mb-2">
                {newsItem.company.description || 'No description available.'}
              </p>
              {newsItem.company.website && (
                <a
                  href={newsItem.company.website}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-primary-600 hover:text-primary-700 font-medium"
                >
                  Visit Website →
                </a>
              )}
            </div>
            <div className="text-sm text-gray-500">
              <div className="space-y-1">
                <div>Category: {newsItem.company.category}</div>
                {newsItem.company.twitter_handle && (
                  <div>Twitter: @{newsItem.company.twitter_handle}</div>
                )}
                {newsItem.company.github_org && (
                  <div>GitHub: {newsItem.company.github_org}</div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Activities */}
      {newsItem.activities && newsItem.activities.length > 0 && (
        <div className="mb-8">
          <h3 className="text-lg font-semibold text-gray-900 mb-3">User Activity</h3>
          <div className="space-y-2">
            {newsItem.activities.map((activity) => (
              <div key={activity.id} className="flex items-center text-sm text-gray-600">
                <span className="capitalize">{activity.action.replace('_', ' ')}</span>
                <span className="mx-2">•</span>
                <span>{formatDate(activity.created_at)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center justify-between pt-8 border-t border-gray-200">
        <div className="flex items-center space-x-4">
          <a
            href={newsItem.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn-primary"
          >
            <ExternalLink className="h-4 w-4 mr-2" />
            Read Original Article
          </a>
          
          <Link to="/news" className="btn btn-outline">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to News
          </Link>
        </div>
        
        <div className="text-sm text-gray-500">
          Article ID: {newsItem.id}
        </div>
      </div>
    </div>
  )
}
