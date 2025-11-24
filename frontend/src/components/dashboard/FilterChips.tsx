import { X } from 'lucide-react'

interface FilterChip {
  id: string
  label: string
  onRemove: () => void
}

interface FilterChipsProps {
  filters: FilterChip[]
  onClearAll?: () => void
  className?: string
}

export default function FilterChips({ filters, onClearAll, className = '' }: FilterChipsProps) {
  if (filters.length === 0) return null

  return (
    <div className={`flex flex-wrap items-center gap-2 ${className}`}>
      {filters.map((filter) => (
        <span
          key={filter.id}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium bg-primary-100 text-primary-700 border border-primary-200"
        >
          <span>{filter.label}</span>
          <button
            onClick={filter.onRemove}
            className="hover:bg-primary-200 rounded-full p-0.5 transition-colors"
            aria-label={`Remove ${filter.label} filter`}
          >
            <X className="h-3 w-3" />
          </button>
        </span>
      ))}
      {onClearAll && filters.length > 1 && (
        <button
          onClick={onClearAll}
          className="text-sm text-gray-600 hover:text-gray-900 font-medium px-2 py-1"
        >
          Clear all
        </button>
      )}
    </div>
  )
}


