export interface FlowInputs {
  fuel: number  // 0~1
  nox: number   // 0~1
  air: number   // 0~1
}

export type FlowVars = {
  '--flow-fuel-duration': string
  '--flow-fuel-state': 'running' | 'paused'
  '--flow-nox-duration': string
  '--flow-nox-state': 'running' | 'paused'
  '--flow-air-duration': string
  '--flow-air-state': 'running' | 'paused'
  '--flow-cards-duration': string
  '--flow-cards-state': 'running' | 'paused'
}

interface Stage {
  duration: string
  state: 'running' | 'paused'
}

// ratio 0~1 → 연속 보간 duration (변화폭 40배, 초·중반 가속 강화)
//   < 0.05 : 정지 (잡음 데이터 스파이크 방지)
//   ≥ 0.05 : 4.0s(느림) → 0.1s(빠름) 지수 감쇠
//   공식: duration = 4.0 * (1/40)^ratio  → r=0.2≈1.74s, 0.3≈1.15s, 0.5≈0.63s, 0.7≈0.34s, 1.0=0.10s
function stageOf(ratio: number): Stage {
  if (!Number.isFinite(ratio) || ratio < 0.05) {
    return { duration: '1.2s', state: 'paused' }
  }
  const r = Math.min(Math.max(ratio, 0), 1)
  const duration = 4.0 * Math.pow(1 / 40, r)
  return { duration: `${duration.toFixed(2)}s`, state: 'running' }
}

export function getFlowAnimationVars(inputs: FlowInputs): FlowVars {
  const fuel = stageOf(inputs.fuel)
  const nox = stageOf(inputs.nox)
  const air = stageOf(inputs.air)
  return {
    '--flow-fuel-duration': fuel.duration,
    '--flow-fuel-state': fuel.state,
    '--flow-nox-duration': nox.duration,
    '--flow-nox-state': nox.state,
    '--flow-air-duration': air.duration,
    '--flow-air-state': air.state,
    '--flow-cards-duration': '1.2s',
    '--flow-cards-state': 'running',
  }
}
