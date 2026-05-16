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
  nox15pct: number
  exhaust: number
  lambda: number
  power: number
  efficiency: number
}

export type ConsoleMetrics = {
  nox: number
  nox15pct: number
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
  // 백엔드 payload의 단조 증가 tick (WS 메시지 1개당 +1). history.length는
  // 60에서 포화되므로 "새 payload 도착" 감지에는 이 값을 써야 한다.
  tick: number
  forecast: RealtimeStreamPayload['forecast']
  // backend warmup/stale 알림. ForecastCard가 예측 보류 표시에 사용.
  warning: RealtimeStreamPayload['warning']
  overrideActive: boolean
  kafkaLatest: RealtimeStreamPayload['kafka_latest']
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
  nox_15pct?: number
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
  // 모든 base/min/max는 학습 CSV(NOx_test_20250825.csv, DWATT>50MW 86401행) median 기반.
  // 운영 한계(min/max)는 학습 정상 운전 분포 ±25% + 도메인 상식 (밸브 0~100% 등).
  syngasFlow: {
    key: 'syngasFlow',
    label: '합성가스 유량',
    shortLabel: '합성가스',
    rawName: 'IGCC.CC.G1.ca_fqsg_cl',
    unit: 'kg/s',
    digits: 1,
    step: 0.5,
    base: 43.0,    // median
    min: 0,
    max: 80,       // median×1.9, plant 정격 영역
    value: 43.0,
  },
  igvOpening: {
    key: 'igvOpening',
    label: 'IGV 개도',
    shortLabel: 'IGV',
    rawName: 'IGCC.CC.G1.csgv',
    unit: '%',     // 개도이므로 ° → %로 정정
    digits: 1,
    step: 1,
    base: 63.0,    // median
    min: 30,
    max: 100,
    value: 63.0,
  },
  n2Offset: {
    key: 'n2Offset',
    label: '질소 오프셋',
    shortLabel: 'N2 오프셋',
    rawName: 'IGCC.CC.G1.NQKR3_MONITOR',
    unit: 'raw',
    digits: 1,
    step: 1,       // step 10→1, median 부근 미세 조정 가능
    base: -10.0,   // median (음수 영역)
    min: -50,
    max: 50,
    value: -10.0,
  },
  n2Valve1: {
    key: 'n2Valve1',
    label: 'N2 제어밸브 #1',
    shortLabel: 'NICVS1',
    rawName: 'IGCC.CC.G1.nicvs1',
    unit: '%',
    digits: 1,
    step: 1,
    base: 27.5,    // median
    min: 0,
    max: 100,
    value: 27.5,
  },
  syngasSrv: {
    key: 'syngasSrv',
    label: 'Syngas SRV',
    shortLabel: 'FSAGR',
    rawName: 'IGCC.CC.G1.FSAGR',
    unit: '%',
    digits: 1,
    step: 1,
    base: 38.6,    // median
    min: 0,
    max: 100,
    value: 38.6,
  },
  syngasGcv1: {
    key: 'syngasGcv1',
    label: 'Syngas GCV #1',
    shortLabel: 'FSAG11',
    rawName: 'IGCC.CC.G1.FSAG11',
    unit: '%',
    digits: 1,
    step: 1,
    base: 72.6,    // median (이전 28.4는 학습 분포 밖)
    min: 0,
    max: 100,
    value: 72.6,
  },
  syngasGcv1a: {
    key: 'syngasGcv1a',
    label: 'Syngas GCV #1A',
    shortLabel: 'FSAG11A',
    rawName: 'IGCC.CC.G1.FSAG11A',
    unit: '%',
    digits: 1,
    step: 1,
    base: 43.7,    // median
    min: 0,
    max: 100,
    value: 43.7,
  },
  syngasGcv2: {
    key: 'syngasGcv2',
    label: 'Syngas GCV #2',
    shortLabel: 'FSAG12',
    rawName: 'IGCC.CC.G1.FSAG12',
    unit: '%',
    digits: 1,
    step: 1,
    base: 15.0,    // median
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
    base: 0.2,     // median (정상 운전 시 거의 닫힘; 가열 시 100%까지 가능)
    min: 0,
    max: 100,
    value: 0.2,
  },
  n2Flow: {
    key: 'n2Flow',
    label: 'N2 주입 유량',
    shortLabel: 'NQJ',
    rawName: 'IGCC.CC.G1.NQJ',
    unit: 'kg/s',
    digits: 1,
    step: 0.5,
    base: 29.0,    // median
    min: 0,
    max: 60,
    value: 29.0,
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
          nox15pct: point.nox15pct,
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
    tick: 0,
    forecast: null,
    warning: null,
    overrideActive: false,
    kafkaLatest: null,
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

  const noxRaw = pickSnapshotValue(outputSource, ['nox'], previous?.metrics.nox ?? 25, 1)
  const metrics = {
    nox: noxRaw,
    // nox_15pct가 mock snapshot에 없을 수도 있으므로 raw nox로 폴백
    nox15pct: pickSnapshotValue(outputSource, ['nox_15pct'], previous?.metrics.nox15pct ?? noxRaw, 1),
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
    // snapshot.t를 tick 소스로 사용한다. backend session 엔드포인트가
    // `"t": payload["tick"]`(app/api/endpoints/session.py)로 채우므로
    // snapshot.t는 WS payload.tick과 동일한 session.tick 정수 카운터다
    // (스키마 타입만 float). ForecastCard는 tick !== seenTick으로 "새
    // payload 도착"만 감지하므로 단조 변화값이면 충분하다. 직전 tick
    // fallback은 세션 0 시작값이 이전 세션 잔존 seenTick과 우연히 충돌해
    // 첫 step이 누락되는 것을 피한다.
    tick: snapshot.t ?? previous?.tick ?? 0,
    forecast: previous?.forecast ?? null,
    warning: previous?.warning ?? null,
    overrideActive: previous?.overrideActive ?? false,
    kafkaLatest: previous?.kafkaLatest ?? null,
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

  // mock 시드에서는 O2 정보가 없으므로 nox15pct = raw nox로 폴백 (실제 backend는 별도 계산)
  return {
    nox: round(nox, 1),
    nox15pct: round(nox, 1),
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
      nox15pct: metrics.nox15pct,
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
      // backend 구버전(nox_15pct 미전송)과의 호환을 위해 optional. 매핑 단계에서 raw nox로 폴백.
      nox_15pct?: number
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
    // 동일 사유로 optional. ForecastCard 등 표시단에서 predicted_nox로 폴백.
    predicted_nox_15pct?: number
    target_time: string
    threshold_value: number
    threshold_exceeded: boolean
  } | null
  warning: string | null
}

// null이 아닌 forecast 페이로드 (isForecastReady 통과 시 narrowing 대상)
type ForecastPayload = NonNullable<RealtimeStreamPayload['forecast']>

/**
 * 5분 후 NOx 예측을 화면에 표시할 수 있는 정상 상태인지 판정.
 *
 * 새로고침 직후 backend SensorBuffer가 부분 충전된 구간에서는 forecaster가
 * OOD 외삽으로 -24 같은 음수를 낼 수 있다(`predict.py` ffill 폴백). 또한
 * backend는 warmup/stale 시 forecast=null + warning을 보낸다. 이 중 하나라도
 * 해당하면 false → 호출부는 "예측 모델 준비 중" 표시로 폴백한다.
 *
 * type predicate라 true 분기에서 forecast가 non-null로 narrowing된다.
 */
export function isForecastReady(
  forecast: RealtimeStreamPayload['forecast'],
  warning: RealtimeStreamPayload['warning'],
): forecast is ForecastPayload {
  if (forecast === null) return false
  if (warning !== null) return false
  const value = forecast.predicted_nox_15pct ?? forecast.predicted_nox
  if (value === undefined || !Number.isFinite(value)) return false
  return value >= 0
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
  // backend 구버전 호환: nox_15pct 미전송 시 raw nox로 폴백
  const noxCorrected = outputs.nox_15pct ?? outputs.nox
  const metrics: ConsoleMetrics = {
    nox: outputs.nox,
    nox15pct: noxCorrected,
    exhaust: outputs.exhaust_temp,
    lambda: outputs.lambda_,
    power: outputs.power,
    efficiency: outputs.efficiency,
    // predictedNox는 표시 일관성을 위해 15% O2 보정값 사용. 양쪽 모두 폴백 체인 적용.
    predictedNox:
      payload.forecast?.predicted_nox_15pct
      ?? payload.forecast?.predicted_nox
      ?? noxCorrected,
  }
  return {
    ...current,
    variables,
    metrics,
    tick: payload.tick,
    forecast: payload.forecast,
    warning: payload.warning,
    overrideActive: payload.override_active,
    kafkaLatest: payload.kafka_latest,
  }
}

function roundForDigits(value: number, digits: number) {
  const factor = 10 ** digits
  return Math.round(value * factor) / factor
}
