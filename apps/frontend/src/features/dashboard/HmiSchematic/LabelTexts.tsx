import { KPI_ANCHORS } from './schematic-roles'
import styles from './HmiSchematic.module.css'

// 좌측 10개 박스 path의 중심 x — 박스 가운데 정렬용.
// 우측 4개(nox/ttxm/dwatt/lambda)는 KPI_ANCHORS의 좌측 정렬 좌표 그대로 사용한다.
const BOX_CENTER_X: Partial<Record<keyof typeof KPI_ANCHORS, number>> = {
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
        const centerX = BOX_CENTER_X[key]
        // 좌측 10개: 박스 중앙. 우측 4개: KPI_ANCHORS 좌측 정렬 좌표 그대로.
        const x = centerX ?? anchor.x
        const textAnchor = centerX !== undefined ? 'middle' : anchor.textAnchor
        return (
          <text
            key={key}
            x={x}
            y={anchor.y + LABEL_Y_OFFSET}
            textAnchor={textAnchor}
            data-role={`label-${key}`}
          >
            {text}
          </text>
        )
      })}
    </g>
  )
}
