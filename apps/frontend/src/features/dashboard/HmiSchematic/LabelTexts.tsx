import { KPI_ANCHORS } from './schematic-roles'
import styles from './HmiSchematic.module.css'

// 박스 path 중심 x 좌표 — schematic.svg의 각 BOX/target 그룹 외곽 path에서 추출.
// 라벨은 박스 중앙에 정렬돼야 자연스러워, KPI_ANCHORS의 숫자값 x(좌측 정렬용)는 무시하고 별도 dict 사용.
const BOX_CENTER_X: Record<keyof typeof KPI_ANCHORS, number> = {
  syngas: 92.5,
  csgv: 453.5,
  nqkr3: 92.5,
  nicvs1: 269.5,
  fsagr: 260.5,
  fsag11: 514.5,
  fsag11a: 630.5,
  fsag12: 746.5,
  csbhx: 277.5,
  nqj: 479.5,
  nox: 1194.5,
  ttxm: 1194.5,
  dwatt: 1194.5,
  lambda: 1194.5,
  'legend-fuel': 0,
  'legend-n2': 0,
  'legend-air': 0,
}

// KPI_ANCHORS의 숫자값 y에서 라벨 위치는 -20px 위쪽
const LABEL_Y_OFFSET = -20

const LABELS: ReadonlyArray<{ key: keyof typeof KPI_ANCHORS; text: string }> = [
  { key: 'syngas', text: '합성가스 유량' },
  { key: 'csgv', text: 'IGV 개도' },
  { key: 'nqkr3', text: '질소 오프셋' },
  { key: 'nicvs1', text: 'N2 제어밸브 #1' },
  { key: 'fsagr', text: 'Syngas SRV' },
  { key: 'fsag11', text: 'Syngas GCV #1' },
  { key: 'fsag11a', text: 'Syngas GCV #1A' },
  { key: 'fsag12', text: 'Syngas GCV #2' },
  { key: 'csbhx', text: 'IBH 가열밸브' },
  { key: 'nqj', text: 'N2 주입 유량' },
  { key: 'nox', text: 'NOx' },
  { key: 'ttxm', text: '배기온도' },
  { key: 'dwatt', text: '발전량' },
  { key: 'lambda', text: '공기비' },
]

export function LabelTexts() {
  return (
    <g data-role="label-texts" className={styles.labelTexts}>
      {LABELS.map(({ key, text }) => {
        const anchor = KPI_ANCHORS[key]
        const cx = BOX_CENTER_X[key]
        return (
          <text
            key={key}
            x={cx}
            y={anchor.y + LABEL_Y_OFFSET}
            textAnchor="middle"
            data-role={`label-${key}`}
          >
            {text}
          </text>
        )
      })}
    </g>
  )
}
