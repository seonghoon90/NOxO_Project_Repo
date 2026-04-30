export type Mode = 'sim' | 'pred'
export type VariableKey = 'syngas' | 'n2' | 'load'

export type VariableConfig = {
  key: VariableKey
  label: string
  shortLabel: string
  rawName: string
  unit: string
  digits: number
  step: number
  base: number
  min: number
  max: number
  value: number
}

export type MetricPoint = {
  label: string
  nox: number
  co: number
  flame: number
  lambda: number
  power: number
}

export type ConsoleMetrics = {
  nox: number
  co: number
  flame: number
  lambda: number
  power: number
  predictedNox: number
}

export type ConsoleState = {
  activeVar: VariableKey
  overlayVisible: boolean
  variables: Record<VariableKey, VariableConfig>
  metrics: ConsoleMetrics
  history: MetricPoint[]
}

export type VariableConfigUpdate = Pick<VariableConfig, 'min' | 'max' | 'step'>

export type BackendConsoleSnapshot = {
  sid?: string
  t?: number
  current?: Record<string, number>
  output?: Record<string, number>
  fuel?: number
  n2?: number
  load?: number
  syngas_flow?: number
  n2_offset?: number
  igv_opening?: number
  lambda?: number
  lambda_?: number
  exhaust_temp?: number
  nox?: number
  co?: number
  power?: number
  efficiency?: number
  predicted_nox?: number
  warning?: boolean
  [key: string]:
    | number
    | string
    | boolean
    | undefined
    | Record<string, number>
}

export const NOX_LIMIT = 50
export const HISTORY_LENGTH = 60
export const POWER_RAW_NAME = 'IGCC.CC.G1.DWATT'

export const variableSeed: Record<VariableKey, VariableConfig> = {
  syngas: {
    key: 'syngas',
    label: '합성가스 유량',
    shortLabel: '합성가스',
    rawName: 'IGCC.CC.G1.ca_fqsg_cl',
    unit: 'raw',
    digits: 1,
    step: 20,
    base: 1500,
    min: 800,
    max: 2200,
    value: 1500,
  },
  n2: {
    key: 'n2',
    label: '질소가스 주입 오프셋',
    shortLabel: '질소오프셋',
    rawName: 'IGCC.CC.G1.NQKR3_MONITOR',
    unit: 'raw',
    digits: 1,
    step: 10,
    base: 200,
    min: 0,
    max: 500,
    value: 200,
  },
  load: {
    key: 'load',
    label: 'IGV 개도',
    shortLabel: 'IGV',
    rawName: 'IGCC.CC.G1.csgv',
    unit: '%',
    digits: 1,
    step: 1,
    base: 75,
    min: 30,
    max: 100,
    value: 75,
  },
}

export function createInitialConsoleState(seedHistory = false): ConsoleState {
  const variables = cloneVariableSeed()
  const metrics = deriveMetrics(variables, 'sim', 0)

  // 백엔드 연결 모드에서는 빈 history로 시작 — 실데이터로만 채워지도록.
  // mock fallback 모드에서만 seed history를 채워 차트가 첫 렌더부터 자연스럽게 보이게 한다.
  const history: MetricPoint[] = seedHistory
    ? Array.from({ length: HISTORY_LENGTH }, (_, index) => {
        const point = deriveMetrics(variables, 'sim', index * 0.14)
        return {
          label: `${HISTORY_LENGTH - index}s`,
          nox: point.nox,
          co: point.co,
          flame: point.flame,
          lambda: point.lambda,
          power: point.power,
        }
      })
    : []

  return {
    activeVar: 'syngas',
    overlayVisible: true,
    variables,
    metrics,
    history,
  }
}

export function cloneVariableSeed() {
  return structuredClone(variableSeed)
}

