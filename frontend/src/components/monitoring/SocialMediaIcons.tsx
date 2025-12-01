import type { SocialMediaSources } from '@/types'
import { Facebook, Instagram, Linkedin, Music, Twitter, Youtube } from 'lucide-react'

interface SocialMediaIconsProps {
  sources: SocialMediaSources
  className?: string
}

const socialMediaConfig = {
  facebook: {
    icon: Facebook,
    label: 'Facebook',
    color: 'text-blue-600 hover:text-blue-700'
  },
  instagram: {
    icon: Instagram,
    label: 'Instagram',
    color: 'text-pink-600 hover:text-pink-700'
  },
  linkedin: {
    icon: Linkedin,
    label: 'LinkedIn',
    color: 'text-blue-700 hover:text-blue-800'
  },
  youtube: {
    icon: Youtube,
    label: 'YouTube',
    color: 'text-red-600 hover:text-red-700'
  },
  tiktok: {
    icon: Music,
    label: 'TikTok',
    color: 'text-black hover:text-gray-800'
  },
  twitter: {
    icon: Twitter,
    label: 'Twitter/X',
    color: 'text-blue-400 hover:text-blue-500'
  }
}

export default function SocialMediaIcons({ sources, className = '' }: SocialMediaIconsProps) {
  const availableSources = Object.entries(sources).filter(
    ([_, data]) => data && data.url
  )

  if (availableSources.length === 0) {
    return (
      <div className={`text-sm text-gray-500 ${className}`}>
        Нет доступных соцсетей
      </div>
    )
  }

  return (
    <div className={`flex flex-wrap gap-2 ${className}`}>
      {availableSources.map(([platform, data]) => {
        const config = socialMediaConfig[platform as keyof typeof socialMediaConfig]
        if (!config || !data?.url) return null

        const Icon = config.icon
        return (
          <a
            key={platform}
            href={data.url}
            target="_blank"
            rel="noopener noreferrer"
            className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-md transition-colors ${config.color} bg-gray-50 hover:bg-gray-100`}
            title={config.label}
          >
            <Icon className="w-4 h-4" />
            <span className="text-xs font-medium">{config.label}</span>
          </a>
        )
      })}
    </div>
  )
}




