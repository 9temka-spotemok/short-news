import type { ComparisonSeriesPoint } from '@/types'
import { useMemo } from 'react'

interface SeriesDescriptor {
  subjectKey: string
  label: string
  color: string
  points: ComparisonSeriesPoint[]
}

interface MultiImpactTrendChartProps {
  series: SeriesDescriptor[]
  height?: number
}

const MultiImpactTrendChart: React.FC<MultiImpactTrendChartProps> = ({ series, height = 220 }) => {
  const chart = useMemo(() => {
    if (!series.length) {
      return null
    }

    const uniqueDates = Array.from(
      new Set(
        series.flatMap(entry => entry.points.map(point => point.period_start))
      )
    ).sort((a, b) => new Date(a).getTime() - new Date(b).getTime())

    if (!uniqueDates.length) {
      return null
    }

    const dateIndex = new Map(uniqueDates.map((date, index) => [date, index]))
    const values = series.flatMap(entry => entry.points.map(point => point.impact_score))
    const minValue = Math.min(...values)
    const maxValue = Math.max(...values)
    const range = maxValue - minValue || 1

    const padding = {
      top: 10,
      bottom: 10,
      left: 10,
      right: 10
    }
    const viewBoxWidth = 100
    const usableWidth = viewBoxWidth - padding.left - padding.right
    const usableHeight = Math.max(height - padding.top - padding.bottom, 1)

    const buildPath = (points: ComparisonSeriesPoint[]) => {
      const orderedPoints = [...points].sort(
        (a, b) => new Date(a.period_start).getTime() - new Date(b.period_start).getTime()
      )
      const d = orderedPoints
        .map(point => {
          const index = dateIndex.get(point.period_start) ?? 0
          const ratio = uniqueDates.length > 1 ? index / (uniqueDates.length - 1) : 0
          const x = padding.left + usableWidth * ratio
          const normalized = (point.impact_score - minValue) / range
          const y = padding.top + (1 - normalized) * usableHeight
          return `${x.toFixed(2)},${y.toFixed(2)}`
        })
        .filter(Boolean)

      if (!d.length) {
        return ''
      }

      return `M${d[0]} L${d.slice(1).join(' L')}`
    }

    const plotPoints = (points: ComparisonSeriesPoint[]) => {
      return points.map(point => {
        const index = dateIndex.get(point.period_start) ?? 0
        const ratio = uniqueDates.length > 1 ? index / (uniqueDates.length - 1) : 0
        const x = padding.left + usableWidth * ratio
        const normalized = (point.impact_score - minValue) / range
        const y = padding.top + (1 - normalized) * usableHeight

        return { x, y, point }
      })
    }

    return {
      uniqueDates,
      padding,
      viewBoxWidth,
      height,
      buildPath,
      plotPoints,
      minValue,
      maxValue
    }
  }, [series, height])

  if (!chart) {
    return (
      <div className="rounded-lg border border-dashed border-gray-300 p-6 text-sm text-gray-500">
        Not enough data to render multi-series chart yet.
      </div>
    )
  }

  return (
    <div className="w-full max-w-full sm:max-w-[490px] md:max-w-[571px] mx-auto">
      <div className="w-full overflow-x-auto">
        <svg
          viewBox={`0 0 ${chart.viewBoxWidth} ${chart.height}`}
          preserveAspectRatio="xMidYMid meet"
          className="w-full min-w-[272px] sm:min-w-[340px] md:min-w-[408px]"
          role="img"
          aria-label="Impact score comparison chart"
        >
        <rect
          x={chart.padding.left}
          y={chart.padding.top}
          width={chart.viewBoxWidth - chart.padding.left - chart.padding.right}
          height={chart.height - chart.padding.top - chart.padding.bottom}
          fill="#f8fafc"
          stroke="#e2e8f0"
          strokeWidth={0.4}
          rx={1}
        />

        {chart.uniqueDates.map((date, index) => {
          if (chart.uniqueDates.length <= 1) return null
          const ratio = index / (chart.uniqueDates.length - 1)
          const x = chart.padding.left + (chart.viewBoxWidth - chart.padding.left - chart.padding.right) * ratio
          return (
            <line
              key={date}
              x1={x}
              x2={x}
              y1={chart.padding.top}
              y2={chart.height - chart.padding.bottom}
              stroke="#e2e8f0"
              strokeWidth={0.3}
            />
          )
        })}

        {series.map(entry => {
          const path = chart.buildPath(entry.points)
          if (!path) return null
          return (
            <path
              key={entry.subjectKey}
              d={path}
              fill="none"
              stroke={entry.color}
              strokeWidth={1.6}
              strokeLinecap="round"
              strokeLinejoin="round"
              opacity={0.9}
            />
          )
        })}

        {series.map(entry =>
          chart.plotPoints(entry.points).map(({ x, y }, idx) => (
            <circle
              key={`${entry.subjectKey}-${idx}`}
              cx={x}
              cy={y}
              r={0.9}
              fill={entry.color}
              opacity={0.95}
            />
          ))
        )}

        <text x={chart.padding.left} y={chart.padding.top - 4} fontSize={3} fill="#64748b">
          Impact score
        </text>
      </svg>
      </div>

      <div className="mt-3 flex flex-wrap gap-2 sm:gap-3 text-xs sm:text-sm">
        {series.map(entry => (
          <div key={entry.subjectKey} className="flex items-center gap-1.5 sm:gap-2">
            <span
              className="inline-block h-2 w-2 rounded-sm flex-shrink-0"
              style={{ backgroundColor: entry.color }}
              aria-hidden="true"
            />
            <span className="text-gray-700 truncate max-w-[120px] sm:max-w-none">{entry.label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

export type { SeriesDescriptor as MultiImpactSeriesDescriptor }
export default MultiImpactTrendChart

