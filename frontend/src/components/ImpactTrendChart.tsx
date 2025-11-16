import { useMemo, useState } from 'react'
import type { CompanyAnalyticsSnapshot } from '../types'

interface ImpactTrendChartProps {
  snapshots: CompanyAnalyticsSnapshot[]
  height?: number
  onPointHover?: (snapshot: CompanyAnalyticsSnapshot | null, index: number | null) => void
}

type ChartPoint = {
  snapshot: CompanyAnalyticsSnapshot
  x: number
  y: number
  score: number
}

const ImpactTrendChart = ({ snapshots, height = 200, onPointHover }: ImpactTrendChartProps) => {
  const [activeIndex, setActiveIndex] = useState<number | null>(null)

  const {
    points,
    linePath,
    areaPath,
    minScore,
    maxScore,
    firstLabel,
    lastLabel,
    paddingTop,
    paddingBottom,
    paddingLeft,
    paddingRight,
    viewBoxWidth
  } = useMemo(() => {
    const paddingTop = 10
    const paddingBottom = 10
    const paddingLeft = 8
    const paddingRight = 8
    const viewBoxWidth = 100
    const usableHeight = Math.max(height - paddingTop - paddingBottom, 1)
    const usableWidth = viewBoxWidth - paddingLeft - paddingRight
    const scores = snapshots.map(snapshot => snapshot.impact_score ?? 0)
    const minScore = scores.length ? Math.min(...scores) : 0
    const maxScore = scores.length ? Math.max(...scores) : 0
    const range = maxScore - minScore || 1
    const dateFormatter = new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric' })

    const points: ChartPoint[] = snapshots.map((snapshot, index) => {
      const ratio = snapshots.length > 1 ? index / (snapshots.length - 1) : 0
      const x = paddingLeft + usableWidth * ratio
      const normalized = (snapshot.impact_score - minScore) / range
      const y = paddingTop + (1 - normalized) * usableHeight
      return { snapshot, x, y, score: snapshot.impact_score }
    })

    const linePath = points
      .map((point, index) => `${index === 0 ? 'M' : 'L'}${point.x.toFixed(2)},${point.y.toFixed(2)}`)
      .join(' ')

    const areaPath =
      points.length > 0
        ? [
            `M${points[0].x.toFixed(2)},${(height - paddingBottom).toFixed(2)}`,
            ...points.map(point => `L${point.x.toFixed(2)},${point.y.toFixed(2)}`),
            `L${points[points.length - 1].x.toFixed(2)},${(height - paddingBottom).toFixed(2)}`,
            'Z'
          ].join(' ')
        : ''

    return {
      points,
      linePath,
      areaPath,
      minScore,
      maxScore,
      firstLabel:
        snapshots[0]?.period_start ? dateFormatter.format(new Date(snapshots[0].period_start)) : '',
      lastLabel:
        snapshots[snapshots.length - 1]?.period_start
          ? dateFormatter.format(new Date(snapshots[snapshots.length - 1].period_start))
          : '',
      paddingTop,
      paddingBottom,
      paddingLeft,
      paddingRight,
      viewBoxWidth
    }
  }, [snapshots, height])

  const activePoint = activeIndex !== null ? points[activeIndex] : null

  return (
    <div className="relative w-full max-w-full sm:max-w-[490px] md:max-w-[571px] mx-auto">
      <svg
        role="img"
        aria-label="Impact score trend"
        viewBox={`0 0 ${viewBoxWidth} ${height}`}
        preserveAspectRatio="xMidYMid meet"
        className="w-full"
        onMouseLeave={() => {
          setActiveIndex(null)
          onPointHover?.(null, null)
        }}
      >
        <defs>
          <linearGradient id="impactAreaGradient" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="#2563eb" stopOpacity="0.25" />
            <stop offset="100%" stopColor="#2563eb" stopOpacity="0" />
          </linearGradient>
          <linearGradient id="impactLineGradient" x1="0" x2="1" y1="0" y2="0">
            <stop offset="0%" stopColor="#60a5fa" />
            <stop offset="100%" stopColor="#2563eb" />
          </linearGradient>
        </defs>

        <rect
          x={paddingLeft}
          y={paddingTop}
          width={viewBoxWidth - paddingLeft - paddingRight}
          height={height - paddingTop - paddingBottom}
          fill="url(#impactAreaGradient)"
          opacity={0.3}
        />

        {points.length > 0 && (
          <>
            <path
              d={areaPath}
              fill="url(#impactAreaGradient)"
              stroke="none"
              opacity={0.6}
            />
            <path
              d={linePath}
              fill="none"
              stroke="url(#impactLineGradient)"
              strokeWidth={1.8}
              strokeLinejoin="round"
              strokeLinecap="round"
            />
          </>
        )}

        {points.length > 0 && (
          <>
            <line
              x1={points[0].x}
              y1={height - paddingBottom}
              x2={points[points.length - 1].x}
              y2={height - paddingBottom}
              stroke="#d1d5db"
              strokeDasharray="4 4"
              strokeWidth={0.5}
            />
            <line
              x1={points[0].x}
              y1={paddingTop}
              x2={points[points.length - 1].x}
              y2={paddingTop}
              stroke="#e5e7eb"
              strokeDasharray="2 4"
              strokeWidth={0.5}
              opacity={0.5}
            />
          </>
        )}

        {points.map((point, index) => (
          <g key={point.snapshot.id}>
            {activeIndex === index && (
              <line
                x1={point.x}
                y1={paddingTop}
                x2={point.x}
                y2={height - paddingBottom}
                stroke="#1d4ed8"
                strokeWidth={0.6}
                strokeDasharray="3 3"
              />
            )}
            <circle
              cx={point.x}
              cy={point.y}
              r={activeIndex === index ? 1.8 : 1}
              fill={activeIndex === index ? '#1d4ed8' : '#60a5fa'}
              className="cursor-pointer transition-all duration-150"
              onMouseEnter={() => {
                setActiveIndex(index)
                onPointHover?.(point.snapshot, index)
              }}
            />
          </g>
        ))}
      </svg>

      {activePoint && (
        <div
          className="absolute z-[1] flex -translate-x-1/2 -translate-y-3 flex-col items-center rounded-md bg-white px-2 py-1 text-xs shadow-md ring-1 ring-blue-100"
          style={{
            left: `${(activePoint.x / viewBoxWidth) * 100}%`,
            top: `${((activePoint.y - 10) / height) * 100}%`
          }}
        >
          <span className="font-semibold text-gray-800">{activePoint.score.toFixed(2)}</span>
          <span className="text-[10px] text-gray-500">
            {new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric' }).format(
              new Date(activePoint.snapshot.period_start)
            )}
          </span>
        </div>
      )}

      {points.length > 0 && (
        <div className="mt-2 flex items-center justify-between text-[11px] text-gray-500">
          <div>
            <span>Lowest</span>
            <span className="ml-2 font-medium text-gray-700">{minScore.toFixed(2)}</span>
          </div>
          <div className="uppercase tracking-wide text-[10px] text-gray-400">
            {firstLabel} — {lastLabel}
          </div>
          <div>
            <span>Highest</span>
            <span className="ml-2 font-medium text-gray-700">{maxScore.toFixed(2)}</span>
          </div>
        </div>
      )}
    </div>
  )
}

export default ImpactTrendChart

