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

function noxState(v: number): KpiState {
  if (!Number.isFinite(v)) return 'normal'
  if (v >= 30) return 'crit'
  if (v >= 25) return 'warn'
  return 'normal'
}

function ttxmState(v: number): KpiState {
  if (!Number.isFinite(v)) return 'normal'
  if (v >= 620) return 'crit'
  if (v >= 600) return 'warn'
  return 'normal'
}

function dwattState(v: number): KpiState {
  if (!Number.isFinite(v)) return 'normal'
  if (v <= 180 || v >= 300) return 'crit'
  if (v < 200 || v > 280) return 'warn'
  return 'normal'
}

function lambdaState(v: number): KpiState {
  if (!Number.isFinite(v)) return 'normal'
  if (v <= 1.00 || v >= 1.25) return 'crit'
  if (v < 1.05 || v > 1.20) return 'warn'
  return 'normal'
}

export function computeKpiStates(inputs: KpiStateInputs): KpiStates {
  return {
    nox: noxState(inputs.nox),
    ttxm: ttxmState(inputs.ttxm),
    dwatt: dwattState(inputs.dwatt),
    lambda: lambdaState(inputs.lambda),
  }
}
