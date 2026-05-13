import type { MetricPoint } from '../mockConsole'

// 카드 안 spark 영역 (산출 SVG 좌표 기준)
// 카드 우측 끝 1275. 좌측 라벨 padding ≈ 12px와 동일하게 우측 여백 확보 → spark 끝 1263
// 단위 path 우측 끝 ~1207 → spark 시작 1213으로 6px 여백
const SPARK_BOXES = {
  nox:    { x: 1213, y: 119, w: 50, h: 30, key: 'nox' as const },
  ttxm:   { x: 1213, y: 215, w: 50, h: 30, key: 'exhaust' as const },
  dwatt:  { x: 1213, y: 305, w: 50, h: 30, key: 'power' as const },
  lambda: { x: 1213, y: 390, w: 50, h: 30, key: 'lambda' as const },
}

export interface SparkLinesProps {
  history: ReadonlyArray<MetricPoint>
}

// 위/아래 각 4px 여백 — 그래프가 카드 상하변과 닿지 않도록
const PADDING_Y = 4

function buildPath(values: number[], box: { x: number; y: number; w: number; h: number }): string {
  if (values.length < 2) return ''
  const min = Math.min(...values)
  const max = Math.max(...values)
  const range = max - min || 1
  const dx = box.w / (values.length - 1)
  const innerH = box.h - PADDING_Y * 2
  const innerTop = box.y + PADDING_Y
  const points = values.map((v, i) => {
    const x = box.x + i * dx
    const y = innerTop + innerH - ((v - min) / range) * innerH
    return `${x.toFixed(1)},${y.toFixed(1)}`
  })
  return `M${points[0]} L${points.slice(1).join(' L')}`
}

export function SparkLines({ history }: SparkLinesProps) {
  if (history.length < 2) return null
  return (
    <g data-role="spark-lines">
      {(Object.entries(SPARK_BOXES) as Array<[keyof typeof SPARK_BOXES, typeof SPARK_BOXES[keyof typeof SPARK_BOXES]]>).map(([role, box]) => {
        const values = history.map((p) => p[box.key])
        return <path key={role} data-role={`spark-${role}`} d={buildPath(values, box)} />
      })}
    </g>
  )
}
