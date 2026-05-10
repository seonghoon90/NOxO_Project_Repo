import styles from './HmiSchematic.module.css'

// 카드 좌측면 좌표에 맞춰 라벨 정렬
// 합성가스/질소 카드 left=31, 공기 카드(CSBHX) left=245
const LEGENDS = [
  { key: 'fuel', text: '합성가스 계통', color: '#FF6B8E', x: 31, y: 142 },
  { key: 'n2',   text: '질소 계통',     color: '#7EDB50', x: 31, y: 252 },
  { key: 'air',  text: '공기 계통',     color: '#2C9DFF', x: 88, y: 388 },
]

export function LegendTexts() {
  return (
    <g data-role="legend-texts" className={styles.legendTexts}>
      {LEGENDS.map(({ key, text, color, x, y }) => (
        <text
          key={key}
          x={x}
          y={y}
          textAnchor="start"
          fill={color}
          data-role={`legend-${key}`}
        >
          {text}
        </text>
      ))}
    </g>
  )
}
