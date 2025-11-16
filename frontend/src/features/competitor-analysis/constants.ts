export type FilterOption = {
  value: string
  label: string
}

export const SOURCE_TYPE_OPTIONS: FilterOption[] = [
  { value: 'blog', label: 'Blog' },
  { value: 'news_site', label: 'News Site' },
  { value: 'press_release', label: 'Press Release' },
  { value: 'twitter', label: 'Twitter/X' },
  { value: 'github', label: 'GitHub' },
  { value: 'reddit', label: 'Reddit' }
]

export const SENTIMENT_OPTIONS: FilterOption[] = [
  { value: 'positive', label: 'Positive' },
  { value: 'neutral', label: 'Neutral' },
  { value: 'negative', label: 'Negative' },
  { value: 'mixed', label: 'Mixed' }
]

export const TOPIC_OPTIONS: FilterOption[] = [
  { value: 'product', label: 'Product & Launches' },
  { value: 'strategy', label: 'Strategy' },
  { value: 'finance', label: 'Finance' },
  { value: 'technology', label: 'Technology' },
  { value: 'security', label: 'Security' },
  { value: 'research', label: 'Research' },
  { value: 'community', label: 'Community' },
  { value: 'talent', label: 'Talent' },
  { value: 'regulation', label: 'Regulation' },
  { value: 'market', label: 'Market' },
  { value: 'other', label: 'Other' }
]












