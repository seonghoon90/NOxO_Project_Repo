export type KpiState = 'normal' | 'warn' | 'crit'

export interface KpiStateInputs {
  nox: number
  ttxm: number
  dwatt: number
  lambda: number
}

export interface KpiStates {
  nox: KpiState
  ttxm: KpiState
  dwatt: KpiState
  lambda: KpiState
}

// 임계 SoT는 digital_twin/simulation/config.py. 호출부에서 useThresholds()로 주입.
// dwatt는 backend 미노출이라 SoT 부재 — 가안 기본값 유지 (정격 240 ±20 / ±60).
export interface KpiThresholds {
  noxWarn: number
  noxCrit: number
  ttxmWarn: number
  ttxmCrit: number
  lambdaWarnLo: number
  lambdaWarnHi: number
  lambdaCritLo: number
  lambdaCritHi: number
}

function rangeState(
  v: number,
  warnLo: number,
  warnHi: number,
  critLo: number,
  critHi: number,
): KpiState {
  if (!Number.isFinite(v)) return 'normal'
  if (v <= critLo || v >= critHi) return 'crit'
  if (v < warnLo || v > warnHi) return 'warn'
  return 'normal'
}

function upperBoundState(v: number, warn: number, crit: number): KpiState {
  if (!Number.isFinite(v)) return 'normal'
  if (v >= crit) return 'crit'
  if (v >= warn) return 'warn'
  return 'normal'
}

function dwattState(v: number): KpiState {
  if (!Number.isFinite(v)) return 'normal'
  if (v <= 180 || v >= 300) return 'crit'
  if (v < 200 || v > 280) return 'warn'
  return 'normal'
}

export function computeKpiStates(
  inputs: KpiStateInputs,
  thresholds: KpiThresholds,
): KpiStates {
  return {
    nox: upperBoundState(inputs.nox, thresholds.noxWarn, thresholds.noxCrit),
    ttxm: upperBoundState(inputs.ttxm, thresholds.ttxmWarn, thresholds.ttxmCrit),
    dwatt: dwattState(inputs.dwatt),
    lambda: rangeState(
      inputs.lambda,
      thresholds.lambdaWarnLo,
      thresholds.lambdaWarnHi,
      thresholds.lambdaCritLo,
      thresholds.lambdaCritHi,
    ),
  }
}