export function createStateFromSnapshot(
  snapshot: BackendConsoleSnapshot,
  previous?: ConsoleState,
): ConsoleState {
  const controlSource = snapshot.current ?? snapshot
  const outputSource = snapshot.output ?? snapshot
  const variables = previous ? structuredClone(previous.variables) : cloneVariableSeed()
  variables.syngas.value = pickSnapshotValue(controlSource, [
    'syngas_flow',
    'fuel',
    variableSeed.syngas.rawName,
  ], variables.syngas.value, variables.syngas.digits)
  variables.n2.value = pickSnapshotValue(controlSource, [
    'n2_offset',
    'n2',
    variableSeed.n2.rawName,
  ], variables.n2.value, variables.n2.digits)
  variables.load.value = pickSnapshotValue(controlSource, [
    'igv_opening',
    'load',
    variableSeed.load.rawName,
  ], variables.load.value, variables.load.digits)

  const metrics = {
    nox: pickSnapshotValue(outputSource, ['nox'], previous?.metrics.nox ?? 25, 1),
    co: pickSnapshotValue(outputSource, ['co'], previous?.metrics.co ?? 12, 1),
    flame: pickSnapshotValue(outputSource, ['exhaust_temp'], previous?.metrics.flame ?? 580, 1),
    lambda: pickSnapshotValue(outputSource, ['lambda', 'lambda_'], previous?.metrics.lambda ?? 1.1, 2),
    // 백엔드 stream/snapshot은 'power' 키 사용 (단위: MW, 태그: IGCC.CC.G1.DWATT).
    // 향후 raw 태그 키로 직송될 가능성 대비해 POWER_RAW_NAME도 fallback에 포함.
    power: pickSnapshotValue(
      outputSource,
      ['power', POWER_RAW_NAME],
      previous?.metrics.power ?? 248.6,
      1,
    ),
    predictedNox: pickSnapshotValue(
      outputSource,
      ['predicted_nox'],
      previous?.metrics.predictedNox ?? (previous?.metrics.nox ?? 25) + 6,
      1,
    ),
  }

  return {
    activeVar: previous?.activeVar ?? 'syngas',
    overlayVisible: previous?.overlayVisible ?? true,
    variables,
    metrics,
    history: previous?.history ?? [],
  }
}

/**
 * 백엔드 미연결(WS 실패 등) 시 fallback 전용 mock 시뮬레이터.
 * 정상 운영에서는 createStateFromSnapshot이 백엔드 stream/snapshot에서 받은 값을
 * 그대로 사용하며, 본 함수는 호출되지 않는다.
 *
 * 식은 backend의 StubPredictor와 동일하게 맞춰 fallback 전환 시 값 점프를 최소화한다.
 */
export function deriveMetrics(
  variables: Record<VariableKey, VariableConfig>,
  mode: Mode,
  tick: number,
): ConsoleMetrics {
  const syngas = variables.syngas.value
  const n2 = variables.n2.value
  const load = variables.load.value

  const lambda = clamp(
    1.1 * (Math.max(load, 1) / 75) / (Math.max(syngas, 1) / 1500) + (n2 - 200) * 0.0005,
    0.5,
    1.5,
  )
  const flameBase = Math.max(
    900,
    1450 + (syngas - 1500) * 0.24 + (load - 75) * 2.4 - (n2 - 200) * 0.3,
  )
  const flame = flameBase + Math.sin(tick * 0.22) * 1.8
  const noxBase =
    25 * Math.exp((flameBase - 1450) / 120) * (1 + 0.6 * Math.max(0, lambda - 1))
  const nox = noxBase + Math.sin(tick * 0.16) * 0.8
  const coBase = 12 + 80 * (lambda - 1) ** 2
  const co = coBase + Math.sin(tick * 0.25) * 0.4
  // backend StubPredictor._power와 동일한 식 — fallback 전환 시 점프 방지용
  const powerBase = 248.6 + (syngas - 1500) * 0.045 + (load - 75) * 1.35 - (n2 - 200) * 0.08
  const power = Math.max(0, powerBase + Math.sin(tick * 0.18) * 1.2)
  const predictedNox = nox + 6 + (mode === 'pred' ? 4 : 0)

  return {
    nox: round(nox, 1),
    co: round(co, 1),
    flame: round(flame, 1),
    lambda: round(lambda, 2),
    power: round(power, 1),
    predictedNox: round(predictedNox, 1),
  }
}

export function applyVariableStep(
  state: ConsoleState,
  direction: 1 | -1,
  mode: Mode,
  tick: number,
) {
  const active = state.variables[state.activeVar]
  const nextValue = clamp(
    active.value + active.step * direction,
    active.min,
    active.max,
  )

  const variables = {
    ...state.variables,
    [state.activeVar]: {
      ...active,
      value: round(nextValue, active.digits),
    },
  }
  const metrics = deriveMetrics(variables, mode, tick)

  return {
    ...state,
    variables,
    metrics,
  }
}

export function appendHistory(
  history: MetricPoint[],
  metrics: ConsoleMetrics,
  index: number,
) {
  const next = [
    ...history.slice(-HISTORY_LENGTH + 1),
    {
      label: index === 0 ? 'now' : `${index}s`,
      nox: metrics.nox,
      co: metrics.co,
      flame: metrics.flame,
      lambda: metrics.lambda,
      power: metrics.power,
    },
  ]

  return next
}

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value))
}

function round(value: number, digits: number) {
  const factor = 10 ** digits
  return Math.round(value * factor) / factor
}

function pickSnapshotValue(
  snapshot: BackendConsoleSnapshot,
  keys: string[],
  fallback: number,
  digits: number,
) {
  for (const key of keys) {
    const raw = snapshot[key]
    if (typeof raw === 'number' && Number.isFinite(raw)) {
      return round(raw, digits)
    }
  }

  return fallback
}
