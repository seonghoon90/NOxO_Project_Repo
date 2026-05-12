export type Mode = 'sim' | 'realtime'
export type VariableKey =
  | 'syngasFlow'
  | 'igvOpening'
  | 'n2Offset'
  | 'n2Valve1'
  | 'syngasSrv'
  | 'syngasGcv1'
  | 'syngasGcv1a'
  | 'syngasGcv2'
  | 'ibhValve'
  | 'n2Flow'

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
  exhaust: number
  lambda: number
  power: number
  efficiency: number
}

export type ConsoleMetrics = {
  nox: number
  exhaust: number
  lambda: number
  power: number
  efficiency: number
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
  n2_valve_1?: number
  syngas_srv?: number
  syngas_gcv_1?: number
  syngas_gcv_1a?: number
  syngas_gcv_2?: number
  ibh_valve?: number
  n2_flow?: number
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
export const CONTROL_VARIABLE_KEYS: VariableKey[] = [
  'syngasFlow',
  'igvOpening',
  'n2Offset',
  'n2Valve1',
  'syngasSrv',
  'syngasGcv1',
  'syngasGcv1a',
  'syngasGcv2',
  'ibhValve',
  'n2Flow',
]
export const variableSeed: Record<VariableKey, VariableConfig> = {
  syngasFlow: {
    key: 'syngasFlow',
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
  igvOpening: {
    key: 'igvOpening',
    label: 'IGV 개도',
    shortLabel: 'IGV',
    rawName: 'IGCC.CC.G1.csgv',
    unit: '°',
    digits: 1,
    step: 1,
    base: 75,
    min: 30,
    max: 100,
    value: 75,
  },
  n2Offset: {
    key: 'n2Offset',
    label: '질소 오프셋',
    shortLabel: 'N2 오프셋',
    rawName: 'IGCC.CC.G1.NQKR3_MONITOR',
    unit: 'raw',
    digits: 1,
    step: 10,
    base: 200,
    min: 0,
    max: 500,
    value: 200,
  },
  n2Valve1: {
    key: 'n2Valve1',
    label: 'N2 제어밸브 #1',
    shortLabel: 'NICVS1',
    rawName: 'IGCC.CC.G1.nicvs1',
    unit: '%',
    digits: 1,
    step: 1,
    base: 28.4,
    min: 0,
    max: 100,
    value: 28.4,
  },
  syngasSrv: {
    key: 'syngasSrv',
    label: 'Syngas SRV',
    shortLabel: 'FSAGR',
    rawName: 'IGCC.CC.G1.FSAGR',
    unit: '%',
    digits: 1,
    step: 1,
    base: 39.3,
    min: 0,
    max: 100,
    value: 39.3,
  },
  syngasGcv1: {
    key: 'syngasGcv1',
    label: 'Syngas GCV #1',
    shortLabel: 'FSAG11',
    rawName: 'IGCC.CC.G1.FSAG11',
    unit: '%',
    digits: 1,
    step: 1,
    base: 28.4,
    min: 0,
    max: 100,
    value: 28.4,
  },
  syngasGcv1a: {
    key: 'syngasGcv1a',
    label: 'Syngas GCV #1A',
    shortLabel: 'FSAG11A',
    rawName: 'IGCC.CC.G1.FSAG11A',
    unit: '%',
    digits: 1,
    step: 1,
    base: 45.9,
    min: 0,
    max: 100,
    value: 45.9,
  },
  syngasGcv2: {
    key: 'syngasGcv2',
    label: 'Syngas GCV #2',
    shortLabel: 'FSAG12',
    rawName: 'IGCC.CC.G1.FSAG12',
    unit: '%',
    digits: 1,
    step: 1,
    base: 15.0,
    min: 0,
    max: 100,
    value: 15.0,
  },
  ibhValve: {
    key: 'ibhValve',
    label: 'IBH 가열밸브',
    shortLabel: 'CSBHX',
    rawName: 'IGCC.CC.G1.CSBHX',
    unit: '%',
    digits: 1,
    step: 1,
    base: 25.0,
    min: 0,
    max: 100,
    value: 25.0,
  },
  n2Flow: {
    key: 'n2Flow',
    label: 'N2 주입 유량',
    shortLabel: 'NQJ',
    rawName: 'IGCC.CC.G1.NQJ',
    unit: 'kg/s',
    digits: 1,
    step: 0.5,
    base: 30.6,
    min: 0,
    max: 60,
    value: 30.6,
  },
}

export function createInitialConsoleState(seedHistory = false): ConsoleState {
  const variables = cloneVariableSeed()
  const metrics = deriveMetrics(variables, 'sim', 0)
  const history: MetricPoint[] = seedHistory
    ? Array.from({ length: HISTORY_LENGTH }, (_, index) => {
        const point = deriveMetrics(variables, 'sim', index * 0.14)
        return {
          label: `${HISTORY_LENGTH - index}s`,
          nox: point.nox,
          exhaust: point.exhaust,
          lambda: point.lambda,
          power: point.power,
          efficiency: point.efficiency,
        }
      })
    : []

  return {
    activeVar: 'syngasFlow',
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

  variables.syngasFlow.value = pickSnapshotValue(
    controlSource,
    ['syngas_flow', 'fuel', variableSeed.syngasFlow.rawName],
    variables.syngasFlow.value,
    variables.syngasFlow.digits,
  )
  variables.igvOpening.value = pickSnapshotValue(
    controlSource,
    ['igv_opening', 'load', variableSeed.igvOpening.rawName],
    variables.igvOpening.value,
    variables.igvOpening.digits,
  )
  variables.n2Offset.value = pickSnapshotValue(
    controlSource,
    ['n2_offset', 'n2', variableSeed.n2Offset.rawName],
    variables.n2Offset.value,
    variables.n2Offset.digits,
  )
  variables.n2Valve1.value = pickSnapshotValue(
    controlSource,
    ['n2_valve_1', 'nicvs1', variableSeed.n2Valve1.rawName],
    variables.n2Valve1.value,
    variables.n2Valve1.digits,
  )
  variables.syngasSrv.value = pickSnapshotValue(
    controlSource,
    ['syngas_srv', 'fsagr', variableSeed.syngasSrv.rawName],
    variables.syngasSrv.value,
    variables.syngasSrv.digits,
  )
  variables.syngasGcv1.value = pickSnapshotValue(
    controlSource,
    ['syngas_gcv_1', 'fsag11', variableSeed.syngasGcv1.rawName],
    variables.syngasGcv1.value,
    variables.syngasGcv1.digits,
  )
  variables.syngasGcv1a.value = pickSnapshotValue(
    controlSource,
    ['syngas_gcv_1a', 'fsag11a', variableSeed.syngasGcv1a.rawName],
    variables.syngasGcv1a.value,
    variables.syngasGcv1a.digits,
  )
  variables.syngasGcv2.value = pickSnapshotValue(
    controlSource,
    ['syngas_gcv_2', 'fsag12', variableSeed.syngasGcv2.rawName],
    variables.syngasGcv2.value,
    variables.syngasGcv2.digits,
  )
  variables.ibhValve.value = pickSnapshotValue(
    controlSource,
    ['ibh_valve', 'csbhx', variableSeed.ibhValve.rawName],
    variables.ibhValve.value,
    variables.ibhValve.digits,
  )
  variables.n2Flow.value = pickSnapshotValue(
    controlSource,
    ['n2_flow', 'nqj', variableSeed.n2Flow.rawName],
    variables.n2Flow.value,
    variables.n2Flow.digits,
  )

  const metrics = {
    nox: pickSnapshotValue(outputSource, ['nox'], previous?.metrics.nox ?? 25, 1),
    exhaust: pickSnapshotValue(outputSource, ['exhaust_temp'], previous?.metrics.exhaust ?? 580, 1),
    lambda: pickSnapshotValue(outputSource, ['lambda', 'lambda_'], previous?.metrics.lambda ?? 1.1, 2),
    power: pickSnapshotValue(outputSource, ['power', POWER_RAW_NAME], previous?.metrics.power ?? 248.6, 1),
    efficiency: pickSnapshotValue(
      outputSource,
      ['efficiency'],
      previous?.metrics.efficiency ?? 0.89,
      3,
    ),
    predictedNox: pickSnapshotValue(
      outputSource,
      ['predicted_nox'],
      previous?.metrics.predictedNox ?? (previous?.metrics.nox ?? 25) + 6,
      1,
    ),
  }

  return {
    activeVar: previous?.activeVar ?? 'syngasFlow',
    overlayVisible: previous?.overlayVisible ?? true,
    variables,
    metrics,
    history: previous?.history ?? [],
  }
}

export function deriveMetrics(
  variables: Record<VariableKey, VariableConfig>,
  mode: Mode,
  tick: number,
): ConsoleMetrics {
  const syngas = variables.syngasFlow.value
  const igv = variables.igvOpening.value
  const n2Offset = variables.n2Offset.value
  const n2Valve = variables.n2Valve1.value
  const syngasSrv = variables.syngasSrv.value
  const syngasGcv1 = variables.syngasGcv1.value
  const syngasGcv1a = variables.syngasGcv1a.value
  const syngasGcv2 = variables.syngasGcv2.value
  const ibhValve = variables.ibhValve.value
  const n2Flow = variables.n2Flow.value

  const syngasValveAvg = (syngasSrv + syngasGcv1 + syngasGcv1a + syngasGcv2) / 4 / 100
  const n2Assist = clamp((n2Valve / 100) * 0.45 + (n2Flow / 60) * 0.55, 0, 1)
  const ibhHeat = clamp(ibhValve / 100, 0, 1)

  const lambda = clamp(
    1.08 * (Math.max(igv, 1) / 75) / (Math.max(syngas, 1) / 1500)
      + (n2Offset - 200) * 0.0005
      + n2Assist * 0.08,
    0.5,
    1.5,
  )
  const exhaustBase = Math.max(
    400,
    560
      + (syngas - 1500) * 0.022
      + syngasValveAvg * 18
      + (igv - 75) * 0.22
      + ibhHeat * 10
      - n2Assist * 18,
  )
  const exhaust = exhaustBase + Math.sin(tick * 0.22) * 0.8
  const noxBase =
    21
    * Math.exp((exhaustBase - 560) / 16)
    * (1 + 0.7 * Math.max(0, lambda - 1))
    * (1 + syngasValveAvg * 0.18 - n2Assist * 0.08)
  const nox = noxBase + Math.sin(tick * 0.16) * 0.8
  const powerBase =
    244
    + (syngas - 1500) * 0.04
    + (igv - 75) * 1.2
    + syngasValveAvg * 5
    - n2Assist * 2
  const power = Math.max(0, powerBase + Math.sin(tick * 0.18) * 1.2)
  const efficiency = clamp(
    0.89 - Math.abs(lambda - 1.1) * 0.05 - Math.abs(syngas - 1500) / 1500 * 0.02,
    0,
    1,
  )
  const predictedNox = nox + 6 + (mode === 'realtime' ? 4 : 0)

  return {
    nox: round(nox, 1),
    exhaust: round(exhaust, 1),
    lambda: round(lambda, 2),
    power: round(power, 1),
    efficiency: round(efficiency, 3),
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
  const nextValue = clamp(active.value + active.step * direction, active.min, active.max)
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
  return [
    ...history.slice(-HISTORY_LENGTH + 1),
    {
      label: index === 0 ? 'now' : `${index}s`,
      nox: metrics.nox,
      exhaust: metrics.exhaust,
      lambda: metrics.lambda,
      power: metrics.power,
      efficiency: metrics.efficiency,
    },
  ]
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

export type RealtimeStreamPayload = {
  v: 1
  sid: string
  tick: number
  ts: string
  mode: Mode
  override_active: boolean
  current: {
    controls: {
      syngas_flow: number
      igv_opening: number
      n2_offset: number
      n2_valve_1: number
      syngas_srv: number
      syngas_gcv_1: number
      syngas_gcv_1a: number
      syngas_gcv_2: number
      ibh_valve: number
      n2_flow: number
    }
    outputs: {
      nox: number
      exhaust_temp: number
      power: number
      lambda_: number
      efficiency: number
    }
  }
  kafka_latest: {
    controls: RealtimeStreamPayload['current']['controls']
    ts: string
  } | null
  forecast: {
    predicted_nox: number
    target_time: string
    threshold_value: number
    threshold_exceeded: boolean
  } | null
  warning: string | null
}

// VariableKey(camelCase) → backend payload.current.controls 키(snake_case) 매핑
export const VARIABLE_KEY_TO_DOMAIN: Record<VariableKey, string> = {
  syngasFlow: 'syngas_flow',
  igvOpening: 'igv_opening',
  n2Offset: 'n2_offset',
  n2Valve1: 'n2_valve_1',
  syngasSrv: 'syngas_srv',
  syngasGcv1: 'syngas_gcv_1',
  syngasGcv1a: 'syngas_gcv_1a',
  syngasGcv2: 'syngas_gcv_2',
  ibhValve: 'ibh_valve',
  n2Flow: 'n2_flow',
}

export function safeParseRealtimePayload(raw: string): RealtimeStreamPayload | null {
  try {
    const parsed = JSON.parse(raw) as RealtimeStreamPayload
    if (parsed.v !== 1) return null
    return parsed
  } catch {
    return null
  }
}

export function createStateFromPayload(
  payload: RealtimeStreamPayload,
  current: ConsoleState,
): ConsoleState {
  const controls = payload.current.controls as unknown as Record<string, number>
  const outputs = payload.current.outputs
  const variables = { ...current.variables }
  for (const key of CONTROL_VARIABLE_KEYS) {
    const domainKey = VARIABLE_KEY_TO_DOMAIN[key]
    const value = controls[domainKey] ?? variables[key].value
    variables[key] = {
      ...variables[key],
      value: roundForDigits(value, variables[key].digits),
    }
  }
  const metrics: ConsoleMetrics = {
    nox: outputs.nox,
    exhaust: outputs.exhaust_temp,
    lambda: outputs.lambda_,
    power: outputs.power,
    efficiency: outputs.efficiency,
    predictedNox: payload.forecast?.predicted_nox ?? outputs.nox,
  }
  return { ...current, variables, metrics }
}

function roundForDigits(value: number, digits: number) {
  const factor = 10 ** digits
  return Math.round(value * factor) / factor
}
