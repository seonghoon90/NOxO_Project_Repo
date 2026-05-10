import { KPI_ANCHORS } from './schematic-roles'
import { formatKpi } from './numericHelpers'
import styles from './HmiSchematic.module.css'

export interface KpiTextsProps {
  // 메인 KPI 4
  nox: number
  ttxm: number
  dwatt: number
  lambda: number
  // 보조 카드 9
  syngas: number
  fsagr: number
  fsag11: number
  fsag11a: number
  fsag12: number
  nicvs1: number
  nqj: number
  csbhx: number
  csgv: number
  nqkr3: number
}

type AnchorKey = keyof typeof KPI_ANCHORS

const ITEMS: ReadonlyArray<{ key: AnchorKey; digits: number }> = [
  { key: 'nox', digits: 1 },
  { key: 'ttxm', digits: 1 },
  { key: 'dwatt', digits: 1 },
  { key: 'lambda', digits: 2 },
  { key: 'syngas', digits: 1 },
  { key: 'fsagr', digits: 1 },
  { key: 'fsag11', digits: 1 },
  { key: 'fsag11a', digits: 1 },
  { key: 'fsag12', digits: 1 },
  { key: 'nicvs1', digits: 1 },
  { key: 'nqj', digits: 1 },
  { key: 'csbhx', digits: 1 },
  { key: 'csgv', digits: 1 },
  { key: 'nqkr3', digits: 1 },
]

export function KpiTexts(props: KpiTextsProps) {
  return (
    <g data-role="kpi-texts" className={styles.kpiTexts}>
      {ITEMS.map(({ key, digits }) => {
        const anchor = KPI_ANCHORS[key]
        return (
          <text
            key={key}
            x={anchor.x}
            y={anchor.y}
            textAnchor={anchor.textAnchor}
            data-role={`kpi-text-${key}`}
          >
            {formatKpi(props[key], digits)}
          </text>
        )
      })}
    </g>
  )
}
