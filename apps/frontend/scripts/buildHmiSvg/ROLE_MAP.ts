// HMI SVG의 단일 진실 매핑.
// kind:
//   - 'kpi-card', 'kpi-box', 'flow-group', 'cascade-step', 'flame-anchor': data-role 부여
//   - 'kpi-value-remove': 빌드 시 element 제거 + bbox 추출 (KPI_ANCHORS export)

export const ROLE_MAP = {
  // KPI 카드 컨테이너 (4)
  'card-nox':       { id: 'metric_NOx',     kind: 'kpi-card' },
  'card-ttxm':      { id: 'target-TTXM',    kind: 'kpi-card' },
  'card-dwatt':     { id: 'target-DWATT',   kind: 'kpi-card' },
  'card-lambda':    { id: 'target-lambda',  kind: 'kpi-card' },

  // KPI 카드 box (glow 대상, 4)
  'card-box-nox':       { id: 'box_NOx',     kind: 'kpi-box' },
  'card-box-ttxm':      { id: 'box_TTXM',    kind: 'kpi-box' },
  'card-box-dwatt':     { id: 'box_DWATT',   kind: 'kpi-box' },
  'card-box-lambda':    { id: 'box_lambda',  kind: 'kpi-box' },

  // 동적 값 path (제거 대상, 4) → KPI_ANCHORS export
  'kpi-value-nox':      { id: '26.5',  kind: 'kpi-value-remove' },
  'kpi-value-ttxm':     { id: '580.0', kind: 'kpi-value-remove' },
  'kpi-value-dwatt':    { id: '248.6', kind: 'kpi-value-remove' },
  'kpi-value-lambda':   { id: '1.10',  kind: 'kpi-value-remove' },

  // flow 그룹 (4: 본 흐름 3 + 카드 연결선 1)
  'flow-fuel':  { id: 'flow_fuel_pink',  kind: 'flow-group' },
  'flow-nox':   { id: 'flow_nox_green',  kind: 'flow-group' },
  'flow-air':   { id: 'flow_air_blue',   kind: 'flow-group' },
  'flow-cards': { id: 'line_to_cards',   kind: 'flow-group' },

  // N2 cascade 박스 (3)
  'cascade-1':  { id: 'BOX_NQKR3_MONITOR', kind: 'cascade-step' },
  'cascade-2':  { id: 'BOX_nicvs1',        kind: 'cascade-step' },
  'cascade-3':  { id: 'BOX_NOJ',           kind: 'cascade-step' },

  // combustor (flame overlay 앵커)
  'combustor':  { id: 'COMBUSTOR', kind: 'flame-anchor' },
} as const

export type RoleKind = (typeof ROLE_MAP)[keyof typeof ROLE_MAP]['kind']
export type RoleName = keyof typeof ROLE_MAP
